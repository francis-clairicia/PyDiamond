# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Stream network packet protocol handler module"""

from __future__ import annotations

__all__ = [
    "StreamNetworkDataConsumer",
    "StreamNetworkDataProducer",
]

from collections import deque
from threading import RLock
from typing import Generator, Generic, Iterator, TypeVar

from ...system.object import Object, final
from ...system.utils.itertools import consumer_start, send_return
from ..protocol.stream import (
    IncrementalDeserializeError,
    NetworkPacketIncrementalDeserializer,
    NetworkPacketIncrementalSerializer,
)

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@final
class StreamNetworkDataProducer(Generic[_ST_contra], Object):
    __slots__ = ("__s", "__q", "__b", "__lock")

    def __init__(self, serializer: NetworkPacketIncrementalSerializer[_ST_contra], *, lock: RLock | None = None) -> None:
        super().__init__()
        assert isinstance(serializer, NetworkPacketIncrementalSerializer)
        self.__s: NetworkPacketIncrementalSerializer[_ST_contra] = serializer
        self.__q: deque[Generator[bytes, None, None]] = deque()
        self.__b: bytes = b""
        self.__lock: RLock = lock or RLock()

    def __bool__(self) -> bool:
        return bool(self.__b) or bool(self.__q)

    def read(self, bufsize: int = -1) -> bytes:
        if bufsize == 0:
            return b""
        data: bytes = self.__b
        with self.__lock:
            queue: deque[Generator[bytes, None, None]] = self.__q

            if bufsize < 0:
                while queue:
                    generator = queue[0]
                    try:
                        for chunk in generator:
                            data += chunk
                    except BaseException:
                        self.__b = data
                        raise
                    finally:
                        del queue[0], generator
                self.__b = b""
                return data

            while len(data) < bufsize and queue:
                generator = queue[0]
                try:
                    while not (chunk := next(generator)):  # Empty bytes are useless
                        continue
                    data += chunk
                except StopIteration:
                    del queue[0]
                except BaseException:
                    self.__b = data
                    raise
                finally:
                    del generator
            self.__b = data[bufsize:]
            return data[:bufsize]

    def queue(self, *packets: _ST_contra) -> None:
        if not packets:
            return
        with self.__lock:
            self.__q.extend(map(self.__s.incremental_serialize, packets))


@final
class StreamNetworkDataConsumer(Iterator[_DT_co], Generic[_DT_co], Object):
    __slots__ = ("__d", "__b", "__c", "__u", "__lock")

    def __init__(self, deserializer: NetworkPacketIncrementalDeserializer[_DT_co], *, lock: RLock | None = None) -> None:
        super().__init__()
        assert isinstance(deserializer, NetworkPacketIncrementalDeserializer)
        self.__d: NetworkPacketIncrementalDeserializer[_DT_co] = deserializer
        self.__c: Generator[None, bytes, tuple[_DT_co, bytes]] | None = None
        self.__b: bytes = b""
        self.__u: bytes = b""
        self.__lock: RLock = lock or RLock()

    def __next__(self) -> _DT_co:
        with self.__lock:
            chunk, self.__b = self.__b, b""
            if chunk:
                consumer, self.__c = self.__c, None
                if consumer is None:
                    consumer = self.__d.incremental_deserialize()
                    consumer_start(consumer)
                packet: _DT_co
                try:
                    packet, chunk = send_return(consumer, chunk)
                except IncrementalDeserializeError as exc:
                    self.__u = b""
                    self.__b = exc.remaining_data
                except StopIteration:
                    self.__u += chunk
                    self.__c = consumer
                except BaseException:
                    self.__u = b""
                    raise
                else:
                    self.__u = b""
                    self.__b = chunk
                    return packet
            raise StopIteration

    def oneshot(self) -> list[_DT_co]:
        with self.__lock:
            return list(self)

    def feed(self, chunk: bytes) -> None:
        assert isinstance(chunk, bytes)
        if not chunk:
            return
        with self.__lock:
            self.__b += chunk

    def get_buffer(self) -> bytes:
        with self.__lock:
            return self.__b

    def get_unconsumed_data(self) -> bytes:
        with self.__lock:
            return self.__u + self.__b
