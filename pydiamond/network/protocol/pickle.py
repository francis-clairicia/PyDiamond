# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pickle-based network packet protocol module"""

from __future__ import annotations

__all__ = [
    "PickleNetworkProtocol",
    "PicklePacketDeserializer",
    "PicklePacketSerializer",
    "SafePickleNetworkProtocol",
    "SafePicklePacketDeserializer",
    "SafePicklePacketSerializer",
]

from io import BytesIO
from pickle import DEFAULT_PROTOCOL, STOP as STOP_OPCODE, Pickler, Unpickler, UnpicklingError
from pickletools import optimize as pickletools_optimize
from typing import IO, TYPE_CHECKING, Any, Callable, Generator, Generic, TypeVar
from weakref import ref as weakref

if TYPE_CHECKING:
    from cryptography.fernet import Fernet, MultiFernet

from ...system.object import Object, ProtocolObjectMeta, final
from ...system.utils.abc import concreteclass
from ...system.utils.weakref import weakref_unwrap
from .base import ValidationError
from .encryptor import EncryptorNetworkProtocol, EncryptorPacketDeserializer, EncryptorPacketSerializer
from .stream import (
    IncrementalDeserializeError,
    NetworkPacketIncrementalDeserializer,
    NetworkPacketIncrementalSerializer,
    StreamNetworkProtocol,
)

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


@concreteclass
class PicklePacketSerializer(NetworkPacketIncrementalSerializer[_T_contra], Object, metaclass=ProtocolObjectMeta):
    def __init__(self) -> None:
        super().__init__()

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        buffer = BytesIO()
        self.incremental_serialize_to(buffer, packet)
        return pickletools_optimize(buffer.getvalue())

    @final
    def incremental_serialize(self, packet: _T_contra) -> Generator[bytes, None, None]:
        yield self.serialize(packet)  # 'incremental' :)

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: _T_contra) -> None:
        assert file.writable()
        pickler = self.get_pickler(file)
        try:
            pickler.dump(packet)
        except BaseException:
            file.write(STOP_OPCODE)  # Ensure there is a stop opcode, so the receiver can quickly ignore it
            raise

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        return Pickler(buffer, protocol=DEFAULT_PROTOCOL, fix_imports=False, buffer_callback=None)


@concreteclass
class PicklePacketDeserializer(NetworkPacketIncrementalDeserializer[_T_co], Object, metaclass=ProtocolObjectMeta):
    def __init__(self) -> None:
        super().__init__()

    @final
    def deserialize(self, data: bytes) -> _T_co:
        if STOP_OPCODE not in data:
            raise ValidationError("Missing 'STOP' pickle opcode in data")
        buffer = BytesIO(data)
        unpickler = self.get_unpickler(buffer)
        try:
            packet: _T_co = unpickler.load()
        except UnpicklingError as exc:
            raise ValidationError("Unpickling error") from exc
        if data := buffer.read():  # There is still data after pickling
            raise ValidationError("Extra data caught")
        return packet

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_T_co, bytes]]:
        data = BytesIO()
        while True:
            data.write((yield))
            if STOP_OPCODE not in data.getvalue():
                continue
            data.seek(0)
            unpickler = self.get_unpickler(data)
            try:
                packet: _T_co = unpickler.load()
            except UnpicklingError as exc:
                remainder = data.getvalue().partition(STOP_OPCODE)[2]
                raise IncrementalDeserializeError(f"Unpickling error: {exc}", remaining_data=remainder) from exc
            return (packet, data.read())

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        return Unpickler(buffer, fix_imports=False, encoding="utf-8", errors="strict", buffers=None)


@concreteclass
class PickleNetworkProtocol(
    PicklePacketSerializer[_T_contra],
    PicklePacketDeserializer[_T_co],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co],
):
    pass


if TYPE_CHECKING:
    from .base import _BaseGenericWrapper


def _monkeypatch_protocol(self: _BaseGenericWrapper[Any], method_name: str) -> None:
    assert self.protocol is not None

    def unset_patch(_: Any, _protocol_ref: weakref[Any] = weakref(self.protocol)) -> None:
        protocol: Any | None = _protocol_ref()
        if protocol is not None:
            try:
                delattr(protocol, method_name)
            except AttributeError:
                pass

    selfref: weakref[_BaseGenericWrapper[Any]] = weakref(self, unset_patch)

    def patch(*args: Any, **kwargs: Any) -> Any:
        self: _BaseGenericWrapper[Any] = weakref_unwrap(selfref)
        method: Callable[..., Any] = getattr(self, method_name)
        return method(*args, **kwargs)

    setattr(self.protocol, method_name, patch)

    del self  # Explicitly breaks the reference


class SafePicklePacketSerializer(EncryptorPacketSerializer[_T_contra, PicklePacketSerializer[Any]], Generic[_T_contra]):
    def __init__(self, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(PicklePacketSerializer(), key)
        _monkeypatch_protocol(self, "get_pickler")

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        protocol = self.protocol
        return protocol.__class__.get_pickler(protocol, buffer)


class SafePicklePacketDeserializer(EncryptorPacketDeserializer[_T_co, PicklePacketDeserializer[Any]], Generic[_T_co]):
    def __init__(self, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(PicklePacketDeserializer(), key)
        _monkeypatch_protocol(self, "get_unpickler")

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        protocol = self.protocol
        return protocol.__class__.get_unpickler(protocol, buffer)


class SafePickleNetworkProtocol(
    EncryptorNetworkProtocol[_T_contra, _T_co, PickleNetworkProtocol[Any, Any]],
    Generic[_T_contra, _T_co],
):
    def __init__(self, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(PickleNetworkProtocol(), key)
        _monkeypatch_protocol(self, "get_pickler")
        _monkeypatch_protocol(self, "get_unpickler")

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        protocol = self.protocol
        return protocol.__class__.get_pickler(protocol, buffer)

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        protocol = self.protocol
        return protocol.__class__.get_unpickler(protocol, buffer)
