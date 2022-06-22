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
    "TCPNetworkServer",
    "UDPNetworkServer",
]

from abc import abstractmethod
from contextlib import suppress
from selectors import EVENT_READ, BaseSelector
from threading import Event, RLock, current_thread
from typing import TYPE_CHECKING, Any, Callable, Generic, Sequence, TypeVar, overload

from ..system.object import Object, final
from ..system.threading import Thread, thread_factory
from ..system.utils.abc import concreteclass, concreteclasscheck
from ..system.utils.functools import dsuppress
from .client import DisconnectedClientError, TCPNetworkClient, UDPNetworkClient
from .protocol.base import AbstractNetworkProtocol
from .protocol.pickle import PicklingNetworkProtocol
from .protocol.stream import AbstractStreamNetworkProtocol
from .selector import DefaultSelector as _Selector
from .socket.base import AbstractSocket, AbstractTCPServerSocket, AbstractUDPServerSocket, SocketAddress
from .socket.python import PythonTCPServerSocket, PythonUDPServerSocket

_T = TypeVar("_T")


class ConnectedClient(Generic[_T], Object):
    def __init__(self, address: SocketAddress) -> None:
        super().__init__()
        self.__addr: SocketAddress = address

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_packet(self, packet: _T, *, flags: int = 0) -> None:
        raise NotImplementedError

    @final
    @property
    def address(self) -> SocketAddress:
        return self.__addr


class AbstractRequestHandler(Generic[_T], Object):
    @final
    def __init__(self, request: _T, client: ConnectedClient[_T], server: AbstractNetworkServer) -> None:
        self.request: _T = request
        self.client: ConnectedClient[_T] = client
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
        pass

    def teardown(self) -> None:
        pass


class AbstractTCPRequestHandler(AbstractRequestHandler[_T]):
    server: AbstractTCPNetworkServer[_T]


class AbstractUDPRequestHandler(AbstractRequestHandler[_T]):
    server: AbstractUDPNetworkServer[_T]


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

    @property
    @abstractmethod
    def protocol_cls(self) -> Callable[[], AbstractNetworkProtocol]:
        raise NotImplementedError


class AbstractTCPNetworkServer(AbstractNetworkServer, Generic[_T]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: Callable[[], AbstractStreamNetworkProtocol] = ...,
        socket_cls: type[AbstractTCPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPServerSocket,
        /,
        *,
        protocol_cls: Callable[[], AbstractStreamNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: AbstractTCPServerSocket | tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        protocol_cls: Callable[[], AbstractStreamNetworkProtocol] = PicklingNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        protocol: AbstractStreamNetworkProtocol = protocol_cls()
        if not isinstance(protocol, AbstractStreamNetworkProtocol):
            raise TypeError("Invalid arguments")
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
        self.__protocol_cls: Callable[[], AbstractStreamNetworkProtocol] = protocol_cls
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__clients: dict[TCPNetworkClient[_T], ConnectedClient[_T]] = {}
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
        clients_dict: dict[TCPNetworkClient[_T], ConnectedClient[_T]] = self.__clients
        selector: BaseSelector = _Selector()

        @thread_factory(daemon=True)
        def verify_client(client: TCPNetworkClient[_T], address: SocketAddress) -> None:
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
            client: TCPNetworkClient[_T] = TCPNetworkClient(client_socket, protocol=self.protocol_cls(), give=True)
            verify_client(client, address)

        def parse_requests(client: TCPNetworkClient[_T]) -> None:
            if not client.is_connected():
                return
            try:
                connected_client: ConnectedClient[_T] = clients_dict[client]
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
            except:
                shutdown_client(client)
                raise

        def shutdown_client(client: TCPNetworkClient[_T]) -> None:
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
    def _process_request(self, request: _T, client: ConnectedClient[_T]) -> None:
        raise NotImplementedError

    def _handle_error(self, client: ConnectedClient[_T]) -> None:
        from sys import stderr
        from traceback import print_exc

        client_address: tuple[Any, ...] = tuple(client.address)
        print("-" * 40, file=stderr)
        print(f"Exception occurred during processing of request from {client_address}", file=stderr)
        print_exc()
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

    def _verify_new_client(self, client: TCPNetworkClient[_T], address: SocketAddress) -> bool:
        return True

    @final
    @property
    def server_address(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @final
    def listen(self, backlog: int) -> None:
        with self.__lock:
            socket: AbstractTCPServerSocket = self.__socket
            return socket.listen(backlog)

    @final
    @property
    def clients(self) -> Sequence[ConnectedClient[_T]]:
        with self.__lock:
            return tuple(self.__clients.values())

    @final
    @property
    def protocol_cls(self) -> Callable[[], AbstractStreamNetworkProtocol]:
        return self.__protocol_cls

    @property
    def recv_flags(self) -> int:
        with self.__lock:
            return self.__recv_flags

    @recv_flags.setter
    def recv_flags(self, value: int) -> None:
        with self.__lock:
            self.__recv_flags = int(value)

    @final
    class __ConnectedClient(ConnectedClient[_T]):
        def __init__(self, client: TCPNetworkClient[_T], address: SocketAddress) -> None:
            super().__init__(address)
            self.__client: TCPNetworkClient[_T] = client

        def close(self) -> None:
            client: TCPNetworkClient[_T] = self.__client
            return client.close()

        def send_packet(self, packet: _T, *, flags: int = 0) -> None:
            client: TCPNetworkClient[_T] = self.__client
            return client.send_packet(packet, flags=flags)


@concreteclass
class TCPNetworkServer(AbstractTCPNetworkServer[_T]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_T]],
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: Callable[[], AbstractStreamNetworkProtocol] = ...,
        socket_cls: type[AbstractTCPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPServerSocket,
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_T]],
        *,
        protocol_cls: Callable[[], AbstractStreamNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(self, __arg: Any, /, request_handler_cls: type[AbstractTCPRequestHandler[_T]], **kwargs: Any) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractTCPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a TCP request handler")
        self.__request_handler_cls: type[AbstractTCPRequestHandler[_T]] = request_handler_cls
        super().__init__(__arg, **kwargs)

    def _process_request(self, request: _T, client: ConnectedClient[_T]) -> None:
        self.__request_handler_cls(request, client, self)

    @final
    @property
    def request_handler_cls(self) -> type[AbstractTCPRequestHandler[_T]]:
        return self.__request_handler_cls


class AbstractUDPNetworkServer(AbstractNetworkServer, Generic[_T]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        family: int = ...,
        protocol_cls: Callable[[], AbstractNetworkProtocol] = ...,
        socket_cls: type[AbstractUDPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPServerSocket,
        /,
        *,
        protocol_cls: Callable[[], AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: AbstractUDPServerSocket | tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        protocol_cls: Callable[[], AbstractNetworkProtocol] = PicklingNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        protocol: AbstractNetworkProtocol = protocol_cls()
        if not isinstance(protocol, AbstractNetworkProtocol):
            raise TypeError("Invalid arguments")
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
        self.__client: UDPNetworkClient[_T] = UDPNetworkClient(socket, protocol=protocol)
        self.__protocol_cls: Callable[[], AbstractNetworkProtocol] = protocol_cls
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

        client: UDPNetworkClient[_T] = self.__client

        def parse_requests() -> None:
            with self.__lock:
                for request, address in client.recv_packets(block=True, flags=self.recv_flags):
                    connected_client: ConnectedClient[_T] = self.__ConnectedClient(client, address)
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
    def _process_request(self, request: _T, client: ConnectedClient[_T]) -> None:
        raise NotImplementedError

    def _handle_error(self, client: ConnectedClient[_T]) -> None:
        from sys import stderr
        from traceback import print_exc

        client_address: tuple[Any, ...] = tuple(client.address)
        print("-" * 40, file=stderr)
        print(f"Exception occurred during processing of request from {client_address}", file=stderr)
        print_exc()
        print("-" * 40, file=stderr)

    def running(self) -> bool:
        with self.__lock:
            return self.__loop

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    @final
    @property
    def server_address(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @final
    @property
    def protocol_cls(self) -> Callable[[], AbstractNetworkProtocol]:
        return self.__protocol_cls

    @property
    def recv_flags(self) -> int:
        with self.__lock:
            return self.__recv_flags

    @recv_flags.setter
    def recv_flags(self, value: int) -> None:
        with self.__lock:
            self.__recv_flags = int(value)

    @final
    class __ConnectedClient(ConnectedClient[_T]):
        def __init__(self, client: UDPNetworkClient[_T], address: SocketAddress) -> None:
            super().__init__(address)
            self.__client: UDPNetworkClient[_T] = client

        def close(self) -> None:
            client: UDPNetworkClient[_T] = self.__client
            return client.close()

        def send_packet(self, packet: _T, *, flags: int = 0) -> None:
            client: UDPNetworkClient[_T] = self.__client
            return client.send_packet(self.address, packet, flags=flags)


@concreteclass
class UDPNetworkServer(AbstractUDPNetworkServer[_T]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_T]],
        *,
        family: int = ...,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
        socket_cls: type[AbstractUDPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPServerSocket,
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_T]],
        *,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(self, __arg: Any, /, request_handler_cls: type[AbstractUDPRequestHandler[_T]], **kwargs: Any) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractUDPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a UDP request handler")
        self.__request_handler_cls: type[AbstractUDPRequestHandler[_T]] = request_handler_cls
        super().__init__(__arg, **kwargs)

    def _process_request(self, request: _T, client: ConnectedClient[_T]) -> None:
        self.__request_handler_cls(request, client, self)

    @final
    @property
    def request_handler_cls(self) -> type[AbstractUDPRequestHandler[_T]]:
        return self.__request_handler_cls
