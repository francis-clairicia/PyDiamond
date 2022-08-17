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
from io import DEFAULT_BUFFER_SIZE, BufferedWriter
from selectors import EVENT_READ, SelectSelector as _Selector
from threading import RLock
from typing import TYPE_CHECKING, Any, Generator, Generic, TypeVar, overload

from ..system.object import Object, final
from ..system.utils.abc import concreteclass, concreteclasscheck
from .protocol.base import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol, ValidationError
from .protocol.pickle import PickleNetworkProtocol
from .protocol.stream import (
    NetworkPacketIncrementalDeserializer,
    NetworkPacketIncrementalSerializer,
    StreamNetworkPacketHandler,
    StreamNetworkProtocol,
)
from .socket.base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractUDPClientSocket,
    AbstractUDPSocket,
    ReceivedDatagram,
    SocketAddress,
    SocketRawIOWrapper,
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
        "__handler",
    )

    @overload
    def __init__(
        self,
        address: tuple[str, int],
        /,
        *,
        family: int = ...,
        timeout: int = ...,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT]
        | tuple[NetworkPacketIncrementalSerializer[_SentPacketT], NetworkPacketIncrementalDeserializer[_ReceivedPacketT]] = ...,
        socket_cls: type[AbstractTCPClientSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPClientSocket,
        /,
        *,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT]
        | tuple[NetworkPacketIncrementalSerializer[_SentPacketT], NetworkPacketIncrementalDeserializer[_ReceivedPacketT]] = ...,
        give: bool = ...,
    ) -> None:
        ...

    def __init__(
        self,
        arg: AbstractTCPClientSocket | tuple[str, int],
        /,
        *,
        protocol: StreamNetworkProtocol[_SentPacketT, _ReceivedPacketT]
        | tuple[NetworkPacketIncrementalSerializer[_SentPacketT], NetworkPacketIncrementalDeserializer[_ReceivedPacketT]]
        | None = None,
        **kwargs: Any,
    ) -> None:
        serializer: NetworkPacketIncrementalSerializer[_SentPacketT]
        deserializer: NetworkPacketIncrementalDeserializer[_ReceivedPacketT]
        # match protocol:
        #     case None:
        #         serializer = deserializer = PickleNetworkProtocol()
        #     case StreamNetworkProtocol():
        #         serializer = deserializer = protocol
        #     case (NetworkPacketIncrementalSerializer(), NetworkPacketIncrementalDeserializer()):
        #         serializer, deserializer = protocol
        #     case _:
        #         raise TypeError("Invalid argument")
        # TODO: mypy crash on match statement (I know, this is not a todo)
        if protocol is None:
            serializer = deserializer = PickleNetworkProtocol[_SentPacketT, _ReceivedPacketT]()
        elif isinstance(protocol, StreamNetworkProtocol):
            serializer = deserializer = protocol
        elif (
            isinstance(protocol, tuple)
            and len(protocol) == 2
            and isinstance(protocol[0], NetworkPacketIncrementalSerializer)
            and isinstance(protocol[1], NetworkPacketIncrementalDeserializer)
        ):
            serializer, deserializer = protocol
        else:
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
        self.__handler: StreamNetworkPacketHandler[_SentPacketT, _ReceivedPacketT] = StreamNetworkPacketHandler(
            serializer, deserializer
        )
        self.__queue: deque[_ReceivedPacketT] = deque()
        self.__lock: RLock = RLock()
        self.__chunk_size: int = DEFAULT_BUFFER_SIZE
        with suppress(OSError):  # Will not work on Windows
            socket_stat = os.fstat(socket.fileno())
            blksize: int = getattr(socket_stat, "st_blksize", 0)
            if blksize > 0:
                self.__chunk_size = blksize
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

    def send_packet(self, packet: _SentPacketT, *, flags: int = 0) -> None:
        with self.__lock, BufferedWriter(SocketRawIOWrapper(self.__socket, flags=flags), buffer_size=self.__chunk_size) as writer:
            try:
                self.__handler.write(writer, packet)
            except ConnectionError as exc:
                raise DisconnectedClientError(self) from exc

    def send_packets(self, *packets: _SentPacketT, flags: int = 0) -> None:
        if not packets:
            return
        with self.__lock, BufferedWriter(SocketRawIOWrapper(self.__socket, flags=flags), buffer_size=self.__chunk_size) as writer:
            serialize = self.__handler.write
            try:
                for packet in packets:
                    serialize(writer, packet)
            except ConnectionError as exc:
                raise DisconnectedClientError(self) from exc

    def recv_packet(self, *, flags: int = 0, retry_on_fail: bool = True) -> _ReceivedPacketT:
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            while not queue:
                queue.extend(self.__recv_packets(flags=flags, block=True))
                if not retry_on_fail:
                    break
            if not queue:
                raise NoValidPacket
            return queue.popleft()

    @overload
    def recv_packet_no_wait(self, *, flags: int = 0, default: None = ...) -> _ReceivedPacketT | None:
        ...

    @overload
    def recv_packet_no_wait(self, *, flags: int = 0, default: _T) -> _ReceivedPacketT | _T:
        ...

    def recv_packet_no_wait(self, *, flags: int = 0, default: Any = None) -> Any:
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, block=False))
                if not queue:
                    return default
            return queue.popleft()

    def recv_packets(self, *, flags: int = 0, block: bool = True) -> Generator[_ReceivedPacketT, None, None]:
        with self.__lock:
            queue: deque[_ReceivedPacketT] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, block=block))
            while queue:
                yield queue.popleft()

    def __recv_packets(self, *, flags: int, block: bool) -> Generator[_ReceivedPacketT, None, None]:
        chunk_reader: Generator[bytes, None, None] = self.read_socket(self.__socket, self.__chunk_size, block=block, flags=flags)
        try:
            while True:
                try:
                    chunk: bytes | None = next(chunk_reader, None)
                except (ConnectionError, EOFError) as exc:
                    raise DisconnectedClientError(self) from exc
                if chunk is None:
                    break
                yield from self.__handler.consume(chunk)
        finally:
            chunk_reader.close()

    @staticmethod
    @final
    def read_socket(
        socket: AbstractTCPClientSocket,
        chunk_size: int,
        *,
        block: bool = True,
        flags: int = 0,
    ) -> Generator[bytes, None, None]:
        if chunk_size <= 0:
            return
        with _Selector() as selector, suppress(BlockingIOError):
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


@concreteclass
class UDPNetworkClient(AbstractNetworkClient, Generic[_SentPacketT, _ReceivedPacketT]):
    __slots__ = (
        "__socket",
        "__socket_cls",
        "__serializer",
        "__deserializer",
        "__queue",
        "__lock",
    )

    @overload
    def __init__(
        self,
        /,
        *,
        family: int = ...,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT]
        | tuple[NetworkPacketSerializer[_SentPacketT], NetworkPacketDeserializer[_ReceivedPacketT]] = ...,
        socket_cls: AbstractUDPClientSocket = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPSocket,
        /,
        *,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT]
        | tuple[NetworkPacketSerializer[_SentPacketT], NetworkPacketDeserializer[_ReceivedPacketT]] = ...,
        give: bool = ...,
    ) -> None:
        ...

    def __init__(
        self,
        socket: AbstractUDPSocket | None = None,
        /,
        *,
        protocol: NetworkProtocol[_SentPacketT, _ReceivedPacketT]
        | tuple[NetworkPacketSerializer[_SentPacketT], NetworkPacketDeserializer[_ReceivedPacketT]]
        | None = None,
        **kwargs: Any,
    ) -> None:
        self.__serializer: NetworkPacketSerializer[_SentPacketT]
        self.__deserializer: NetworkPacketDeserializer[_ReceivedPacketT]
        # match protocol:
        #     case None:
        #         self.__serializer = self.__deserializer = PickleNetworkProtocol()
        #     case NetworkProtocol():
        #         self.__serializer = self.__deserializer = protocol
        #     case (NetworkPacketSerializer(), NetworkPacketDeserializer()):
        #         self.__serializer, self.__deserializer = protocol
        #     case _:
        #         raise TypeError("Invalid arguments")
        # TODO: mypy crash on match statement (I know, this is not a todo)
        if protocol is None:
            self.__serializer = self.__deserializer = PickleNetworkProtocol[_SentPacketT, _ReceivedPacketT]()
        elif isinstance(protocol, NetworkProtocol):
            self.__serializer = self.__deserializer = protocol
        elif (
            isinstance(protocol, tuple)
            and len(protocol) == 2
            and isinstance(protocol[0], NetworkPacketSerializer)
            and isinstance(protocol[1], NetworkPacketDeserializer)
        ):
            self.__serializer, self.__deserializer = protocol
        else:
            raise TypeError("Invalid argument")

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
            self.__socket.sendto(self.__serializer.serialize(packet), address, flags=flags)

    def send_packets(self, address: SocketAddress, *packets: _SentPacketT, flags: int = 0) -> None:
        if not packets:
            return
        with self.__lock:
            sendto = self.__socket.sendto
            for data in map(self.__serializer.serialize, packets):
                sendto(data, address, flags=flags)

    def recv_packet(self, *, flags: int = 0, retry_on_fail: bool = True) -> tuple[_ReceivedPacketT, SocketAddress]:
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            while not queue:
                queue.extend(self.__recv_packets(flags=flags, block=True))
                if not retry_on_fail:
                    break
            if not queue:
                raise NoValidPacket
            return queue.popleft()

    @overload
    def recv_packet_no_wait(self, *, flags: int = 0, default: None = ...) -> tuple[_ReceivedPacketT, SocketAddress] | None:
        ...

    @overload
    def recv_packet_no_wait(self, *, flags: int = 0, default: _T) -> tuple[_ReceivedPacketT, SocketAddress] | _T:
        ...

    def recv_packet_no_wait(self, *, flags: int = 0, default: Any = None) -> Any:
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, block=False))
                if not queue:
                    return default
            return queue.popleft()

    def recv_packets(
        self, *, flags: int = 0, block: bool = True
    ) -> Generator[tuple[_ReceivedPacketT, SocketAddress], None, None]:
        with self.__lock:
            queue: deque[tuple[_ReceivedPacketT, SocketAddress]] = self.__queue
            if not queue:
                queue.extend(self.__recv_packets(flags=flags, block=block))
            while queue:
                yield queue.popleft()

    def __recv_packets(self, flags: int, block: bool) -> Generator[tuple[_ReceivedPacketT, SocketAddress], None, None]:
        deserialize = self.__deserializer.deserialize

        chunk_generator = self.read_socket(self.__socket, block=block, flags=flags)

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
        block: bool = True,
        flags: int = 0,
    ) -> Generator[ReceivedDatagram, None, None]:
        with _Selector() as selector, suppress(BlockingIOError):
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

    def fileno(self) -> int:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.fileno()
