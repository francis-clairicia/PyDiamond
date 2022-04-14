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

from abc import abstractmethod
from selectors import EVENT_READ, EVENT_WRITE
from sys import exc_info
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic, Iterator, TypeVar, final, overload

from ..system.object import Object
from ..system.utils import concreteclass, concreteclasscheck
from .protocol.base import AbstractNetworkProtocol, ValidationError
from .protocol.pickle import PicklingNetworkProtocol
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

if TYPE_CHECKING:
    from selectors import BaseSelector

    _Selector: type[BaseSelector]

try:
    from selectors import PollSelector as _Selector
except ImportError:
    from selectors import SelectSelector as _Selector

if not TYPE_CHECKING:
    from ..system.object import final as final


_T = TypeVar("_T")


class AbstractNetworkClient(Object):
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

    @overload
    @abstractmethod
    def getsockopt(self, level: int, optname: int) -> int:
        ...

    @overload
    @abstractmethod
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        ...

    @abstractmethod
    def getsockopt(self, level: int, optname: int, buflen: int = ...) -> int | bytes:
        raise NotImplementedError

    @overload
    @abstractmethod
    def setsockopt(self, level: int, optname: int, value: int | bytes) -> None:
        ...

    @overload
    @abstractmethod
    def setsockopt(self, level: int, optname: int, value: None, optlen: int) -> None:
        ...

    @abstractmethod
    def setsockopt(self, level: int, optname: int, value: int | bytes | None, optlen: int = ...) -> None:
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
    RECV_CHUNK_SIZE: ClassVar[int] = 4096

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
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            protocol: AbstractNetworkProtocol = self.__protocol
            queue: list[_T] = self.__queue
            block = block and not queue

            def read_socket() -> Iterator[bytes]:
                chunk_size: int = self.RECV_CHUNK_SIZE
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

            buffer_recv: bytes
            buffer_recv, self.__buffer_recv = self.__buffer_recv, bytes()
            try:
                for chunk in read_socket():
                    buffer_recv += chunk
            except (ConnectionError, EOFError) as exc:
                raise DisconnectedClientError(self) from exc

            def parse_received_data() -> Iterator[bytes]:
                self.__buffer_recv = yield from protocol.parse_received_data(buffer_recv)

            for data in parse_received_data():
                if not data:
                    continue
                try:
                    protocol.verify_received_data(data)
                except ValidationError:
                    continue
                try:
                    packet: _T = protocol.deserialize(data)
                except:
                    if not protocol.handle_deserialize_error(data, *exc_info()):
                        raise
                    continue
                try:
                    protocol.verify_received_packet(packet)
                except ValidationError:
                    continue
                queue.append(packet)

    def has_saved_packets(self) -> bool:
        return True if self.__queue else False

    def getsockname(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    def getpeername(self) -> SocketAddress | None:
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            return socket.getpeername()

    def is_connected(self) -> bool:
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            return socket.is_connected()

    @overload
    def getsockopt(self, level: int, optname: int) -> int:
        ...

    @overload
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        ...

    def getsockopt(self, *args: Any, **kwargs: Any) -> int | bytes:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockopt(*args, **kwargs)

    @overload
    def setsockopt(self, level: int, optname: int, value: int | bytes) -> None:
        ...

    @overload
    def setsockopt(self, level: int, optname: int, value: None, optlen: int) -> None:
        ...

    def setsockopt(self, *args: Any, **kwargs: Any) -> None:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.setsockopt(*args, **kwargs)

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

    @overload
    def reconnect(self) -> None:
        ...

    @overload
    def reconnect(self, timeout: float | None) -> None:
        ...

    def reconnect(self, *args: Any, **kwargs: Any) -> None:
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            return socket.reconnect(*args, **kwargs)

    def try_reconnect(self, timeout: float | None = None) -> bool:
        with self.__lock:
            socket: AbstractTCPClientSocket = self.__socket
            return socket.try_reconnect(timeout=timeout)

    @final
    @property
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        return self.__protocol.__class__


@concreteclass
class UDPNetworkClient(AbstractNetworkClient, Generic[_T]):
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
            with _Selector() as selector:
                selector.register(socket, EVENT_WRITE)
                while not selector.select():
                    continue
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
        with self.__lock:
            socket: AbstractUDPSocket = self.__socket
            protocol: AbstractNetworkProtocol = self.__protocol
            queue: list[tuple[_T, SocketAddress]] = self.__queue
            block = block and not queue

            def read_socket() -> Iterator[ReceivedDatagram]:
                with _Selector() as selector:
                    selector.register(socket, EVENT_READ)
                    if not block and not selector.select(timeout=0):
                        return
                    datagram = socket.recvfrom(flags=flags)
                    if datagram.body:
                        yield datagram
                    while selector.select(timeout=0):
                        datagram = socket.recvfrom(flags=flags)
                        if not datagram.body:
                            continue
                        yield datagram

            for data, sender in tuple(read_socket()):
                try:
                    protocol.verify_received_data(data)
                except ValidationError:
                    continue
                try:
                    packet: _T = protocol.deserialize(data)
                except:
                    if not protocol.handle_deserialize_error(data, *exc_info()):
                        raise
                    continue
                try:
                    protocol.verify_received_packet(packet)
                except ValidationError:
                    continue
                queue.append((packet, sender))

    def has_saved_packets(self) -> bool:
        with self.__lock:
            return True if self.__queue else False

    def getsockname(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @overload
    def getsockopt(self, level: int, optname: int) -> int:
        ...

    @overload
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        ...

    def getsockopt(self, *args: Any, **kwargs: Any) -> int | bytes:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockopt(*args, **kwargs)

    @overload
    def setsockopt(self, level: int, optname: int, value: int | bytes) -> None:
        ...

    @overload
    def setsockopt(self, level: int, optname: int, value: None, optlen: int) -> None:
        ...

    def setsockopt(self, *args: Any, **kwargs: Any) -> None:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.setsockopt(*args, **kwargs)

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
