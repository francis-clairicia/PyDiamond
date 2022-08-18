# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network server module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkServer",
    "AbstractRequestHandler",
    "AbstractTCPNetworkServer",
    "AbstractTCPRequestHandler",
    "AbstractUDPNetworkServer",
    "AbstractUDPRequestHandler",
    "ConnectedClient",
    "StateLessTCPNetworkServer",
    "StateLessUDPNetworkServer",
]

from abc import abstractmethod
from contextlib import suppress
from selectors import EVENT_READ, BaseSelector
from threading import Event, RLock, current_thread
from typing import TYPE_CHECKING, Any, Callable, Generic, Sequence, TypeAlias, TypeVar, overload

from ..system.object import Object, final
from ..system.threading import Thread, thread_factory
from ..system.utils.abc import concreteclass, concreteclasscheck
from ..system.utils.functools import dsuppress
from .client import DisconnectedClientError, TCPNetworkClient, UDPNetworkClient
from .protocol.base import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol
from .protocol.pickle import PickleNetworkProtocol
from .protocol.stream import NetworkPacketIncrementalDeserializer, NetworkPacketIncrementalSerializer, StreamNetworkProtocol
from .selector import DefaultSelector as _Selector
from .socket.base import AbstractSocket, AbstractTCPServerSocket, AbstractUDPServerSocket, SocketAddress
from .socket.python import PythonTCPServerSocket, PythonUDPServerSocket

_RequestT = TypeVar("_RequestT")
_ResponseT = TypeVar("_ResponseT")


class ConnectedClient(Generic[_ResponseT], Object):
    def __init__(self, address: SocketAddress) -> None:
        super().__init__()
        self.__addr: SocketAddress = address

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_packet(self, packet: _ResponseT, *, flags: int = 0) -> None:
        raise NotImplementedError

    @property
    @final
    def address(self) -> SocketAddress:
        return self.__addr


class AbstractRequestHandler(Generic[_RequestT, _ResponseT], Object):
    @final
    def __init__(self, request: _RequestT, client: ConnectedClient[_ResponseT], server: AbstractNetworkServer) -> None:
        self.request: _RequestT = request
        self.client: ConnectedClient[_ResponseT] = client
        self.server: AbstractNetworkServer = server
        self.setup()
        try:
            self.handle()
        finally:
            self.teardown()

    def setup(self) -> None:
        pass

    @abstractmethod
    def handle(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        pass


class AbstractTCPRequestHandler(AbstractRequestHandler[_RequestT, _ResponseT]):
    server: AbstractTCPNetworkServer[_RequestT, _ResponseT]

    @classmethod
    def welcome(cls, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True


class AbstractUDPRequestHandler(AbstractRequestHandler[_RequestT, _ResponseT]):
    server: AbstractUDPNetworkServer[_RequestT, _ResponseT]


class AbstractNetworkServer(Object):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractNetworkServer")

    def __init__(self) -> None:
        super().__init__()
        self.__t: Thread | None = None

    def __enter__(self: __Self) -> __Self:
        return self

    def __exit__(self, *args: Any) -> None:
        t: Thread | None = self.__t
        self.__t = None
        if t is not None:
            if t is not current_thread() and t.is_alive():
                self.shutdown()
                t.join()
        else:
            self.shutdown()
        self.server_close()

    @abstractmethod
    def serve_forever(self, poll_interval: float = ...) -> None:
        raise NotImplementedError

    def serve_forever_in_thread(
        self,
        poll_interval: float = 0.5,
        *,
        daemon: bool | None = None,
        name: str | None = None,
    ) -> Thread:
        if self.running():
            raise RuntimeError("Server already running")

        @thread_factory(daemon=daemon, name=name)
        def run(self: AbstractNetworkServer, poll_interval: float) -> None:
            self.serve_forever(poll_interval)

        t: Thread | None = self.__t
        if t is not None and t.is_alive():
            t.join()
        self.__t = t = run(self, poll_interval)
        return t

    @abstractmethod
    def server_close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def running(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def shutdown(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def server_address(self) -> SocketAddress:
        raise NotImplementedError


NetworkProtocolFactory: TypeAlias = Callable[[], NetworkProtocol[_ResponseT, _RequestT]]
NetworkPacketDeserializerFactory: TypeAlias = Callable[[], NetworkPacketDeserializer[_RequestT]]
NetworkPacketSerializerFactory: TypeAlias = Callable[[], NetworkPacketSerializer[_ResponseT]]

StreamNetworkProtocolFactory: TypeAlias = Callable[[], StreamNetworkProtocol[_ResponseT, _RequestT]]
NetworkPacketIncrementalDeserializerFactory: TypeAlias = Callable[[], NetworkPacketIncrementalDeserializer[_RequestT]]
NetworkPacketIncrementalSerializerFactory: TypeAlias = Callable[[], NetworkPacketIncrementalSerializer[_ResponseT]]


class AbstractTCPNetworkServer(AbstractNetworkServer, Generic[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[
            NetworkPacketIncrementalSerializerFactory[_ResponseT],
            NetworkPacketIncrementalDeserializerFactory[_RequestT],
        ] = ...,
        socket_cls: type[AbstractTCPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPServerSocket,
        /,
        *,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[
            NetworkPacketIncrementalSerializerFactory[_ResponseT],
            NetworkPacketIncrementalDeserializerFactory[_RequestT],
        ] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: AbstractTCPServerSocket | tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[
            NetworkPacketIncrementalSerializerFactory[_ResponseT],
            NetworkPacketIncrementalDeserializerFactory[_RequestT],
        ] = PickleNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        if not isinstance(protocol_cls, tuple):
            if not callable(protocol_cls):
                raise TypeError("Invalid arguments")
            protocol_cls = protocol_cls, protocol_cls
        socket: AbstractTCPServerSocket
        self.__socket_cls: type[AbstractTCPServerSocket] | None
        if isinstance(__arg, AbstractTCPServerSocket):
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = __arg
            self.__socket_cls = None
        elif isinstance(__arg, tuple):
            address: tuple[str, int] | tuple[str, int, int, int] = __arg
            socket_cls: type[AbstractTCPServerSocket] = kwargs.pop("socket_cls", PythonTCPServerSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.bind(address, **kwargs)
            self.__socket_cls = socket_cls
        else:
            raise TypeError("Invalid arguments")
        self.__socket: AbstractTCPServerSocket = socket
        self.__protocol_cls: tuple[
            NetworkPacketIncrementalSerializerFactory[_ResponseT],
            NetworkPacketIncrementalDeserializerFactory[_RequestT],
        ] = protocol_cls
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__clients: dict[TCPNetworkClient[_ResponseT, _RequestT], ConnectedClient[_ResponseT]] = {}
        self.__recv_flags: int = 0
        super().__init__()

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        if self.running():
            raise RuntimeError("Server already running")
        with self.__lock:
            self.__loop = True
            self.__is_shutdown.clear()
        socket: AbstractTCPServerSocket = self.__socket
        clients_dict: dict[TCPNetworkClient[_ResponseT, _RequestT], ConnectedClient[_ResponseT]] = self.__clients
        selector: BaseSelector = _Selector()

        @thread_factory(daemon=True)
        def verify_client(client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> None:
            if not self._verify_new_client(client, address):
                client.close()
                return
            selector.register(client, EVENT_READ)
            clients_dict[client] = self.__ConnectedClient(client, address)

        def new_client() -> None:
            try:
                client_socket, address = socket.accept()
            except OSError:
                return
            serializer_cls, deserializer_cls = self.__protocol_cls
            protocol = (serializer_cls(), deserializer_cls())
            client: TCPNetworkClient[_ResponseT, _RequestT] = TCPNetworkClient(client_socket, protocol=protocol, give=True)
            verify_client(client, address)

        def parse_requests(client: TCPNetworkClient[_ResponseT, _RequestT]) -> None:
            if not client.is_connected():
                return
            try:
                connected_client: ConnectedClient[_ResponseT] = clients_dict[client]
                for request in client.recv_packets(block=True, flags=self.recv_flags):  # TODO: Handle one packet per loop
                    # TODO (3.11): Exception groups
                    try:
                        self._process_request(request, connected_client)
                    except DisconnectedClientError:
                        raise
                    except Exception:
                        self._handle_error(connected_client)
                    if not client.is_connected():
                        shutdown_client(client)
                        return
            except DisconnectedClientError:
                shutdown_client(client)
            except BaseException:
                shutdown_client(client)
                raise

        def shutdown_client(client: TCPNetworkClient[_ResponseT, _RequestT]) -> None:
            with suppress(KeyError):
                selector.unregister(client)
            with suppress(Exception):
                client.close()
            clients_dict.pop(client, None)

        def remove_closed_clients() -> None:
            for client in filter(lambda client: not client.is_connected(), tuple(clients_dict)):
                with suppress(KeyError):
                    selector.unregister(client)
                clients_dict.pop(client, None)

        with selector:
            selector.register(socket, EVENT_READ)
            try:
                while self.running():
                    ready = selector.select(poll_interval)
                    if not self.running():
                        break
                    for key, _ in ready:
                        fileobj: Any = key.fileobj
                        if fileobj is socket:
                            new_client()
                        else:
                            parse_requests(fileobj)
                    remove_closed_clients()
                    self.service_actions()
            finally:
                try:
                    with self.__lock:
                        self.__loop = False
                        for client in tuple(clients_dict):
                            shutdown_client(client)
                finally:
                    clients_dict.clear()
                    self.__is_shutdown.set()

    @final
    def running(self) -> bool:
        with self.__lock:
            return self.__loop

    def service_actions(self) -> None:
        pass

    @abstractmethod
    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        raise NotImplementedError

    def _handle_error(self, client: ConnectedClient[_ResponseT]) -> None:
        from sys import stderr
        from traceback import print_exc

        client_address: tuple[Any, ...] = tuple(client.address)
        print("-" * 40, file=stderr)
        print(f"Exception occurred during processing of request from {client_address}", file=stderr)
        print_exc(file=stderr)
        print("-" * 40, file=stderr)

    def server_close(self) -> None:
        with self.__lock:
            if self.__socket_cls is None:
                return
            self.__socket_cls = None
            socket: AbstractSocket = self.__socket
            if socket.is_open():
                socket.close()

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def _verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True

    @property
    @final
    def server_address(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @final
    def listen(self, backlog: int) -> None:
        with self.__lock:
            socket: AbstractTCPServerSocket = self.__socket
            return socket.listen(backlog)

    @property
    @final
    def clients(self) -> Sequence[ConnectedClient[_ResponseT]]:
        with self.__lock:
            return tuple(self.__clients.values())

    @property  # type: ignore[misc]
    @final
    def recv_flags(self) -> int:
        with self.__lock:
            return self.__recv_flags

    @recv_flags.setter
    def recv_flags(self, value: int) -> None:
        with self.__lock:
            self.__recv_flags = int(value)

    @final
    class __ConnectedClient(ConnectedClient[_ResponseT]):
        def __init__(self, client: TCPNetworkClient[_ResponseT, Any], address: SocketAddress) -> None:
            super().__init__(address)
            self.__client: TCPNetworkClient[_ResponseT, Any] = client

        def close(self) -> None:
            return self.__client.close()

        def send_packet(self, packet: _ResponseT, *, flags: int = 0) -> None:
            return self.__client.send_packet(packet, flags=flags)


@concreteclass
class StateLessTCPNetworkServer(AbstractTCPNetworkServer[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]],
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[
            NetworkPacketIncrementalSerializerFactory[_ResponseT],
            NetworkPacketIncrementalDeserializerFactory[_RequestT],
        ] = ...,
        socket_cls: type[AbstractTCPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPServerSocket,
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]],
        *,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[
            NetworkPacketIncrementalSerializerFactory[_ResponseT],
            NetworkPacketIncrementalDeserializerFactory[_RequestT],
        ] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: Any,
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]],
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractTCPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a TCP request handler")
        self.__request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]] = request_handler_cls
        super().__init__(__arg, **kwargs)

    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        self.__request_handler_cls(request, client, self)

    def _verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return self.__request_handler_cls.welcome(client, address)

    @property
    @final
    def request_handler_cls(self) -> type[AbstractTCPRequestHandler[_RequestT, _ResponseT]]:
        return self.__request_handler_cls


class AbstractUDPNetworkServer(AbstractNetworkServer, Generic[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        family: int = ...,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[NetworkPacketSerializerFactory[_ResponseT], NetworkPacketDeserializerFactory[_RequestT]] = ...,
        socket_cls: type[AbstractUDPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPServerSocket,
        /,
        *,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[NetworkPacketSerializerFactory[_ResponseT], NetworkPacketDeserializerFactory[_RequestT]] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: AbstractUDPServerSocket | tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[NetworkPacketSerializerFactory[_ResponseT], NetworkPacketDeserializerFactory[_RequestT]] = PickleNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        serializer_cls: NetworkPacketSerializerFactory[_ResponseT]
        deserializer_cls: NetworkPacketDeserializerFactory[_RequestT]
        if not isinstance(protocol_cls, tuple):
            if not callable(protocol_cls):
                raise TypeError("Invalid arguments")
            serializer_cls, deserializer_cls = protocol_cls, protocol_cls
        else:
            serializer_cls, deserializer_cls = protocol_cls
        protocol = (serializer_cls(), deserializer_cls())
        socket: AbstractUDPServerSocket
        self.__socket_cls: type[AbstractUDPServerSocket] | None
        if isinstance(__arg, AbstractUDPServerSocket):
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = __arg
            self.__socket_cls = None
        elif isinstance(__arg, tuple):
            address: tuple[str, int] | tuple[str, int, int, int] = __arg
            socket_cls: type[AbstractUDPServerSocket] = kwargs.pop("socket_cls", PythonUDPServerSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.bind(address, **kwargs)
            self.__socket_cls = socket_cls
        else:
            raise TypeError("Invalid arguments")
        self.__socket: AbstractUDPServerSocket = socket
        self.__client: UDPNetworkClient[_ResponseT, _RequestT] = UDPNetworkClient(socket, protocol=protocol)
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__recv_flags: int = 0
        super().__init__()

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        if self.running():
            raise RuntimeError("Server already running")
        with self.__lock:
            self.__loop = True
            self.__is_shutdown.clear()

        client: UDPNetworkClient[_ResponseT, _RequestT] = self.__client

        def parse_requests() -> None:
            with self.__lock:
                for request, address in client.recv_packets(block=True, flags=self.recv_flags):
                    connected_client: ConnectedClient[_ResponseT] = self.__ConnectedClient(client, address)
                    try:
                        self._process_request(request, connected_client)
                    except DisconnectedClientError:
                        raise
                    except Exception:
                        self._handle_error(connected_client)

        with _Selector() as selector:
            selector.register(self.__socket, EVENT_READ)
            try:
                while self.running():
                    ready: bool = len(selector.select(poll_interval)) > 0
                    if not self.running():
                        break
                    if ready:
                        parse_requests()
                    self.service_actions()
            finally:
                with self.__lock:
                    self.__loop = False
                self.__is_shutdown.set()

    def server_close(self) -> None:
        with self.__lock:
            if self.__socket_cls is None:
                return
            self.__socket_cls = None
            socket: AbstractSocket = self.__socket
            if socket.is_open():
                socket.close()

    def service_actions(self) -> None:
        pass

    @abstractmethod
    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        raise NotImplementedError

    def _handle_error(self, client: ConnectedClient[_ResponseT]) -> None:
        from sys import stderr
        from traceback import print_exc

        client_address: tuple[Any, ...] = tuple(client.address)
        print("-" * 40, file=stderr)
        print(f"Exception occurred during processing of request from {client_address}", file=stderr)
        print_exc(file=stderr)
        print("-" * 40, file=stderr)

    def running(self) -> bool:
        with self.__lock:
            return self.__loop

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    @property
    @final
    def server_address(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @property  # type: ignore[misc]
    @final
    def recv_flags(self) -> int:
        with self.__lock:
            return self.__recv_flags

    @recv_flags.setter
    def recv_flags(self, value: int) -> None:
        with self.__lock:
            self.__recv_flags = int(value)

    @final
    class __ConnectedClient(ConnectedClient[_ResponseT]):
        def __init__(self, client: UDPNetworkClient[_ResponseT, Any], address: SocketAddress) -> None:
            super().__init__(address)
            self.__client: UDPNetworkClient[_ResponseT, Any] = client

        def close(self) -> None:
            return self.__client.close()

        def send_packet(self, packet: _ResponseT, *, flags: int = 0) -> None:
            return self.__client.send_packet(self.address, packet, flags=flags)


@concreteclass
class StateLessUDPNetworkServer(AbstractUDPNetworkServer[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]],
        *,
        family: int = ...,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[NetworkPacketSerializerFactory[_ResponseT], NetworkPacketDeserializerFactory[_RequestT]] = ...,
        socket_cls: type[AbstractUDPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPServerSocket,
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]],
        *,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT]
        | tuple[NetworkPacketSerializerFactory[_ResponseT], NetworkPacketDeserializerFactory[_RequestT]] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: Any,
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]],
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractUDPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a UDP request handler")
        self.__request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]] = request_handler_cls
        super().__init__(__arg, **kwargs)

    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        self.__request_handler_cls(request, client, self)

    @property
    @final
    def request_handler_cls(self) -> type[AbstractUDPRequestHandler[_RequestT, _ResponseT]]:
        return self.__request_handler_cls
