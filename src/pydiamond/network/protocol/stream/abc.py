# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Stream network packet protocol handler module"""

from __future__ import annotations

__all__ = [
    "AutoParsedStreamNetworkProtocol",
    "AutoSeparatedStreamNetworkProtocol",
    "FixedPacketSizeStreamNetworkProtocol",
    "NetworkPacketIncrementalDeserializer",
    "NetworkPacketIncrementalSerializer",
    "StreamNetworkProtocol",
]

import hashlib
from abc import abstractmethod
from hmac import compare_digest
from io import BytesIO
from struct import Struct, error as StructError
from typing import Any, Generator, TypeVar

from ....system.object import final
from ....system.utils.itertools import NoStopIteration, consumer_start, send_return
from ..abc import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol
from ..exceptions import DeserializeError
from .exceptions import IncrementalDeserializeError

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


class NetworkPacketIncrementalSerializer(NetworkPacketSerializer[_ST_contra]):
    __slots__ = ()

    def serialize(self, packet: _ST_contra) -> bytes:
        # The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        return b"".join(list(self.incremental_serialize(packet)))

    @abstractmethod
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        raise NotImplementedError


class NetworkPacketIncrementalDeserializer(NetworkPacketDeserializer[_DT_co]):
    __slots__ = ()

    def deserialize(self, data: bytes) -> _DT_co:
        consumer: Generator[None, bytes, tuple[_DT_co, bytes]] = self.incremental_deserialize()
        consumer_start(consumer)
        packet: _DT_co
        remaining: bytes
        try:
            packet, remaining = send_return(consumer, data)
        except NoStopIteration:
            consumer.close()
            raise DeserializeError("Missing data to create packet") from None
        if remaining:
            raise DeserializeError("Extra data caught")
        return packet

    @abstractmethod
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        raise NotImplementedError


class StreamNetworkProtocol(
    NetworkProtocol[_ST_contra, _DT_co],
    NetworkPacketIncrementalSerializer[_ST_contra],
    NetworkPacketIncrementalDeserializer[_DT_co],
):
    __slots__ = ()


class AutoSeparatedStreamNetworkProtocol(StreamNetworkProtocol[_ST_contra, _DT_co]):
    __slots__ = ("__separator", "__keepends")

    def __init__(self, separator: bytes, *, keepends: bool = False, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        assert isinstance(separator, bytes)
        if len(separator) < 1:
            raise ValueError("Empty separator")
        self.__separator: bytes = separator
        self.__keepends: bool = bool(keepends)

    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        separator: bytes = self.__separator
        data = data.rstrip(separator)
        if separator in data:
            raise ValueError(f"{separator!r} separator found in serialized packet {packet!r} which was not at the end")
        yield data + separator

    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        buffer: bytes = b""
        separator: bytes = self.__separator
        keepends: bool = self.__keepends
        while separator not in buffer:
            buffer += yield
        data, _, buffer = buffer.partition(separator)
        if keepends:
            data += separator
        try:
            packet = self.deserialize(data)
        except DeserializeError as exc:
            raise IncrementalDeserializeError(
                f"Error when deserializing data: {exc}",
                remaining_data=buffer,
            ) from exc
        return (packet, buffer)

    @property
    @final
    def separator(self) -> bytes:
        return self.__separator

    @property
    @final
    def keepends(self) -> bool:
        return self.__keepends


class AutoParsedStreamNetworkProtocol(StreamNetworkProtocol[_ST_contra, _DT_co]):
    __slots__ = ("__magic", "__algorithm")

    def __init__(self, magic: bytes, *, checksum: str = "md5", **kwargs: Any) -> None:
        assert isinstance(magic, bytes)
        if len(magic) != 4:
            raise ValueError("Magic bytes must be 4-byte length")
        if checksum not in hashlib.algorithms_available:
            raise ValueError(f"Unknown hashlib algorithm {checksum!r}")
        super().__init__(**kwargs)
        self.__magic: bytes = magic
        self.__algorithm: str = checksum

    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        header: bytes = Struct("!4sH").pack(self.__magic, len(data))
        yield header
        yield data
        checksum = hashlib.new(self.__algorithm, usedforsecurity=False)
        checksum.update(header)
        checksum.update(data)
        yield checksum.digest()

    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        header_struct: Struct = Struct("!4sH")
        expected_magic: bytes = self.__magic
        checksum_algorithm: str = self.__algorithm
        header: bytes = b""
        while len(header) < header_struct.size:
            header += yield

        buffer = BytesIO(header[header_struct.size :])
        header = header[: header_struct.size]
        try:
            magic: bytes
            body_length: int
            magic, body_length = header_struct.unpack(header)
            if magic != expected_magic:
                raise StructError("Invalid magic number")
        except StructError as exc:
            # data may be corrupted
            # Shift by 1 received data
            raise IncrementalDeserializeError(
                "Invalid header",
                remaining_data=header[1:] + buffer.read(),
            ) from exc

        checksum = hashlib.new(checksum_algorithm, usedforsecurity=False)
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
                raise StructError("Invalid checksum")
        except StructError as exc:
            raise IncrementalDeserializeError(
                f"Data corrupted: {exc}",
                remaining_data=buffer.read(),
            ) from exc
        try:
            packet: _DT_co = self.deserialize(body)
        except DeserializeError as exc:
            raise IncrementalDeserializeError(
                f"Error when deserializing data: {exc}",
                remaining_data=buffer.read(),
            ) from exc
        return (packet, buffer.read())

    @property
    @final
    def magic(self) -> bytes:
        return self.__magic

    @property
    @final
    def checksum_algorithm(self) -> str:
        return self.__algorithm


class FixedPacketSizeStreamNetworkProtocol(StreamNetworkProtocol[_ST_contra, _DT_co]):
    __slots__ = ("__size",)

    def __init__(self, size: int, **kwargs: Any) -> None:
        size = int(size)
        if size <= 0:
            raise ValueError("size must be a positive integer")
        super().__init__(**kwargs)
        self.__size: int = size

    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        data = self.serialize(packet)
        if len(data) != self.__size:
            raise ValueError("serialized data size does not meet expectation")
        yield data

    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        buffer: bytes = b""
        packet_size: int = self.__size
        while len(buffer) < packet_size:
            buffer += yield
        data, buffer = buffer[:packet_size], buffer[packet_size:]
        try:
            packet = self.deserialize(data)
        except DeserializeError as exc:
            raise IncrementalDeserializeError(
                f"Error when deserializing data: {exc}",
                remaining_data=data[1:] + buffer,
            ) from exc
        return (packet, buffer)

    @property
    @final
    def packet_size(self) -> int:
        return self.__size
