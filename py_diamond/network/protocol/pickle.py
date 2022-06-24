# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pickle-based network packet protocol module"""

from __future__ import annotations

__all__ = ["PicklingNetworkProtocol", "SafePicklingNetworkProtocol"]

from io import BytesIO
from pickle import HIGHEST_PROTOCOL, STOP as STOP_OPCODE, Pickler, Unpickler, UnpicklingError
from pickletools import optimize as pickletools_optimize
from typing import IO, TYPE_CHECKING, Any, Callable, Generator
from weakref import ref as weakref

if TYPE_CHECKING:
    from cryptography.fernet import Fernet, MultiFernet

from ...system.object import final
from ...system.utils.abc import concreteclass
from ...system.utils.weakref import weakref_unwrap
from .base import ValidationError
from .encryptor import EncryptorProtocol
from .stream import AbstractStreamNetworkProtocol


@concreteclass
class PicklingNetworkProtocol(AbstractStreamNetworkProtocol):
    @final
    def serialize(self, packet: Any) -> bytes:
        buffer = BytesIO()
        self.incremental_serialize_to(buffer, packet)
        return pickletools_optimize(buffer.getvalue())

    @final
    def incremental_serialize(self, packet: Any) -> Generator[bytes, None, None]:
        yield self.serialize(packet)  # 'incremental' :)

    @final
    def deserialize(self, data: bytes) -> Any:
        if STOP_OPCODE not in data:
            raise ValidationError("Missing 'STOP' pickle opcode in data")
        buffer = BytesIO(data)
        unpickler = self.get_unpickler(buffer)
        try:
            packet = unpickler.load()
        except UnpicklingError as exc:
            raise ValidationError("Unpickling error") from exc
        if buffer.read():  # There is still data after pickling
            raise ValidationError("Extra data caught")
        return packet

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: Any) -> None:
        assert file.writable()
        pickler = self.get_pickler(file)
        pickler.dump(packet)

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[Any, bytes]]:
        data = BytesIO()
        while True:
            data.write((yield))
            if STOP_OPCODE in data.getvalue():
                data.seek(0)
                unpickler = self.get_unpickler(data)
                try:
                    packet = unpickler.load()
                except UnpicklingError:
                    # We flush unused data as it may be corrupted
                    data = BytesIO(data.getvalue().partition(STOP_OPCODE)[2])
                else:
                    return (packet, data.read())

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        return Pickler(buffer, protocol=HIGHEST_PROTOCOL, fix_imports=False, buffer_callback=None)

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        return Unpickler(buffer, fix_imports=False, encoding="utf-8", errors="strict", buffers=None)


class SafePicklingNetworkProtocol(EncryptorProtocol[PicklingNetworkProtocol]):
    def __init__(self, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(PicklingNetworkProtocol(), key)

        def monkeypatch_protocol(self: SafePicklingNetworkProtocol, method_name: str) -> None:
            def unset_patch(_: Any, _protocol_ref: weakref[PicklingNetworkProtocol] = weakref(self.protocol)) -> None:
                protocol: PicklingNetworkProtocol | None = _protocol_ref()
                if protocol is not None:
                    try:
                        delattr(protocol, method_name)
                    except AttributeError:
                        pass

            selfref: weakref[SafePicklingNetworkProtocol] = weakref(self, unset_patch)

            def patch(*args: Any, **kwargs: Any) -> Any:
                self: SafePicklingNetworkProtocol = weakref_unwrap(selfref)
                method: Callable[..., Any] = getattr(self, method_name)
                return method(*args, **kwargs)

            setattr(self.protocol, method_name, patch)

            del self  # Explicitly breaks the reference

        monkeypatch_protocol(self, "get_pickler")
        monkeypatch_protocol(self, "get_unpickler")

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        protocol = self.protocol
        return protocol.__class__.get_pickler(protocol, buffer)

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        protocol = self.protocol
        return protocol.__class__.get_unpickler(protocol, buffer)
