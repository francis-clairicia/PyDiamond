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
]

from io import BytesIO
from pickle import DEFAULT_PROTOCOL, STOP as STOP_OPCODE, Pickler, Unpickler, UnpicklingError
from pickletools import optimize as pickletools_optimize
from typing import TYPE_CHECKING, Any, Callable, Generator, Generic, TypeVar
from weakref import ref as weakref

if TYPE_CHECKING:
    from cryptography.fernet import Fernet, MultiFernet
    from pickle import _WritableFileobj, _ReadableFileobj

from ...system.object import Object, ProtocolObjectMeta, final
from ...system.utils.abc import concreteclass
from ...system.utils.weakref import weakref_unwrap
from .abc import ValidationError
from .stream import (
    IncrementalDeserializeError,
    NetworkPacketIncrementalDeserializer,
    NetworkPacketIncrementalSerializer,
    StreamNetworkProtocol,
)
from .wrapper.encryptor import EncryptorNetworkProtocol

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@concreteclass
class PicklePacketSerializer(NetworkPacketIncrementalSerializer[_ST_contra], Object, metaclass=ProtocolObjectMeta):
    def __init__(self) -> None:
        super().__init__()

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        buffer = BytesIO()
        pickler = self.get_pickler(buffer)
        pickler.dump(packet)
        return pickletools_optimize(buffer.getvalue())

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        yield self.serialize(packet)  # 'incremental' :)

    def get_pickler(self, buffer: _WritableFileobj) -> Pickler:
        return Pickler(buffer, protocol=DEFAULT_PROTOCOL, fix_imports=False, buffer_callback=None)


@concreteclass
class PicklePacketDeserializer(NetworkPacketIncrementalDeserializer[_DT_co], Object, metaclass=ProtocolObjectMeta):
    def __init__(self) -> None:
        super().__init__()

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        if STOP_OPCODE not in data:
            raise ValidationError("Missing 'STOP' pickle opcode in data")
        buffer = BytesIO(data)
        unpickler = self.get_unpickler(buffer)
        try:
            packet: _DT_co = unpickler.load()
        except UnpicklingError as exc:
            raise ValidationError("Unpickling error") from exc
        if data := buffer.read():  # There is still data after pickling
            raise ValidationError("Extra data caught")
        return packet

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        data = BytesIO()
        while STOP_OPCODE not in data.getvalue():
            data.write((yield))
        data.seek(0)
        unpickler = self.get_unpickler(data)
        try:
            packet: _DT_co = unpickler.load()
        except UnpicklingError as exc:
            data_with_error, _, remainder = data.getvalue().partition(STOP_OPCODE)
            raise IncrementalDeserializeError(
                f"Unpickling error: {exc}",
                remaining_data=remainder,
                data_with_error=data_with_error,
            ) from exc
        return (packet, data.read())

    def get_unpickler(self, buffer: _ReadableFileobj) -> Unpickler:
        return Unpickler(buffer, fix_imports=False, encoding="utf-8", errors="strict", buffers=None)


@concreteclass
class PickleNetworkProtocol(
    PicklePacketSerializer[_ST_contra],
    PicklePacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    pass


class SafePickleNetworkProtocol(EncryptorNetworkProtocol[_ST_contra, _DT_co], Generic[_ST_contra, _DT_co]):
    def __init__(self, key: str | bytes | Fernet | MultiFernet, ttl: int | None = None) -> None:
        super().__init__(PickleNetworkProtocol(), key, ttl)
        self.__monkeypatch_protocol("get_pickler")
        self.__monkeypatch_protocol("get_unpickler")

    def get_pickler(self, buffer: _WritableFileobj) -> Pickler:
        protocol: PickleNetworkProtocol[Any, Any] = self.protocol
        return protocol.__class__.get_pickler(protocol, buffer)

    def get_unpickler(self, buffer: _ReadableFileobj) -> Unpickler:
        protocol: PickleNetworkProtocol[Any, Any] = self.protocol
        return protocol.__class__.get_unpickler(protocol, buffer)

    def __monkeypatch_protocol(self, method_name: str) -> None:
        def unset_patch(_: Any, _protocol_ref: weakref[Any] = weakref(self.protocol)) -> None:
            protocol: Any | None = _protocol_ref()
            if protocol is not None:
                try:
                    delattr(protocol, method_name)
                except AttributeError:
                    pass

        selfref = weakref(self, unset_patch)

        def patch(*args: Any, **kwargs: Any) -> Any:
            self = weakref_unwrap(selfref)
            method: Callable[..., Any] = getattr(self, method_name)
            return method(*args, **kwargs)

        setattr(self.protocol, method_name, patch)

    if TYPE_CHECKING:

        @property
        def protocol(self) -> PickleNetworkProtocol[_ST_contra, _DT_co]:
            ...
