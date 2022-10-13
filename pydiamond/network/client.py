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


class NoValidPacket(ValueError):
    pass


@concreteclass
class TCPNetworkClient(AbstractNetworkClient, Generic[_SentPacketT, _ReceivedPacketT]):
    __slots__ = (
        "__socket",
        "__owner",
        "__closed",
        "__buffer_recv",
        "__queue",
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
        self.__queue: deque[_ReceivedPacketT] = deque()
        self.__lock: RLock = RLock()
        self.__chunk_size: int = guess_best_buffer_size(socket)
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
        self._check_closed()
        self.__writer.write(packet)
        self.__writer.flush()

    def send_packets(self, *packets: _SentPacketT) -> None:
        self._check_closed()
        if not packets:
            return
        with self.__lock:
            send = self.__writer.write
            for packet in packets:
                send(packet)
            self.__writer.flush()

    def recv_packet(self, *, retry_on_fail: bool = True) -> _ReceivedPacketT:
        self._check_closed()
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
        self._check_closed()
        timeout = int(timeout)
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(timeout=timeout))
                if not queue:
                    return default
            return queue.popleft()

    def recv_packets(self, *, timeout: int | None = None) -> Generator[_ReceivedPacketT, None, None]:
        self._check_closed()
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(timeout=timeout))
            while queue:
                yield queue.popleft()

    def __recv_packets(self, *, timeout: int | None) -> Generator[_ReceivedPacketT, None, None]:
        chunk_reader: Generator[bytes, None, None] = self.__read_socket(self.__socket, self.__chunk_size, timeout=timeout)
        try:
            while (chunk := next(chunk_reader, None)) is not None:
                self.__consumer.feed(chunk)
            yield from self.__consumer
        finally:
            chunk_reader.close()

    @staticmethod
    @final
    def __read_socket(
        socket: Socket,
        chunk_size: int,
        *,
        timeout: int | None = None,
    ) -> Generator[bytes, None, None]:
        if chunk_size <= 0:
            return
        with _Selector() as selector, _remove_timeout(socket):
            selector.register(socket, EVENT_READ)
            if not selector.select(timeout=timeout):
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
        self._check_closed()
        with self.__lock:
            return True if self.__queue else False

    def flush_queue(self) -> deque[_ReceivedPacketT]:
        with self.__lock:
            q = self.__queue.copy()
            self.__queue.clear()
            return q

    def getsockname(self) -> SocketAddress:
        self._check_closed()
        return new_socket_address(self.__socket.getsockname(), self.__socket.family)

    def getpeername(self) -> SocketAddress | None:
        self._check_closed()
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
        self._check_closed()
        socket: Socket = self.__socket
        return socket.dup()

    def detach(self) -> Socket:
        self._check_closed()
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
        self._check_closed()
        return self.__socket.getsockopt(*args)

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: int | bytes, /) -> None:
        ...

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: None, __optlen: int, /) -> None:
        ...

    def setsockopt(self, *args: Any) -> None:
        self._check_closed()
        return self.__socket.setsockopt(*args)

    def reconnect(self, timeout: float | None = None) -> None:
        self._check_closed()
        socket: Socket = self.__socket
        try:
            socket.getpeername()
        except OSError:
            pass
        else:
            return
        address: tuple[Any, ...] = self.__peer
        try:
            socket.settimeout(timeout)
            socket.connect(address)
        finally:
            if timeout is not None:
                socket.settimeout(None)

    def try_reconnect(self, timeout: float | None = None) -> bool:
        try:
            self.reconnect(timeout=timeout)
        except OSError:
            return False
        return True

    @final
    def _get_buffer(self) -> bytes:
        return self.__consumer.get_buffer()

    @final
    def _check_closed(self) -> None:
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
        self._check_closed()
        with self.__lock:
            self.__socket.sendto(self.__protocol.serialize(packet), flags, address)

    def send_packets(self, address: _Address, *packets: _SentPacketT, flags: int = 0) -> None:
        self._check_closed()
        if not packets:
            return
        with self.__lock:
            sendto = self.__socket.sendto
            for data in map(self.__protocol.serialize, packets):
                sendto(data, flags, address)

    def recv_packet(self, *, flags: int = 0, retry_on_fail: bool = True) -> tuple[_ReceivedPacketT, SocketAddress]:
        self._check_closed()
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
        self._check_closed()
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
        self._check_closed()
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, timeout=timeout))
            while queue:
                yield queue.popleft()

    def __recv_packets(self, flags: int, timeout: int | None) -> Generator[tuple[_ReceivedPacketT, SocketAddress], None, None]:
        deserialize = self.__protocol.deserialize

        chunk_generator = self.__read_socket(self.__socket, self.__max_packet_size, timeout=timeout, flags=flags)

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
    @final
    def __read_socket(
        socket: Socket,
        bufsize: int,
        *,
        timeout: int | None = None,
        flags: int = 0,
    ) -> Generator[tuple[bytes, SocketAddress], None, None]:
        def convert(recv: tuple[bytes, tuple[Any, ...]]) -> tuple[bytes, SocketAddress]:
            return recv[0], new_socket_address(recv[1], socket.family)

        with _Selector() as selector, _remove_timeout(socket):
            selector.register(socket, EVENT_READ)
            if timeout is not None and not selector.select(timeout=0):
                return
            yield convert(socket.recvfrom(bufsize, flags))
            while selector.select(timeout=0):
                yield convert(socket.recvfrom(bufsize, flags))

    def has_saved_packets(self) -> bool:
        self._check_closed()
        with self.__lock:
            return True if self.__queue else False

    def flush_queue(self) -> deque[tuple[_ReceivedPacketT, SocketAddress]]:
        with self.__lock:
            q = self.__queue.copy()
            self.__queue.clear()
            return q

    def getsockname(self) -> SocketAddress:
        self._check_closed()
        return new_socket_address(self.__socket.getsockname(), self.__socket.family)

    def fileno(self) -> int:
        if self.__closed:
            return -1
        return self.__socket.fileno()

    def dup(self) -> Socket:
        self._check_closed()
        socket: Socket = self.__socket
        return socket.dup()

    def detach(self) -> Socket:
        self._check_closed()
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
        self._check_closed()
        return self.__socket.getsockopt(*args)

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: int | bytes, /) -> None:
        ...

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: None, __optlen: int, /) -> None:
        ...

    def setsockopt(self, *args: Any) -> None:
        self._check_closed()
        return self.__socket.setsockopt(*args)

    @final
    def _check_closed(self) -> None:
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
