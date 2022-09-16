# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network client module"""

from __future__ import annotations

__all__ = ["AbstractNetworkClient", "DisconnectedClientError", "TCPClientError", "TCPNetworkClient", "UDPNetworkClient"]


import os
from abc import abstractmethod
from collections import deque
from contextlib import suppress
from io import DEFAULT_BUFFER_SIZE
from selectors import EVENT_READ, SelectSelector as _Selector
from threading import RLock
from typing import TYPE_CHECKING, Any, Generator, Generic, TypeVar, overload

from ..system.object import Object, final
from ..system.utils.abc import concreteclass, concreteclasscheck
from .protocol.base import NetworkProtocol, ValidationError
from .protocol.pickle import PickleNetworkProtocol
from .protocol.stream import StreamNetworkDataConsumer, StreamNetworkPacketWriter, StreamNetworkProtocol
from .socket.base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractUDPClientSocket,
    AbstractUDPSocket,
    ReceivedDatagram,
    SocketAddress,
)
from .socket.constants import SHUT_WR
from .socket.python import PythonTCPClientSocket, PythonUDPClientSocket

_T = TypeVar("_T")
_ReceivedPacketT = TypeVar("_ReceivedPacketT")
_SentPacketT = TypeVar("_SentPacketT")


class AbstractNetworkClient(Object):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractNetworkClient")

    def __enter__(self: __Self) -> __Self:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def getsockname(self) -> SocketAddress:
        raise NotImplementedError

    @abstractmethod
    def fileno(self) -> int:
        raise NotImplementedError


class TCPClientError(Exception):
    def __init__(self, client: TCPNetworkClient[Any, Any], message: str | None = None) -> None:
        if not message:
            if not client.is_connected():
                message = "Something went wrong for a client, and was disconnected"
            else:
                addr: SocketAddress = client.getsockname()
                message = f"Something went wrong for the client {addr.host}:{addr.port}"
        super().__init__(message)
        self.client: TCPNetworkClient[Any, Any] = client


class DisconnectedClientError(TCPClientError, ConnectionError):
    def __init__(self, client: TCPNetworkClient[Any, Any]) -> None:
        addr: SocketAddress = client.getsockname()
        super().__init__(client, f"{addr.host}:{addr.port} has been disconnected")


class NoValidPacket(ValueError):
    pass


@concreteclass
class TCPNetworkClient(AbstractNetworkClient, Generic[_SentPacketT, _ReceivedPacketT]):
    __slots__ = (
        "__socket",
        "__socket_cls",
        "__buffer_recv",
        "__queue",
        "__lock",
        "__chunk_size",
        "__writer",
        "__consumer",
    )

    @overload
    def __init__(
        self,
        address: tuple[str, int],
        /,
        *,
        family: int = ...,
        timeout: int = ...,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        socket_cls: type[AbstractTCPClientSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPClientSocket,
        /,
        *,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        give: bool = ...,
    ) -> None:
        ...

    def __init__(
        self,
        arg: AbstractTCPClientSocket | tuple[str, int],
        /,
        *,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT] | None = None,
        **kwargs: Any,
    ) -> None:
        if protocol is None:
            protocol = PickleNetworkProtocol[_SentPacketT, _ReceivedPacketT]()
        elif not isinstance(protocol, StreamNetworkProtocol):
            raise TypeError("Invalid argument")
        socket: AbstractTCPClientSocket
        self.__socket_cls: type[AbstractTCPClientSocket] | None
        if isinstance(arg, AbstractTCPClientSocket):
            give: bool = kwargs.pop("give", False)
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = arg
            self.__socket_cls = None if not give else type(socket)
        elif isinstance(arg, tuple):
            address: tuple[str, int] = arg
            socket_cls: type[AbstractTCPClientSocket] = kwargs.pop("socket_cls", PythonTCPClientSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.connect(address, **kwargs)
            self.__socket_cls = socket_cls
        else:
            raise TypeError("Invalid arguments")
        self.__socket: AbstractTCPClientSocket = socket
        self.__queue: deque[_ReceivedPacketT] = deque()
        self.__lock: RLock = RLock()
        self.__chunk_size: int = DEFAULT_BUFFER_SIZE
        with suppress(OSError):  # Will not work on Windows
            socket_stat = os.fstat(socket.fileno())
            blksize: int = getattr(socket_stat, "st_blksize", 0)
            if blksize > 0:
                self.__chunk_size = blksize
        self.__writer: StreamNetworkPacketWriter[_SentPacketT] = StreamNetworkPacketWriter(
            socket.makefile("wb", buffering=self.__chunk_size),
            protocol,
            lock=self.__lock,
        )
        self.__consumer: StreamNetworkDataConsumer[_ReceivedPacketT] = StreamNetworkDataConsumer(
            protocol,
            lock=self.__lock,
        )
        super().__init__()

    def close(self) -> None:
        with self.__lock:
            if self.__socket_cls is None:
                return
            self.__socket_cls = None
            socket: AbstractTCPClientSocket = self.__socket
            if socket.is_open():
                try:
                    socket.shutdown(SHUT_WR)
                except OSError:
                    pass
                finally:
                    socket.close()

    def send_packet(self, packet: _SentPacketT) -> None:
        try:
            self.__writer.write(packet)
            self.__writer.flush()
        except ConnectionError as exc:
            raise DisconnectedClientError(self) from exc

    def send_packets(self, *packets: _SentPacketT) -> None:
        if not packets:
            return
        with self.__lock:
            send = self.__writer.write
            try:
                for packet in packets:
                    send(packet)
                self.__writer.flush()
            except ConnectionError as exc:
                raise DisconnectedClientError(self) from exc

    def recv_packet(self, *, retry_on_fail: bool = True) -> _ReceivedPacketT:
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            while not queue:
                queue.extend(self.__recv_packets(timeout=None))
                if not retry_on_fail:
                    break
            if not queue:
                raise NoValidPacket
            return queue.popleft()

    @overload
    def recv_packet_no_block(self, *, default: None = ..., timeout: int = ...) -> _ReceivedPacketT | None:
        ...

    @overload
    def recv_packet_no_block(self, *, default: _T, timeout: int = ...) -> _ReceivedPacketT | _T:
        ...

    def recv_packet_no_block(self, *, default: Any = None, timeout: int = 0) -> Any:
        timeout = int(timeout)
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(timeout=timeout))
                if not queue:
                    return default
            return queue.popleft()

    def recv_packets(self, *, timeout: int | None = None) -> Generator[_ReceivedPacketT, None, None]:
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(timeout=timeout))
            while queue:
                yield queue.popleft()

    def __recv_packets(self, *, timeout: int | None) -> Generator[_ReceivedPacketT, None, None]:
        chunk_reader: Generator[bytes, None, None] = self.read_socket(self.__socket, self.__chunk_size, timeout=timeout)
        try:
            while True:
                try:
                    chunk: bytes | None = next(chunk_reader, None)
                except (ConnectionError, EOFError) as exc:
                    raise DisconnectedClientError(self) from exc
                if chunk is None:
                    break
                self.__consumer.feed(chunk)
                yield from self.__consumer
        finally:
            chunk_reader.close()

    @staticmethod
    @final
    def read_socket(
        socket: AbstractTCPClientSocket,
        chunk_size: int,
        *,
        timeout: int | None = None,
    ) -> Generator[bytes, None, None]:
        if chunk_size <= 0:
            return
        with _Selector() as selector, suppress(BlockingIOError):
            selector.register(socket, EVENT_READ)
            if timeout is not None and not selector.select(timeout=timeout):
                return
            data: bytes = socket.recv(chunk_size)
            if (length := len(data)) == 0:
                raise EOFError
            yield data
            while length >= chunk_size and selector.select(timeout=0):
                data = socket.recv(chunk_size)
                if (length := len(data)) == 0:
                    break
                yield data

    def has_saved_packets(self) -> bool:
        with self.__lock:
            return True if self.__queue else False

    def getsockname(self) -> SocketAddress:
        return self.__socket.getsockname()

    def getpeername(self) -> SocketAddress | None:
        return self.__socket.getpeername()

    def is_connected(self) -> bool:
        return self.__socket.is_connected()

    def getblocking(self) -> bool:
        return self.__socket.getblocking()

    def setblocking(self, flag: bool) -> None:
        return self.__socket.setblocking(flag)

    def fileno(self) -> int:
        return self.__socket.fileno()

    @overload
    def reconnect(self) -> None:
        ...

    @overload
    def reconnect(self, timeout: float | None) -> None:
        ...

    def reconnect(self, *args: Any, **kwargs: Any) -> None:
        return self.__socket.reconnect(*args, **kwargs)

    def try_reconnect(self, timeout: float | None = None) -> bool:
        return self.__socket.try_reconnect(timeout=timeout)


@concreteclass
class UDPNetworkClient(AbstractNetworkClient, Generic[_SentPacketT, _ReceivedPacketT]):
    __slots__ = (
        "__socket",
        "__socket_cls",
        "__protocol",
        "__queue",
        "__lock",
    )

    @overload
    def __init__(
        self,
        /,
        *,
        family: int = ...,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        socket_cls: AbstractUDPClientSocket = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPSocket,
        /,
        *,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        give: bool = ...,
    ) -> None:
        ...

    def __init__(
        self,
        socket: AbstractUDPSocket | None = None,
        /,
        *,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] | None = None,
        **kwargs: Any,
    ) -> None:
        self.__protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT]
        if protocol is None:
            protocol = PickleNetworkProtocol[_SentPacketT, _ReceivedPacketT]()
        elif not isinstance(protocol, NetworkProtocol):
            raise TypeError("Invalid argument")
        self.__protocol = protocol
        self.__socket_cls: type[AbstractUDPSocket] | None
        if isinstance(socket, AbstractUDPSocket):
            give: bool = kwargs.pop("give", False)
            if kwargs:
                raise TypeError("Invalid arguments")
            self.__socket_cls = None if not give else type(socket)
        elif socket is None:
            socket_cls: type[AbstractUDPClientSocket] = kwargs.pop("socket_cls", PythonUDPClientSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.create(**kwargs)
            self.__socket_cls = socket_cls
        else:
            raise TypeError("Invalid arguments")
        super().__init__()
        self.__socket: AbstractUDPSocket = socket
        self.__queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = deque()
        self.__lock: RLock = RLock()

    def close(self) -> None:
        with self.__lock:
            if self.__socket_cls is None:
                return
            self.__socket_cls = None
            socket: AbstractSocket = self.__socket
            if socket.is_open():
                socket.close()

    def send_packet(self, address: SocketAddress, packet: _SentPacketT, *, flags: int = 0) -> None:
        with self.__lock:
            self.__socket.sendto(self.__protocol.serialize(packet), address, flags=flags)

    def send_packets(self, address: SocketAddress, *packets: _SentPacketT, flags: int = 0) -> None:
        if not packets:
            return
        with self.__lock:
            sendto = self.__socket.sendto
            for data in map(self.__protocol.serialize, packets):
                sendto(data, address, flags=flags)

    def recv_packet(self, *, flags: int = 0, retry_on_fail: bool = True) -> tuple[_ReceivedPacketT, SocketAddress]:
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            while not queue:
                queue.extend(self.__recv_packets(flags=flags, timeout=None))
                if not retry_on_fail:
                    break
            if not queue:
                raise NoValidPacket
            return queue.popleft()

    @overload
    def recv_packet_no_block(
        self, *, flags: int = 0, default: None = ..., timeout: int = ...
    ) -> tuple[_ReceivedPacketT, SocketAddress] | None:
        ...

    @overload
    def recv_packet_no_block(
        self, *, flags: int = 0, default: _T, timeout: int = ...
    ) -> tuple[_ReceivedPacketT, SocketAddress] | _T:
        ...

    def recv_packet_no_block(self, *, flags: int = 0, default: Any = None, timeout: int = 0) -> Any:
        timeout = int(timeout)
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, timeout=timeout))
                if not queue:
                    return default
            return queue.popleft()

    def recv_packets(
        self,
        *,
        flags: int = 0,
        timeout: int | None = None,
    ) -> Generator[tuple[_ReceivedPacketT, SocketAddress], None, None]:
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, timeout=timeout))
            while queue:
                yield queue.popleft()

    def __recv_packets(self, flags: int, timeout: int | None) -> Generator[tuple[_ReceivedPacketT, SocketAddress], None, None]:
        deserialize = self.__protocol.deserialize

        chunk_generator = self.read_socket(self.__socket, timeout=timeout, flags=flags)

        for data, sender in chunk_generator:
            try:
                try:
                    packet: _ReceivedPacketT = deserialize(data)
                except ValidationError:
                    continue
                yield (packet, sender)
            except BaseException:
                chunk_generator.close()
                raise

    @staticmethod
    def read_socket(
        socket: AbstractUDPSocket,
        *,
        timeout: int | None = None,
        flags: int = 0,
    ) -> Generator[ReceivedDatagram, None, None]:
        with _Selector() as selector, suppress(BlockingIOError):
            selector.register(socket, EVENT_READ)
            if timeout is not None and not selector.select(timeout=0):
                return
            yield socket.recvfrom(flags=flags)
            while selector.select(timeout=0):
                yield socket.recvfrom(flags=flags)

    def has_saved_packets(self) -> bool:
        with self.__lock:
            return True if self.__queue else False

    def getsockname(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    def fileno(self) -> int:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.fileno()
