# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Stream network packet protocol handler module"""

from __future__ import annotations

__all__ = [
    "AbstractStreamNetworkProtocol",
    "AutoParsedStreamNetworkProtocol",
    "AutoSeparatedStreamNetworkProtocol",
    "StreamNetworkPacketHandler",
]

import hashlib
from abc import abstractmethod
from hmac import compare_digest
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
        except Exception as exc:
            raise RuntimeError("generator stopped abruptly") from exc
        if packet is self.__class__.NO_PACKET:
            raise ValidationError("Missing data to create packet")
        try:
            next_packet = next(consumer)
        except Exception as exc:
            raise RuntimeError("generator stopped abruptly") from exc
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


class AutoSeparatedStreamNetworkProtocol(AbstractStreamNetworkProtocol):
    def __init__(self, separator: bytes, keepends: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        assert isinstance(separator, bytes)
        if len(separator) < 1:
            raise ValueError("Empty separator")
        self.__separator: bytes = separator
        self.__keepends: bool = bool(keepends)

    @abstractmethod
    def serialize(self, packet: Any) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: Any) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        if self.separator in data:
            if len(data[data.find(self.separator) + len(self.separator) :]) > 0:
                raise ValidationError(f"{self.separator!r} separator found in serialized packet {packet!r} and is not at the end")
            yield data
        else:
            yield data + self.separator

    @final
    def incremental_deserialize(self, initial_bytes: bytes) -> Generator[Any, bytes | None, None]:
        buffer: bytes = initial_bytes
        del initial_bytes
        separator: bytes = self.separator
        while True:
            packet: Any
            new_chunk: bytes | None
            if separator in buffer:
                data, _, buffer = buffer.partition(separator)
                if self.__keepends:
                    data += separator
                try:
                    packet = self.deserialize(data)
                except ValidationError:
                    packet = self.__class__.NO_PACKET
            else:
                packet = self.__class__.NO_PACKET
            new_chunk = yield packet
            if new_chunk:
                buffer += new_chunk
            del new_chunk

    @property
    @final
    def separator(self) -> bytes:
        return self.__separator

    @property
    @final
    def keepends(self) -> bool:
        return self.__keepends


class AutoParsedStreamNetworkProtocol(AbstractStreamNetworkProtocol):
    MAGIC: Final[bytes] = b"\x7f\x1b\xea\xff"
    header: Final[Struct] = Struct(f"!4sI")

    @abstractmethod
    def serialize(self, packet: Any) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: Any) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        header: bytes = self.header.pack(self.__class__.MAGIC, len(data))
        checksum = hashlib.md5(usedforsecurity=False)
        checksum.update(header)
        checksum.update(data)
        yield header
        yield data
        yield checksum.digest()

    @final
    def incremental_deserialize(self, initial_bytes: bytes) -> Generator[Any, bytes | None, None]:
        header_struct: Struct = self.header
        header: bytes = initial_bytes
        del initial_bytes
        while True:
            new_chunks: bytes | None
            while len(header) < header_struct.size:
                new_chunks = yield self.__class__.NO_PACKET
                if new_chunks:
                    header += new_chunks
                del new_chunks

            buffer = BytesIO(header[header_struct.size :])
            header = header[: header_struct.size]
            try:
                magic: bytes
                body_length: int
                magic, body_length = header_struct.unpack(header)
                if magic != self.__class__.MAGIC:
                    raise StructError
            except (StructError, TypeError):
                # data may be corrupted
                # Shift by 1 received data
                header = header[1:] + buffer.read(None)
            else:
                checksum = hashlib.md5(usedforsecurity=False)
                checksum.update(header)
                body_struct = Struct(f"{body_length}s{checksum.digest_size}s")
                while len(buffer.getvalue()) < body_struct.size:
                    new_chunks = yield self.__class__.NO_PACKET
                    if new_chunks:
                        buffer.write(new_chunks)
                    del new_chunks

                buffer.seek(0)
                try:
                    body: bytes
                    checksum_digest: bytes
                    body, checksum_digest = body_struct.unpack(buffer.read(body_struct.size))
                except (StructError, TypeError):
                    # data may be corrupted
                    packet = self.__class__.NO_PACKET
                else:
                    try:
                        checksum.update(body)
                        if not compare_digest(checksum.digest(), checksum_digest):  # Data really corrupted
                            raise ValidationError
                        packet = self.deserialize(body)
                    except ValidationError:
                        packet = self.__class__.NO_PACKET
                new_chunks = yield packet
                header = buffer.read(None) + (new_chunks or b"")
                del new_chunks
            finally:
                del buffer


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
        if not chunk:
            return

        incremental_deserialize = self.__incremental_deserialize
        NO_PACKET = self.__protocol.__class__.NO_PACKET

        data: bytes | None = chunk
        del chunk

        def send(gen: Generator[_T, Any, Any], v: Any) -> _T:
            try:
                return gen.send(v)
            except Exception as exc:
                raise RuntimeError("generator stopped abruptly") from exc

        while (packet := send(incremental_deserialize, data)) is not NO_PACKET:
            yield packet
            data = None  # Ask to re-use internal buffer

    @property
    @final
    def protocol(self) -> AbstractStreamNetworkProtocol:
        return self.__protocol
