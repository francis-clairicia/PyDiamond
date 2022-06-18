# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Stream network packet protocol handler module"""

from __future__ import annotations

__all__ = [
    "AbstractStreamNetworkProtocol",
    "AutoParsedStreamNetworkProtocol",
    "StreamNetworkPacketHandler",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from io import BytesIO
from struct import Struct, error as StructError
from typing import Any, Final, Generator, Generic, TypeVar

from ...system.object import Object, final
from .base import AbstractNetworkProtocol, ValidationError

_T = TypeVar("_T")


class AbstractStreamNetworkProtocol(AbstractNetworkProtocol):
    NO_PACKET: Final[Any] = object()

    def serialize(self, packet: Any) -> bytes:
        return b"".join(self.incremental_serialize(packet))

    def deserialize(self, data: bytes) -> Any:
        consumer = self.incremental_deserialize(data)
        try:
            packet = next(consumer)
        except:
            raise RuntimeError("generator stopped abruptly") from None
        if packet is self.__class__.NO_PACKET:
            raise ValidationError("Missing data to create packet")
        try:
            next_packet = next(consumer)
        except:
            raise RuntimeError("generator stopped abruptly") from None
        consumer.close()
        if next_packet is not self.__class__.NO_PACKET:
            raise ValidationError("Extra data")
        return packet

    @abstractmethod
    def incremental_serialize(self, packet: Any) -> Generator[bytes, None, None]:
        raise NotImplementedError

    @abstractmethod
    def incremental_deserialize(self, initial_bytes: bytes) -> Generator[Any, bytes | None, None]:
        raise NotImplementedError


class AutoParsedStreamNetworkProtocol(AbstractStreamNetworkProtocol):
    MAGIC: Final[bytes] = b"\x7f\x1b\xea\xff"
    __header_struct: Final[Struct] = Struct(f"!{len(MAGIC)}sI")

    @abstractmethod
    def serialize(self, packet: Any) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: Any) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        yield self.__header_struct.pack(self.__class__.MAGIC, len(data))
        yield data

    @final
    def incremental_deserialize(self, initial_bytes: bytes) -> Generator[Any, bytes | None, None]:
        struct: Struct = self.__header_struct
        header: bytes = initial_bytes
        del initial_bytes
        while True:
            new_chunks: bytes | None
            while len(header) < struct.size:
                new_chunks = yield self.__class__.NO_PACKET
                if new_chunks:
                    header += new_chunks
                del new_chunks

            body = BytesIO(header[struct.size :])
            header = header[: struct.size]
            try:
                magic: bytes
                body_length: int
                magic, body_length = struct.unpack(header)
                if magic != self.__class__.MAGIC:
                    raise StructError
            except (StructError, TypeError):
                # data may be corrupted
                # Shift by 1 received data
                header = header[1:] + body.read(None)
            else:
                while len(body.getbuffer()) < body_length:
                    new_chunks = yield self.__class__.NO_PACKET
                    if new_chunks:
                        body.write(new_chunks)
                    del new_chunks

                body.seek(0)
                try:
                    packet = self.deserialize(body.read(body_length))
                except ValidationError:
                    packet = self.__class__.NO_PACKET
                new_chunks = yield packet
                header = body.read(None) + (new_chunks or b"")
            finally:
                del body


class StreamNetworkPacketHandler(Generic[_T], Object):
    def __init__(self, protocol: AbstractStreamNetworkProtocol) -> None:
        super().__init__()
        assert isinstance(protocol, AbstractStreamNetworkProtocol)
        self.__protocol: AbstractStreamNetworkProtocol = protocol
        self.__incremental_deserialize: Generator[_T, bytes | None, None] = protocol.incremental_deserialize(b"")
        next(self.__incremental_deserialize)  # Generator ready for send()

    def produce(self, packet: _T) -> Generator[bytes, None, None]:
        yield from self.__protocol.incremental_serialize(packet)

    def consume(self, chunk: bytes) -> Generator[_T, None, None]:
        incremental_deserialize = self.__incremental_deserialize
        NO_PACKET = self.__protocol.__class__.NO_PACKET

        data: bytes | None = chunk
        del chunk

        def send(gen: Generator[_T, Any, Any], v: Any) -> _T:
            try:
                return gen.send(v)
            except:
                raise RuntimeError("generator stopped abruptly") from None

        while (packet := send(incremental_deserialize, data)) is not NO_PACKET:
            yield packet
            data = None  # Ask to re-use internal buffer

    @property
    @final
    def protocol(self) -> AbstractStreamNetworkProtocol:
        return self.__protocol
