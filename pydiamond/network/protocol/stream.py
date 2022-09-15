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
    "NetworkPacketIncrementalDeserializer",
    "NetworkPacketIncrementalSerializer",
    "StreamNetworkPacketHandler",
    "StreamNetworkProtocol",
]

import hashlib
from abc import abstractmethod
from hmac import compare_digest
from io import BytesIO
from struct import Struct, error as StructError
from typing import IO, Any, Final, Generator, Generic, Protocol, TypeVar, runtime_checkable

from ...system.object import Object, ProtocolObjectMeta, final
from ...system.utils.itertools import consumer_start, send_return
from .base import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol, ValidationError

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


class IncrementalDeserializeError(ValidationError):
    def __init__(self, message: str, *, remaining_data: bytes, data_with_error: bytes = b"") -> None:
        if data_with_error:
            message = f"Error when parsing {data_with_error!r}: {message}"
        super().__init__(message)
        self.remaining_data = remaining_data


@runtime_checkable
class NetworkPacketIncrementalSerializer(NetworkPacketSerializer[_T_contra], Protocol[_T_contra]):
    def serialize(self, packet: _T_contra) -> bytes:
        # The list call should be roughly
        # equivalent to the PySequence_Fast that ''.join() would do.
        return b"".join(list(self.incremental_serialize(packet)))

    @abstractmethod
    def incremental_serialize(self, packet: _T_contra) -> Generator[bytes, None, None]:
        raise NotImplementedError

    def incremental_serialize_to(self, file: IO[bytes], packet: _T_contra) -> None:
        assert file.writable()
        write = file.write
        for chunk in self.incremental_serialize(packet):
            write(chunk)


@runtime_checkable
class NetworkPacketIncrementalDeserializer(NetworkPacketDeserializer[_T_co], Protocol[_T_co]):
    def deserialize(self, data: bytes) -> _T_co:
        consumer: Generator[None, bytes, tuple[_T_co, bytes]] = self.incremental_deserialize()
        consumer_start(consumer)
        packet: _T_co
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
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_T_co, bytes]]:
        raise NotImplementedError


@runtime_checkable
class StreamNetworkProtocol(
    NetworkPacketIncrementalSerializer[_T_contra],
    NetworkPacketIncrementalDeserializer[_T_co],
    NetworkProtocol[_T_contra, _T_co],
    Protocol[_T_contra, _T_co],
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


class AutoSeparatedPacketSerializer(_BaseAutoSeparatedPacket, NetworkPacketIncrementalSerializer[_T_contra]):
    @abstractmethod
    def serialize(self, packet: _T_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _T_contra) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        separator: bytes = self.separator
        data = data.rstrip(separator)
        if separator in data:
            raise ValidationError(f"{separator!r} separator found in serialized packet {packet!r} and is not at the end")
        yield data + separator

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: _T_contra) -> None:
        return NetworkPacketIncrementalSerializer.incremental_serialize_to(self, file, packet)


class AutoSeparatedPacketDeserializer(_BaseAutoSeparatedPacket, NetworkPacketIncrementalDeserializer[_T_co]):
    @abstractmethod
    def deserialize(self, data: bytes) -> _T_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_T_co, bytes]]:
        buffer: bytes = b""
        separator: bytes = self.separator
        keepends: bool = self.keepends
        while True:
            buffer += yield
            if separator not in buffer:
                continue
            data, _, buffer = buffer.partition(separator)
            if keepends:
                data += separator
            try:
                packet = self.deserialize(data)
            except ValidationError:
                continue
            else:
                return (packet, buffer)
            finally:
                del data


class AutoSeparatedStreamNetworkProtocol(
    AutoSeparatedPacketSerializer[_T_contra],
    AutoSeparatedPacketDeserializer[_T_co],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co],
):
    pass


class _BaseAutoParsedPacket(metaclass=ProtocolObjectMeta):
    MAGIC: Final[bytes] = b"\x7f\x1b\xea\xff"
    header: Final[Struct] = Struct("!4sI")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class AutoParsedPacketSerializer(_BaseAutoParsedPacket, NetworkPacketIncrementalSerializer[_T_contra]):
    @abstractmethod
    def serialize(self, packet: _T_contra) -> bytes:
        raise NotImplementedError

    @final
    def incremental_serialize(self, packet: _T_contra) -> Generator[bytes, None, None]:
        data: bytes = self.serialize(packet)
        header: bytes = self.header.pack(self.__class__.MAGIC, len(data))
        yield header
        yield data
        checksum = hashlib.md5(usedforsecurity=False)
        checksum.update(header)
        checksum.update(data)
        yield checksum.digest()

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: _T_contra) -> None:
        return NetworkPacketIncrementalSerializer.incremental_serialize_to(self, file, packet)


class AutoParsedPacketDeserializer(_BaseAutoParsedPacket, NetworkPacketIncrementalDeserializer[_T_co]):
    @abstractmethod
    def deserialize(self, data: bytes) -> _T_co:
        raise NotImplementedError

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_T_co, bytes]]:
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
                        packet: _T_co = self.deserialize(body)
                    except ValidationError:
                        pass
                    else:
                        return (packet, buffer.read())
                    finally:
                        del body, checksum_digest
                finally:
                    del checksum
                header = buffer.read()
            finally:
                del buffer


class AutoParsedStreamNetworkProtocol(
    AutoParsedPacketSerializer[_T_contra],
    AutoParsedPacketDeserializer[_T_co],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co],
):
    pass


class StreamNetworkPacketHandler(Generic[_T_contra, _T_co], Object):
    __slots__ = (
        "__serializer",
        "__deserializer",
        "__incremental_deserialize",
    )

    def __init__(
        self,
        serializer: NetworkPacketIncrementalSerializer[_T_contra],
        deserializer: NetworkPacketIncrementalDeserializer[_T_co],
    ) -> None:
        super().__init__()
        assert isinstance(serializer, NetworkPacketIncrementalSerializer)
        assert isinstance(deserializer, NetworkPacketIncrementalDeserializer)
        self.__serializer: NetworkPacketIncrementalSerializer[_T_contra] = serializer
        self.__deserializer: NetworkPacketIncrementalDeserializer[_T_co] = deserializer
        self.__incremental_deserialize: Generator[None, bytes, tuple[_T_co, bytes]] | None = None

    def produce(self, packet: _T_contra) -> Generator[bytes, None, None]:
        return (yield from self.__serializer.incremental_serialize(packet))

    def write(self, file: IO[bytes], packet: _T_contra) -> None:
        return self.__serializer.incremental_serialize_to(file, packet)

    def consume(self, chunk: bytes) -> Generator[_T_co, None, None]:
        assert isinstance(chunk, bytes)
        if not chunk:
            return

        incremental_deserialize = self.__incremental_deserialize
        self.__incremental_deserialize = None

        while chunk:
            if incremental_deserialize is None:
                incremental_deserialize = self.__deserializer.incremental_deserialize()
                consumer_start(incremental_deserialize)
            packet: _T_co
            try:
                incremental_deserialize.send(chunk)
            except StopIteration as exc:
                incremental_deserialize = None
                packet, chunk = exc.value
            else:
                break
            yield packet  # yield out of exception clause, in order to erase the StopIteration except context

        self.__incremental_deserialize = incremental_deserialize
