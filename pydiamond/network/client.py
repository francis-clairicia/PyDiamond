# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
# mypy: no-warn-unused-ignores
"""Network client module"""

from __future__ import annotations

__all__ = ["AbstractNetworkClient", "TCPNetworkClient", "UDPNetworkClient"]

from abc import abstractmethod
from collections import deque
from contextlib import contextmanager
from selectors import EVENT_READ
from socket import socket as Socket
from threading import RLock
from typing import TYPE_CHECKING, Any, Generic, Iterator, TypeAlias, TypeVar, overload

try:
    from selectors import PollSelector as _Selector  # type: ignore[attr-defined]
except ImportError:
    from selectors import SelectSelector as _Selector  # type: ignore[misc]

from ..system.object import Object, final
from ..system.utils.abc import concreteclass
from .protocol.abc import NetworkProtocol
from .protocol.exceptions import DeserializeError
from .protocol.stream.abc import StreamNetworkProtocol
from .socket import SHUT_WR, AddressFamily, SocketAddress, create_connection, guess_best_buffer_size, new_socket_address
from .tools.stream import StreamNetworkDataConsumer, StreamNetworkDataProducer

_T = TypeVar("_T")
_ReceivedPacketT = TypeVar("_ReceivedPacketT")
_SentPacketT = TypeVar("_SentPacketT")


_Address: TypeAlias = tuple[str, int] | tuple[str, int, int, int]  # type: ignore[misc]
# False positive, see https://github.com/python/mypy/issues/11098


_NO_DEFAULT: Any = object()


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

    @abstractmethod
    def dup(self) -> Socket:
        raise NotImplementedError

    @abstractmethod
    def detach(self) -> Socket:
        raise NotImplementedError


@concreteclass
class TCPNetworkClient(AbstractNetworkClient, Generic[_SentPacketT, _ReceivedPacketT]):
    __slots__ = (
        "__socket",
        "__owner",
        "__closed",
        "__lock",
        "__chunk_size",
        "__producer",
        "__consumer",
        "__peer",
        "__default_send_flags",
        "__default_recv_flags",
    )

    @overload
    def __init__(
        self,
        address: tuple[str, int],
        /,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT],
        *,
        timeout: float | None = ...,
        family: int | None = ...,
        source_address: tuple[bytearray | bytes | str, int] | None = ...,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: Socket,
        /,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT],
        *,
        give: bool = ...,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: Socket | tuple[str, int],
        /,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT],
        *,
        send_flags: int = 0,
        recv_flags: int = 0,
        **kwargs: Any,
    ) -> None:
        if not isinstance(protocol, StreamNetworkProtocol):
            raise TypeError("Invalid argument")
        send_flags = int(send_flags)
        recv_flags = int(recv_flags)
        socket: Socket

        super().__init__()

        self.__owner: bool
        if isinstance(__arg, Socket):
            give: bool = kwargs.pop("give", False)
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = __arg
            self.__owner = bool(give)
        elif isinstance(__arg, tuple):
            address: tuple[str, int] = __arg
            socket = create_connection(address, **kwargs)
            self.__owner = True
        else:
            raise TypeError("Invalid arguments")

        from socket import SOCK_STREAM

        if socket.type != SOCK_STREAM:
            raise ValueError("Invalid socket type")

        self.__peer: tuple[Any, ...] = socket.getpeername()
        self.__closed: bool = False
        self.__socket: Socket = socket
        self.__lock: RLock = RLock()
        self.__chunk_size: int = guess_best_buffer_size(socket)
        self.__producer: StreamNetworkDataProducer[_SentPacketT] = StreamNetworkDataProducer(protocol)
        self.__consumer: StreamNetworkDataConsumer[_ReceivedPacketT] = StreamNetworkDataConsumer(protocol)
        self.__default_send_flags: int = send_flags
        self.__default_recv_flags: int = recv_flags

    def close(self) -> None:
        with self.__lock:
            if self.__closed:
                return
            self.__closed = True
            socket: Socket = self.__socket
            del self.__socket
            if not self.__owner:
                return
            try:
                socket.shutdown(SHUT_WR)
            except OSError:
                pass
            finally:
                socket.close()

    def send_packet(self, packet: _SentPacketT, *, timeout: float | None = None, flags: int = 0) -> None:
        self._check_not_closed()
        with self.__lock:
            self.__producer.queue(packet)
            self.__write_on_socket(timeout=timeout, flags=flags)

    def send_packets(self, *packets: _SentPacketT, timeout: float | None = None, flags: int = 0) -> None:
        self._check_not_closed()
        if not packets:
            return
        with self.__lock:
            self.__producer.queue(*packets)
            self.__write_on_socket(timeout=timeout, flags=flags)

    def __write_on_socket(self, *, timeout: float | None, flags: int) -> None:
        if timeout is not None:
            if timeout < 0:
                raise ValueError("Timeout out of range")
            if timeout == 0:
                raise ValueError("non-blocking sockets are not supported")

        flags |= self.__default_send_flags

        data: bytes = self.__producer.read(-1)
        if not data:
            return
        socket: Socket = self.__socket
        with _use_timeout(socket, timeout):
            socket.sendall(data, flags)

    def recv_packet(self, *, flags: int = 0) -> _ReceivedPacketT:
        self._check_not_closed()
        with self.__lock:
            while True:
                try:
                    return next(self.__consumer)
                except StopIteration:
                    pass
                self.__read_socket(timeout=None, flags=flags)

    @overload
    def recv_packet_no_block(self, *, timeout: float = ..., flags: int = ...) -> _ReceivedPacketT:
        ...

    @overload
    def recv_packet_no_block(self, *, default: _T, timeout: float = ..., flags: int = ...) -> _ReceivedPacketT | _T:
        ...

    def recv_packet_no_block(self, *, default: Any = _NO_DEFAULT, timeout: float = 0, flags: int = 0) -> Any:
        timeout = float(timeout)
        self._check_not_closed()
        with self.__lock:
            try:
                return next(self.__consumer)
            except StopIteration:
                pass
            self.__read_socket(timeout=timeout, flags=flags)
            try:
                return next(self.__consumer)
            except StopIteration:
                pass
            if default is not _NO_DEFAULT:
                return default
            raise TimeoutError("recv_packet() timed out")

    def recv_packets(self, *, timeout: float | None = 0, flags: int = 0) -> list[_ReceivedPacketT]:
        self._check_not_closed()
        with self.__lock:
            if timeout is not None:
                self.__read_socket(timeout=timeout, flags=flags)
                return self.__consumer.oneshot()
            while not (packets := self.__consumer.oneshot()):
                self.__read_socket(timeout=None, flags=flags)
            return packets

    def __read_socket(self, *, timeout: float | None, flags: int) -> None:
        flags |= self.__default_recv_flags
        if timeout is not None and timeout < 0:
            raise ValueError("Timeout out of range")

        socket: Socket = self.__socket
        socket_recv = socket.recv
        chunk_size: int = self.__chunk_size
        consumer = self.__consumer
        consumer_feed = consumer.feed
        if consumer.get_buffer():
            timeout = 0
        with _Selector() as selector, _remove_timeout(socket):
            selector.register(socket, EVENT_READ)
            select = selector.select
            while timeout is None or select(timeout=timeout):
                timeout = 0  # Future select() must exit quickly
                chunk: bytes = socket_recv(chunk_size, flags)
                if not chunk:
                    if consumer.get_buffer():
                        # consumer.feed() has been called
                        # The next read_socket() will raise an EOFError
                        return
                    raise EOFError("Closed connection")
                consumer_feed(chunk)

    def getsockname(self) -> SocketAddress:
        self._check_not_closed()
        return new_socket_address(self.__socket.getsockname(), self.__socket.family)

    def getpeername(self) -> SocketAddress | None:
        self._check_not_closed()
        try:
            return new_socket_address(self.__socket.getpeername(), self.__socket.family)
        except OSError:
            return None

    def is_connected(self) -> bool:
        if self.__closed:
            return False
        try:
            self.__socket.getpeername()
        except OSError:
            return False
        return True

    def fileno(self) -> int:
        if self.__closed:
            return -1
        return self.__socket.fileno()

    def dup(self) -> Socket:
        self._check_not_closed()
        socket: Socket = self.__socket
        return socket.dup()

    def detach(self) -> Socket:
        self._check_not_closed()
        socket: Socket = self.__socket
        fd: int = socket.detach()
        if fd < 0:
            raise OSError("Closed socket")
        socket = Socket(socket.family, socket.type, socket.proto, fileno=fd)
        try:
            self.__owner = False
            self.close()
        except BaseException:
            socket.close()
            raise
        return socket

    @overload
    def getsockopt(self, __level: int, __optname: int, /) -> int:
        ...

    @overload
    def getsockopt(self, __level: int, __optname: int, __buflen: int, /) -> bytes:
        ...

    def getsockopt(self, *args: int) -> int | bytes:
        self._check_not_closed()
        return self.__socket.getsockopt(*args)

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: int | bytes, /) -> None:
        ...

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: None, __optlen: int, /) -> None:
        ...

    def setsockopt(self, *args: Any) -> None:
        self._check_not_closed()
        return self.__socket.setsockopt(*args)

    def reconnect(self, timeout: float | None = None) -> None:
        self._check_not_closed()
        socket: Socket = self.__socket
        try:
            socket.getpeername()
        except OSError:
            pass
        else:
            return
        address: tuple[Any, ...] = self.__peer
        former_timeout = socket.gettimeout()
        socket.settimeout(timeout)
        try:
            socket.connect(address)
        finally:
            socket.settimeout(former_timeout)

    def try_reconnect(self, timeout: float | None = None) -> bool:
        try:
            self.reconnect(timeout=timeout)
        except OSError:
            return False
        return True

    @final
    def _get_buffer(self) -> bytes:
        return self.__consumer.get_unconsumed_data()

    @final
    def _check_not_closed(self) -> None:
        if self.__closed:
            raise RuntimeError("Closed client")

    @property
    @final
    def default_send_flags(self) -> int:
        return self.__default_send_flags

    @property
    @final
    def default_recv_flags(self) -> int:
        return self.__default_recv_flags

    @property
    @final
    def closed(self) -> bool:
        return self.__closed


@concreteclass
class UDPNetworkClient(AbstractNetworkClient, Generic[_SentPacketT, _ReceivedPacketT]):
    __slots__ = (
        "__socket",
        "__owner",
        "__closed",
        "__protocol",
        "__queue",
        "__lock",
        "__max_packet_size",
        "__default_send_flags",
        "__default_recv_flags",
    )

    @overload
    def __init__(
        self,
        /,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT],
        *,
        family: int = ...,
        source_address: tuple[bytearray | bytes | str, int] | None = ...,
        max_packet_size: int = ...,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        /,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT],
        *,
        socket: Socket,
        give: bool = ...,
        max_packet_size: int = ...,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    def __init__(
        self,
        /,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT],
        *,
        max_packet_size: int = 0,
        send_flags: int = 0,
        recv_flags: int = 0,
        **kwargs: Any,
    ) -> None:
        send_flags = int(send_flags)
        recv_flags = int(recv_flags)

        if not isinstance(protocol, NetworkProtocol):
            raise TypeError("Invalid argument")

        super().__init__()

        self.__protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] = protocol

        from socket import AF_INET, SOCK_DGRAM

        socket: Socket
        if "socket" in kwargs:
            socket = kwargs.pop("socket")
            if not isinstance(socket, Socket):
                raise TypeError("Invalid arguments")
            give: bool = kwargs.pop("give", False)
            if kwargs:
                raise TypeError("Invalid arguments")
            self.__owner = bool(give)
        else:
            family = AddressFamily(kwargs.pop("family", AF_INET))
            source_address: tuple[bytearray | bytes | str, int] | None = kwargs.pop("source_address", None)
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = Socket(family, SOCK_DGRAM)
            if source_address is None:
                socket.bind(("", 0))
            else:
                socket.bind(source_address)
            self.__owner = True

        if socket.type != SOCK_DGRAM:
            raise ValueError("Invalid socket type")

        if max_packet_size <= 0:
            max_packet_size = 8192

        self.__closed: bool = False
        self.__socket: Socket = socket
        self.__queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = deque()
        self.__lock: RLock = RLock()
        self.__max_packet_size: int = max_packet_size
        self.__default_send_flags: int = send_flags
        self.__default_recv_flags: int = recv_flags

    def close(self) -> None:
        with self.__lock:
            if self.__closed:
                return
            self.__closed = True
            socket: Socket = self.__socket
            del self.__socket
            if not self.__owner:
                return
            socket.close()

    def send_packet(self, address: _Address, packet: _SentPacketT, *, flags: int = 0) -> None:
        flags |= self.__default_send_flags
        self._check_not_closed()
        with self.__lock:
            self.__socket.sendto(self.__protocol.serialize(packet), flags, address)

    def send_packets(self, address: _Address, *packets: _SentPacketT, flags: int = 0) -> None:
        flags |= self.__default_send_flags
        self._check_not_closed()
        if not packets:
            return
        with self.__lock:
            sendto = self.__socket.sendto
            for data in map(self.__protocol.serialize, packets):
                sendto(data, flags, address)

    def recv_packet(self, *, flags: int = 0) -> tuple[_ReceivedPacketT, SocketAddress]:
        self._check_not_closed()
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            while not queue:
                self.__recv_packets(flags=flags, timeout=None)
            return queue.popleft()

    @overload
    def recv_packet_no_block(self, *, flags: int = 0, timeout: float = ...) -> tuple[_ReceivedPacketT, SocketAddress]:
        ...

    @overload
    def recv_packet_no_block(
        self, *, flags: int = 0, default: _T, timeout: float = ...
    ) -> tuple[_ReceivedPacketT, SocketAddress] | _T:
        ...

    def recv_packet_no_block(self, *, flags: int = 0, default: Any = _NO_DEFAULT, timeout: float = 0) -> Any:
        self._check_not_closed()
        timeout = float(timeout)
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if not queue:
                self.__recv_packets(flags=flags, timeout=timeout)
                if not queue:
                    if default is not _NO_DEFAULT:
                        return default
                    raise TimeoutError("recv_packet() timed out")
            return queue.popleft()

    def recv_packets(
        self,
        *,
        flags: int = 0,
        timeout: float | None = 0,
    ) -> list[tuple[_ReceivedPacketT, SocketAddress]]:
        self._check_not_closed()
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if timeout is not None:
                self.__recv_packets(flags=flags, timeout=timeout)
            else:
                while not queue:
                    self.__recv_packets(flags=flags, timeout=None)
            packets = list(queue)
            queue.clear()
            return packets

    def __recv_packets(self, *, flags: int, timeout: float | None) -> None:
        flags |= self.__default_recv_flags
        if timeout is not None and timeout < 0:
            raise ValueError("Timeout out of range")

        socket: Socket = self.__socket
        bufsize: int = self.__max_packet_size
        deserialize = self.__protocol.deserialize
        queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue

        if queue:
            timeout = 0
        with _Selector() as selector, _remove_timeout(socket):
            selector.register(socket, EVENT_READ)
            while timeout is None or selector.select(timeout=timeout):
                timeout = 0  # Future select() must exit quickly
                data, sender = socket.recvfrom(bufsize, flags)
                if not data:
                    continue
                try:
                    packet: _ReceivedPacketT = deserialize(data)
                except DeserializeError:
                    continue
                queue.append((packet, new_socket_address(sender, socket.family)))

    def getsockname(self) -> SocketAddress:
        self._check_not_closed()
        return new_socket_address(self.__socket.getsockname(), self.__socket.family)

    def fileno(self) -> int:
        if self.__closed:
            return -1
        return self.__socket.fileno()

    def dup(self) -> Socket:
        self._check_not_closed()
        socket: Socket = self.__socket
        return socket.dup()

    def detach(self) -> Socket:
        self._check_not_closed()
        socket: Socket = self.__socket
        fd: int = socket.detach()
        if fd < 0:
            raise OSError("Closed socket")
        socket = Socket(socket.family, socket.type, socket.proto, fileno=fd)
        try:
            self.__owner = False
            self.close()
        except BaseException:
            socket.close()
            raise
        return socket

    @overload
    def getsockopt(self, __level: int, __optname: int, /) -> int:
        ...

    @overload
    def getsockopt(self, __level: int, __optname: int, __buflen: int, /) -> bytes:
        ...

    def getsockopt(self, *args: int) -> int | bytes:
        self._check_not_closed()
        return self.__socket.getsockopt(*args)

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: int | bytes, /) -> None:
        ...

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: None, __optlen: int, /) -> None:
        ...

    def setsockopt(self, *args: Any) -> None:
        self._check_not_closed()
        return self.__socket.setsockopt(*args)

    @final
    def _check_not_closed(self) -> None:
        if self.__closed:
            raise RuntimeError("Closed client")

    @property
    @final
    def default_send_flags(self) -> int:
        return self.__default_send_flags

    @property
    @final
    def default_recv_flags(self) -> int:
        return self.__default_recv_flags

    @property
    @final
    def closed(self) -> bool:
        return self.__closed


@contextmanager
def _remove_timeout(socket: Socket) -> Iterator[None]:
    timeout: float | None = socket.gettimeout()
    socket.settimeout(None)
    try:
        yield
    finally:
        socket.settimeout(timeout)


@contextmanager
def _use_timeout(socket: Socket, timeout: float | None) -> Iterator[None]:
    old_timeout: float | None = socket.gettimeout()
    socket.settimeout(timeout)
    try:
        yield
    finally:
        socket.settimeout(old_timeout)
