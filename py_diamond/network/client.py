# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network client module"""

from __future__ import annotations

__all__ = ["AbstractNetworkClient", "ClientError", "DisconnectedClientError", "TCPNetworkClient", "UDPNetworkClient"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import sys
from abc import abstractmethod
from io import DEFAULT_BUFFER_SIZE
from os import fstat
from selectors import EVENT_READ, EVENT_WRITE
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterator, TypeVar, overload

from ..system.object import Object, final
from ..system.utils.abc import concreteclass, concreteclasscheck
from .protocol.base import AbstractNetworkProtocol, ValidationError
from .protocol.pickle import PicklingNetworkProtocol
from .selector import DefaultSelector as _Selector
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
    def getblocking(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def setblocking(self, flag: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def fileno(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        raise NotImplementedError


class ClientError(Exception):
    def __init__(self, client: TCPNetworkClient[Any], message: str | None = None) -> None:
        if not message:
            if not client.is_connected():
                message = "Something went wrong for a client"
            else:
                addr: SocketAddress = client.getsockname()
                message = f"Something went wrong for the client {addr.host}:{addr.port}"
        super().__init__(message)
        self.client: TCPNetworkClient[Any] = client


class DisconnectedClientError(ClientError, ConnectionError):
    def __init__(self, client: TCPNetworkClient[Any]) -> None:
        addr: SocketAddress = client.getsockname()
        super().__init__(client, f"{addr.host}:{addr.port} has been disconnected")


class NoValidPacket(ValueError):
    pass


@concreteclass
class TCPNetworkClient(AbstractNetworkClient, Generic[_T]):
    __slots__ = (
        "__socket",
        "__buffer_recv",
        "__protocol",
        "__queue",
        "__lock",
        "__chunk_size",
    )

    @overload
    def __init__(
        self,
        address: tuple[str, int],
        /,
        *,
        family: int = ...,
        timeout: int = ...,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
        socket_cls: type[AbstractTCPClientSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPClientSocket,
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        arg: AbstractTCPClientSocket | tuple[str, int],
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = PicklingNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(protocol_cls)
        socket: AbstractTCPClientSocket
        if isinstance(arg, AbstractTCPClientSocket):
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = arg
        elif isinstance(arg, tuple):
            address: tuple[str, int] = arg
            socket_cls: type[AbstractTCPClientSocket] = kwargs.pop("socket_cls", PythonTCPClientSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.connect(address, **kwargs)
        else:
            raise TypeError("Invalid arguments")
        self.__socket: AbstractTCPClientSocket = socket
        self.__buffer_recv: bytes = b""
        self.__protocol: AbstractNetworkProtocol = protocol_cls()
        self.__queue: list[_T] = []
        self.__lock: RLock = RLock()
        self.__chunk_size: int = DEFAULT_BUFFER_SIZE
        if sys.platform != "win32":  # Will not work on Windows
            try:
                socket_stat = fstat(socket.fileno())
            except OSError:
                pass
            else:
                blksize: int = getattr(socket_stat, "st_blksize", 0)
                if blksize > 0:
                    self.__chunk_size = blksize
        super().__init__()

    def close(self) -> None:
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            if socket.is_open():
                try:
                    socket.shutdown(SHUT_WR)
                except OSError:
                    pass
                finally:
                    socket.close()

    def send_packet(self, packet: _T, *, flags: int = 0) -> None:
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            protocol: AbstractNetworkProtocol = self.__protocol
            protocol.verify_packet_to_send(packet)
            data: bytes = protocol.serialize(packet)
            data = protocol.parser_add_header_footer(data)
            try:
                with _Selector() as selector:
                    selector.register(socket, EVENT_WRITE)
                    while data:
                        while not selector.select():
                            continue
                        sent: int = socket.send(data, flags)
                        data = data[sent:]
            except ConnectionError as exc:
                raise DisconnectedClientError(self) from exc

    def recv_packet(self, *, flags: int = 0, retry_on_fail: bool = True) -> _T:
        with self.__lock:
            queue: list[_T] = self.__queue
            if not queue:
                recv_packets: Callable[[], None] = lambda: self.__recv_packets(flags=flags, block=True)
                recv_packets()
                while not queue and retry_on_fail:
                    recv_packets()
                if not queue:
                    raise NoValidPacket
            return queue.pop(0)

    def recv_packet_no_wait(self, *, flags: int = 0) -> _T | None:
        with self.__lock:
            queue: list[_T] = self.__queue
            if not queue:
                self.__recv_packets(flags=flags, block=False)
                if not queue:
                    return None
            return queue.pop(0)

    def recv_packets(self, *, flags: int = 0, block: bool = True) -> Iterator[_T]:
        with self.__lock:
            self.__recv_packets(flags=flags, block=block)
            queue: list[_T] = self.__queue
            while queue:
                yield queue.pop(0)

    def __recv_packets(self, flags: int, block: bool) -> None:
        protocol: AbstractNetworkProtocol = self.__protocol
        queue: list[_T] = self.__queue
        block = block and not queue

        buffer_recv: bytes = self.__buffer_recv
        self.__buffer_recv = bytes()
        try:
            for chunk in self.read_socket(self.__socket, self.__chunk_size, block=block, flags=flags):
                buffer_recv += chunk
        except (ConnectionError, EOFError) as exc:
            raise DisconnectedClientError(self) from exc

        for data in self.__parse_received_data(buffer_recv):
            if not data:
                continue
            try:
                protocol.verify_received_data(data)
            except ValidationError:
                continue
            try:
                packet: _T = protocol.deserialize(data)
            except Exception:
                if not protocol.handle_deserialize_error(data, *sys.exc_info()):
                    raise
                continue
            try:
                protocol.verify_received_packet(packet)
            except ValidationError:
                continue
            queue.append(packet)

    def __parse_received_data(self, buffer: bytes) -> Iterator[bytes]:
        self.__buffer_recv = yield from self.__protocol.parse_received_data(buffer)

    @staticmethod
    def read_socket(socket: AbstractTCPClientSocket, chunk_size: int, *, block: bool = True, flags: int = 0) -> Iterator[bytes]:
        if chunk_size <= 0:
            return
        with _Selector() as selector:
            selector.register(socket, EVENT_READ)
            if not block and not selector.select(timeout=0):
                return
            data: bytes = socket.recv(chunk_size)
            if (length := len(data)) == 0:
                raise EOFError
            yield data
            while length >= chunk_size and selector.select(timeout=0):
                data = socket.recv(chunk_size, flags=flags)
                if (length := len(data)) == 0:
                    break
                yield data

    def has_saved_packets(self) -> bool:
        with self.__lock:
            return True if self.__queue else False

    def getsockname(self) -> SocketAddress:
        with self.__lock:
            return self.__socket.getsockname()

    def getpeername(self) -> SocketAddress | None:
        with self.__lock:
            return self.__socket.getpeername()

    def is_connected(self) -> bool:
        with self.__lock:
            return self.__socket.is_connected()

    def getblocking(self) -> bool:
        with self.__lock:
            return self.__socket.getblocking()

    def setblocking(self, flag: bool) -> None:
        with self.__lock:
            return self.__socket.setblocking(flag)

    def fileno(self) -> int:
        with self.__lock:
            return self.__socket.fileno()

    @overload
    def reconnect(self) -> None:
        ...

    @overload
    def reconnect(self, timeout: float | None) -> None:
        ...

    def reconnect(self, *args: Any, **kwargs: Any) -> None:
        with self.__lock:
            return self.__socket.reconnect(*args, **kwargs)

    def try_reconnect(self, timeout: float | None = None) -> bool:
        with self.__lock:
            return self.__socket.try_reconnect(timeout=timeout)

    @final
    @property
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        return self.__protocol.__class__


@concreteclass
class UDPNetworkClient(AbstractNetworkClient, Generic[_T]):
    __slots__ = (
        "__socket",
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
        protocol_cls: type[AbstractNetworkProtocol] = ...,
        socket_cls: type[AbstractUDPClientSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPSocket,
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        socket: AbstractUDPSocket | None = None,
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = PicklingNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(protocol_cls)
        if isinstance(socket, AbstractUDPSocket):
            if kwargs:
                raise TypeError("Invalid arguments")
        elif socket is None:
            socket_cls: type[AbstractUDPClientSocket] = kwargs.pop("socket_cls", PythonUDPClientSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.create(**kwargs)
        else:
            raise TypeError("Invalid arguments")
        super().__init__()
        self.__socket: AbstractUDPSocket = socket
        self.__protocol: AbstractNetworkProtocol = protocol_cls()
        self.__queue: list[tuple[_T, SocketAddress]] = []
        self.__lock: RLock = RLock()

    def close(self) -> None:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            if socket.is_open():
                socket.close()

    def send_packet(self, packet: _T, address: SocketAddress, *, flags: int = 0) -> None:
        with self.__lock:
            socket: AbstractUDPSocket = self.__socket
            protocol: AbstractNetworkProtocol = self.__protocol
            protocol.verify_packet_to_send(packet)
            data: bytes = protocol.serialize(packet)
            socket.sendto(data, address, flags=flags)

    def recv_packet(self, *, flags: int = 0, retry_on_fail: bool = True) -> tuple[_T, SocketAddress]:
        with self.__lock:
            queue: list[tuple[_T, SocketAddress]] = self.__queue
            if not queue:
                recv_packets: Callable[[], None] = lambda: self.__recv_packets(flags=flags, block=True)
                recv_packets()
                while not queue and retry_on_fail:
                    recv_packets()
                if not queue:
                    raise NoValidPacket
            return queue.pop(0)

    def recv_packet_no_wait(self, *, flags: int = 0) -> tuple[_T, SocketAddress] | None:
        with self.__lock:
            queue: list[tuple[_T, SocketAddress]] = self.__queue
            if not queue:
                self.__recv_packets(flags=flags, block=False)
                if not queue:
                    return None
            return queue.pop(0)

    def recv_packets(self, *, flags: int = 0, block: bool = True) -> Iterator[tuple[_T, SocketAddress]]:
        with self.__lock:
            self.__recv_packets(flags=flags, block=block)
            queue: list[tuple[_T, SocketAddress]] = self.__queue
            while queue:
                yield queue.pop(0)

    def __recv_packets(self, flags: int, block: bool) -> None:
        protocol: AbstractNetworkProtocol = self.__protocol
        queue: list[tuple[_T, SocketAddress]] = self.__queue
        block = block and not queue

        for data, sender in tuple(self.read_socket(self.__socket, block=block, flags=flags)):
            try:
                protocol.verify_received_data(data)
            except ValidationError:
                continue
            try:
                packet: _T = protocol.deserialize(data)
            except Exception:
                if not protocol.handle_deserialize_error(data, *sys.exc_info()):
                    raise
                continue
            try:
                protocol.verify_received_packet(packet)
            except ValidationError:
                continue
            queue.append((packet, sender))

    @staticmethod
    def read_socket(socket: AbstractUDPSocket, *, block: bool = True, flags: int = 0) -> Iterator[ReceivedDatagram]:
        with _Selector() as selector:
            selector.register(socket, EVENT_READ)
            if not block and not selector.select(timeout=0):
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

    def getblocking(self) -> bool:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getblocking()

    def setblocking(self, flag: bool) -> None:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.setblocking(flag)

    def fileno(self) -> int:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.fileno()

    @final
    @property
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        return self.__protocol.__class__
