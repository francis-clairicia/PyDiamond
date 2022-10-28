# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network client module"""

from __future__ import annotations

__all__ = ["AbstractNetworkClient", "TCPNetworkClient", "UDPNetworkClient"]

from abc import abstractmethod
from collections import deque
from contextlib import contextmanager
from io import DEFAULT_BUFFER_SIZE
from selectors import EVENT_READ, SelectSelector as _Selector
from socket import socket as Socket
from threading import RLock
from typing import TYPE_CHECKING, Any, Generator, Generic, Iterator, TypeAlias, TypeVar, overload

from ..system.object import Object, final
from ..system.utils.abc import concreteclass
from .protocol.abc import NetworkProtocol, ValidationError
from .protocol.pickle import PickleNetworkProtocol
from .protocol.stream import StreamNetworkProtocol
from .socket import SHUT_WR, AddressFamily, SocketAddress, create_connection, guess_best_buffer_size, new_socket_address
from .tools.stream import StreamNetworkDataConsumer, StreamNetworkPacketWriter

_T = TypeVar("_T")
_ReceivedPacketT = TypeVar("_ReceivedPacketT")
_SentPacketT = TypeVar("_SentPacketT")


_Address: TypeAlias = tuple[str, int] | tuple[str, int, int, int]  # type: ignore[misc]
# False positive, see https://github.com/python/mypy/issues/11098


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
        "__buffer_recv",
        "__lock",
        "__chunk_size",
        "__writer",
        "__consumer",
        "__peer",
    )

    @overload
    def __init__(
        self,
        address: tuple[str, int],
        /,
        *,
        timeout: float | None = ...,
        family: int | None = ...,
        source_address: tuple[bytearray | bytes | str, int] | None = ...,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: Socket,
        /,
        *,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        give: bool = ...,
    ) -> None:
        ...

    def __init__(
        self,
        arg: Socket | tuple[str, int],
        /,
        *,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT] | None = None,
        **kwargs: Any,
    ) -> None:
        if protocol is None:
            protocol = PickleNetworkProtocol[_SentPacketT, _ReceivedPacketT]()
        elif not isinstance(protocol, StreamNetworkProtocol):
            raise TypeError("Invalid argument")
        socket: Socket
        self.__owner: bool
        if isinstance(arg, Socket):
            give: bool = kwargs.pop("give", False)
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = arg
            self.__owner = bool(give)
        elif isinstance(arg, tuple):
            address: tuple[str, int] = arg
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
        self.__writer: StreamNetworkPacketWriter[_SentPacketT] = StreamNetworkPacketWriter(
            socket.makefile("wb", buffering=self.__chunk_size),  # type: ignore[arg-type]
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
            if self.__closed:
                return
            self.__closed = True
            self.__writer.close()
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

    def send_packet(self, packet: _SentPacketT) -> None:
        self._check_not_closed()
        self.__writer.write(packet)

    def send_packets(self, *packets: _SentPacketT) -> None:
        self._check_not_closed()
        self.__writer.write(*packets)

    def recv_packet(self) -> _ReceivedPacketT:
        self._check_not_closed()
        with self.__lock:
            while True:
                try:
                    return next(self.__consumer)
                except StopIteration:
                    pass
                self.__read_socket(timeout=None)

    @overload
    def recv_packet_no_block(self, *, default: None = ..., timeout: int = ...) -> _ReceivedPacketT | None:
        ...

    @overload
    def recv_packet_no_block(self, *, default: _T, timeout: int = ...) -> _ReceivedPacketT | _T:
        ...

    def recv_packet_no_block(self, *, default: Any = None, timeout: int = 0) -> Any:
        timeout = int(timeout)
        self._check_not_closed()
        with self.__lock:
            self.__read_socket(timeout=timeout)
            return next(self.__consumer, default)

    def recv_packets(self, *, timeout: int | None = None) -> Generator[_ReceivedPacketT, None, None]:
        self._check_not_closed()
        with self.__lock:
            self.__read_socket(timeout=timeout)
            yield from self.__consumer

    def __read_socket(self, *, timeout: int | None) -> None:
        socket: Socket = self.__socket
        chunk_size: int = self.__chunk_size
        if timeout is None and self.__consumer.get_buffer():
            timeout = 0
        with _Selector() as selector, _remove_timeout(socket):
            selector.register(socket, EVENT_READ)
            while selector.select(timeout=timeout):
                timeout = 0  # Future select() must exit quickly
                chunk: bytes = socket.recv(chunk_size)
                if not chunk:
                    if self.__consumer.get_buffer():
                        # consumer.feed() has been called
                        # The next read_socket() will raise an EOFError
                        return
                    raise EOFError("Closed connection")
                self.__consumer.feed(chunk)

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
        socket = Socket(fileno=fd)
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
    )

    @overload
    def __init__(
        self,
        /,
        *,
        family: int = ...,
        source_address: tuple[bytearray | bytes | str, int] | None = ...,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        max_packet_size: int | None = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: Socket,
        /,
        *,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] = ...,
        give: bool = ...,
        max_packet_size: int | None = ...,
    ) -> None:
        ...

    def __init__(
        self,
        socket: Socket | None = None,
        /,
        *,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT] | None = None,
        max_packet_size: int | None = None,
        **kwargs: Any,
    ) -> None:
        self.__protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT]
        if protocol is None:
            protocol = PickleNetworkProtocol[_SentPacketT, _ReceivedPacketT]()
        elif not isinstance(protocol, NetworkProtocol):
            raise TypeError("Invalid argument")
        self.__protocol = protocol

        from socket import AF_INET, SOCK_DGRAM

        if isinstance(socket, Socket):
            give: bool = kwargs.pop("give", False)
            if kwargs:
                raise TypeError("Invalid arguments")
            self.__owner = bool(give)
        elif socket is None:
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
        else:
            raise TypeError("Invalid arguments")

        if socket.type != SOCK_DGRAM:
            raise ValueError("Invalid socket type")

        if max_packet_size is None:
            max_packet_size = DEFAULT_BUFFER_SIZE

        self.__closed: bool = False
        self.__socket: Socket = socket
        self.__queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = deque()
        self.__lock: RLock = RLock()
        self.__max_packet_size: int = max_packet_size
        super().__init__()

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
        self._check_not_closed()
        with self.__lock:
            self.__socket.sendto(self.__protocol.serialize(packet), flags, address)

    def send_packets(self, address: _Address, *packets: _SentPacketT, flags: int = 0) -> None:
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
        self._check_not_closed()
        timeout = int(timeout)
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            self.__recv_packets(flags=flags, timeout=timeout)
            if not queue:
                return default
            return queue.popleft()

    def recv_packets(
        self,
        *,
        flags: int = 0,
        timeout: int | None = None,
    ) -> Generator[tuple[_ReceivedPacketT, SocketAddress], None, None]:
        self._check_not_closed()
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            self.__recv_packets(flags=flags, timeout=timeout)
            while queue:
                yield queue.popleft()

    def __recv_packets(self, flags: int, timeout: int | None) -> None:
        socket: Socket = self.__socket
        bufsize: int = self.__max_packet_size
        deserialize = self.__protocol.deserialize
        queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue

        if timeout is None and queue:
            timeout = 0
        with _Selector() as selector, _remove_timeout(socket):
            selector.register(socket, EVENT_READ)
            while selector.select(timeout=timeout):
                timeout = 0  # Future select() must exit quickly
                data, sender = socket.recvfrom(bufsize, flags)
                if not data:
                    continue
                try:
                    packet: _ReceivedPacketT = deserialize(data)
                except ValidationError:
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
        socket = Socket(fileno=fd)
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
    def closed(self) -> bool:
        return self.__closed


@contextmanager
def _remove_timeout(socket: Socket) -> Iterator[None]:
    timeout: float | None = socket.gettimeout()
    if timeout is None:
        yield
        return
    socket.settimeout(None)
    try:
        yield
    finally:
        socket.settimeout(timeout)
