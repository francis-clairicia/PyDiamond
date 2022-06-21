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
from typing import IO, Any, Final, Generator, Generic, TypeVar

from ...system.object import Object, final
from ...system.utils.itertools import consumer_start
from .base import AbstractNetworkProtocol, ValidationError

_T = TypeVar("_T")


class AbstractStreamNetworkProtocol(AbstractNetworkProtocol):
    def serialize(self, packet: Any) -> bytes:
        return b"".join(self.incremental_serialize(packet))

    def deserialize(self, data: bytes) -> Any:
        consumer: Generator[None, bytes, tuple[Any, bytes]] = self.incremental_deserialize()
        consumer_start(consumer)
        packet: Any
        remaining: bytes
        try:
            consumer.send(data)
        except StopIteration as exc:
            packet, remaining = exc.value
        else:
            consumer.close()
            raise ValidationError("Missing data to create packet")
        if remaining:
            raise ValidationError("Extra data caught")
        return packet

    @abstractmethod
    def incremental_serialize(self, packet: Any) -> Generator[bytes, None, None]:
        raise NotImplementedError

    def incremental_serialize_to(self, file: IO[bytes], packet: Any) -> None:
        assert file.writable()
        for chunk in self.incremental_serialize(packet):
            file.write(chunk)

    @abstractmethod
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[Any, bytes]]:
        raise NotImplementedError


class AutoSeparatedStreamNetworkProtocol(AbstractStreamNetworkProtocol):
    def __init__(self, separator: bytes, *, keepends: bool = False, **kwargs: Any) -> None:
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
        data = data.rstrip(self.separator)
        if self.separator in data:
            raise ValidationError(f"{self.separator!r} separator found in serialized packet {packet!r} and is not at the end")
        yield data + self.separator

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: Any) -> None:
        return AbstractStreamNetworkProtocol.incremental_serialize_to(self, file, packet)

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[Any, bytes]]:
        buffer: bytes = b""
        separator: bytes = self.separator
        keepends: bool = self.__keepends
        while True:
            buffer += yield
            if separator not in buffer:
                continue
            data, _, buffer = buffer.partition(separator)
            if keepends:
                data += separator
            try:
                packet = self.deserialize(data)
                return (packet, buffer)
            except ValidationError:
                continue
            finally:
                del data

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
        yield header
        yield data
        checksum = hashlib.md5(usedforsecurity=False)
        checksum.update(header)
        checksum.update(data)
        yield checksum.digest()

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: Any) -> None:
        return AbstractStreamNetworkProtocol.incremental_serialize_to(self, file, packet)

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[Any, bytes]]:
        header_struct: Struct = self.header
        header: bytes = yield
        while True:
            while len(header) < header_struct.size:
                header += yield

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
                header = header[1:] + buffer.read()
            else:
                checksum = hashlib.md5(usedforsecurity=False)
                checksum.update(header)
                body_struct = Struct(f"{body_length}s{checksum.digest_size}s")
                while len(buffer.getvalue()) < body_struct.size:
                    buffer.write((yield))

                buffer.seek(0)
                try:
                    body: bytes
                    checksum_digest: bytes
                    body, checksum_digest = body_struct.unpack(buffer.read(body_struct.size))
                except (StructError, TypeError):
                    # data may be corrupted
                    pass
                else:
                    try:
                        checksum.update(body)
                        if not compare_digest(checksum.digest(), checksum_digest):  # Data really corrupted
                            raise ValidationError
                        packet = self.deserialize(body)
                        return (packet, buffer.read())
                    except ValidationError:
                        pass
                    finally:
                        del body, checksum_digest
                finally:
                    del checksum
                header = buffer.read()
            finally:
                del buffer


class StreamNetworkPacketHandler(Generic[_T], Object):
    __slots__ = (
        "__protocol",
        "__incremental_deserialize",
    )

    def __init__(self, protocol: AbstractStreamNetworkProtocol) -> None:
        super().__init__()
        assert isinstance(protocol, AbstractStreamNetworkProtocol)
        self.__protocol: AbstractStreamNetworkProtocol = protocol
        self.__incremental_deserialize: Generator[None, bytes, tuple[_T, bytes]] | None = None

    def produce(self, packet: _T) -> Generator[bytes, None, None]:
        return (yield from self.__protocol.incremental_serialize(packet))

    def write(self, file: IO[bytes], packet: _T) -> None:
        return self.__protocol.incremental_serialize_to(file, packet)

    def consume(self, chunk: bytes) -> Generator[_T, None, None]:
        assert isinstance(chunk, bytes)
        if not chunk:
            return

        incremental_deserialize = self.__incremental_deserialize
        self.__incremental_deserialize = None

        while chunk:
            if incremental_deserialize is None:
                incremental_deserialize = self.__protocol.incremental_deserialize()
                consumer_start(incremental_deserialize)
            packet: _T
            try:
                incremental_deserialize.send(chunk)
            except StopIteration as exc:
                incremental_deserialize = None
                packet, chunk = exc.value
            else:
                break
            yield packet  # yield out of exception clause, in order to erase the StopIteration except context

        self.__incremental_deserialize = incremental_deserialize

    @property
    @final
    def protocol(self) -> AbstractStreamNetworkProtocol:
        return self.__protocol
