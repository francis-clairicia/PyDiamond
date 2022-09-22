# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Stream network packet protocol handler module"""

from __future__ import annotations

__all__ = [
    "AutoParsedPacketDeserializer",
    "AutoParsedPacketSerializer",
    "AutoParsedStreamNetworkProtocol",
    "AutoSeparatedPacketDeserializer",
    "AutoSeparatedPacketSerializer",
    "AutoSeparatedStreamNetworkProtocol",
    "FixedPacketSizeDeserializer",
    "FixedPacketSizeSerializer",
    "FixedPacketSizeStreamNetworkProtocol",
    "NetworkPacketIncrementalDeserializer",
    "NetworkPacketIncrementalSerializer",
    "StreamNetworkProtocol",
]

import hashlib
from abc import abstractmethod
from hmac import compare_digest
from io import BytesIO, IOBase
from struct import Struct, error as StructError
from typing import IO, Any, Final, Generator, Generic, Protocol, TypeVar, runtime_checkable

from ...system.object import ProtocolObjectMeta, final
from ...system.utils.itertools import consumer_start, send_return
from .abc import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol, ValidationError

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


class IncrementalDeserializeError(ValidationError):
    def __init__(self, message: str, *, remaining_data: bytes, data_with_error: bytes = b"") -> None:
        if data_with_error:
            message = f"Error when parsing {data_with_error!r}: {message}"
        super().__init__(message)
        self.remaining_data = remaining_data


@runtime_checkable
class NetworkPacketIncrementalSerializer(NetworkPacketSerializer[_ST_contra], Protocol[_ST_contra]):
    def serialize(self, packet: _ST_contra) -> bytes:
        # The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        return b"".join(list(self.incremental_serialize(packet)))

    @abstractmethod
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        raise NotImplementedError

    def incremental_serialize_to(self, file: IOBase | IO[bytes], packet: _ST_contra) -> None:
        assert file.writable()
        write = file.write
        for chunk in self.incremental_serialize(packet):
            write(chunk)


@runtime_checkable
class NetworkPacketIncrementalDeserializer(NetworkPacketDeserializer[_DT_co], Protocol[_DT_co]):
    def deserialize(self, data: bytes) -> _DT_co:
        consumer: Generator[None, bytes, tuple[_DT_co, bytes]] = self.incremental_deserialize()
        consumer_start(consumer)
        packet: _DT_co
        remaining: bytes
        try:
            packet, remaining = send_return(consumer, data)
        except StopIteration:
            consumer.close()
            raise ValidationError("Missing data to create packet") from None
        if remaining:
            raise ValidationError("Extra data caught")
        return packet

    @abstractmethod
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        raise NotImplementedError


@runtime_checkable
class StreamNetworkProtocol(
    NetworkPacketIncrementalSerializer[_ST_contra],
    NetworkPacketIncrementalDeserializer[_DT_co],
    NetworkProtocol[_ST_contra, _DT_co],
    Protocol[_ST_contra, _DT_co],
):
    pass


class _BaseAutoSeparatedPacket(metaclass=ProtocolObjectMeta):
    def __init__(self, separator: bytes, *, keepends: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        assert isinstance(separator, bytes)
        if len(separator) < 1:
            raise ValueError("Empty separator")
        self.__separator: bytes = separator
        self.__keepends: bool = bool(keepends)

    @property
    @final
    def separator(self) -> bytes:
        return self.__separator

    @property
    @final
    def keepends(self) -> bool:
        return self.__keepends


class AutoSeparatedPacketSerializer(_BaseAutoSeparatedPacket, NetworkPacketIncrementalSerializer[_ST_contra]):
    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        separator: bytes = self.separator
        data = data.rstrip(separator)
        if separator in data:
            raise ValidationError(f"{separator!r} separator found in serialized packet {packet!r} and is not at the end")
        yield data + separator

    @final
    def incremental_serialize_to(self, file: IOBase | IO[bytes], packet: _ST_contra) -> None:
        return NetworkPacketIncrementalSerializer.incremental_serialize_to(self, file, packet)


class AutoSeparatedPacketDeserializer(_BaseAutoSeparatedPacket, NetworkPacketIncrementalDeserializer[_DT_co]):
    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        buffer: bytes = b""
        separator: bytes = self.separator
        keepends: bool = self.keepends
        while separator not in buffer:
            buffer += yield
        data, _, buffer = buffer.partition(separator)
        if keepends:
            data += separator
        try:
            packet = self.deserialize(data)
        except ValidationError as exc:
            raise IncrementalDeserializeError(
                f"Error when deserializing data: {exc}",
                remaining_data=buffer,
                data_with_error=data,
            )
        return (packet, buffer)


class AutoSeparatedStreamNetworkProtocol(
    AutoSeparatedPacketSerializer[_ST_contra],
    AutoSeparatedPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    pass


class _BaseAutoParsedPacket(metaclass=ProtocolObjectMeta):
    MAGIC: Final[bytes] = b"\x7f\x1b\xea\xff"
    header: Final[Struct] = Struct("!4sI")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class AutoParsedPacketSerializer(_BaseAutoParsedPacket, NetworkPacketIncrementalSerializer[_ST_contra]):
    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        header: bytes = self.header.pack(self.__class__.MAGIC, len(data))
        yield header
        yield data
        checksum = hashlib.md5(usedforsecurity=False)
        checksum.update(header)
        checksum.update(data)
        yield checksum.digest()

    @final
    def incremental_serialize_to(self, file: IOBase | IO[bytes], packet: _ST_contra) -> None:
        return NetworkPacketIncrementalSerializer.incremental_serialize_to(self, file, packet)


class AutoParsedPacketDeserializer(_BaseAutoParsedPacket, NetworkPacketIncrementalDeserializer[_DT_co]):
    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
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
            except StructError:
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
                data = buffer.read(body_struct.size)
                try:
                    body: bytes
                    checksum_digest: bytes
                    body, checksum_digest = body_struct.unpack(data)
                    checksum.update(body)
                    if not compare_digest(checksum.digest(), checksum_digest):  # Data really corrupted
                        raise StructError
                except StructError as exc:
                    raise IncrementalDeserializeError(
                        f"Data corrupted: {exc}",
                        remaining_data=buffer.read(),
                        data_with_error=data,
                    ) from exc
                try:
                    packet: _DT_co = self.deserialize(body)
                except ValidationError as exc:
                    raise IncrementalDeserializeError(
                        f"Error when deserializing data: {exc}",
                        remaining_data=buffer.read(),
                        data_with_error=data,
                    ) from exc
                return (packet, buffer.read())
            finally:
                del buffer


class AutoParsedStreamNetworkProtocol(
    AutoParsedPacketSerializer[_ST_contra],
    AutoParsedPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    pass


class _BaseFixedPacketSize(metaclass=ProtocolObjectMeta):
    def __init__(self, size: int, **kwargs: Any) -> None:
        size = int(size)
        if size <= 0:
            raise ValueError("size must be a positive integer")
        super().__init__(**kwargs)
        self.__size: int = size

    @property
    @final
    def packet_size(self) -> int:
        return self.__size


class FixedPacketSizeSerializer(_BaseFixedPacketSize, NetworkPacketIncrementalSerializer[_ST_contra]):
    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        data = self.serialize(packet)
        if len(data) != self.packet_size:
            raise ValidationError("serialized data size does not meet expectation")
        yield data


class FixedPacketSizeDeserializer(_BaseFixedPacketSize, NetworkPacketIncrementalDeserializer[_DT_co]):
    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        buffer: bytes = b""
        packet_size: int = self.packet_size
        while len(buffer) < packet_size:
            buffer += yield
        data, buffer = buffer[:packet_size], buffer[packet_size:]
        try:
            packet = self.deserialize(data)
        except ValidationError as exc:
            raise IncrementalDeserializeError(
                f"Error when deserializing data: {exc}",
                remaining_data=buffer,
                data_with_error=data,
            ) from exc
        return (packet, buffer)


class FixedPacketSizeStreamNetworkProtocol(
    FixedPacketSizeSerializer[_ST_contra],
    FixedPacketSizeDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    pass
