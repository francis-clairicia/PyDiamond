# -*- coding: Utf-8 -*
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

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from contextlib import suppress
from selectors import EVENT_READ
from threading import Event, RLock, current_thread
from typing import TYPE_CHECKING, Any, Callable, Generic, Sequence, TypeVar, final, overload

from ..system.threading import Thread, thread
from ..system.utils import concreteclass, concreteclasscheck, dsuppress
from .client import DisconnectedClientError, TCPNetworkClient, UDPNetworkClient
from .protocol.base import AbstractNetworkProtocol
from .protocol.pickle import PicklingNetworkProtocol
from .socket.base import AbstractSocket, AbstractTCPServerSocket, AbstractUDPServerSocket, SocketAddress
from .socket.python import PythonTCPServerSocket, PythonUDPServerSocket

if TYPE_CHECKING:
    from selectors import BaseSelector

    _Selector: type[BaseSelector]

try:
    from selectors import PollSelector as _Selector
except ImportError:
    from selectors import SelectSelector as _Selector

_T = TypeVar("_T")


class ConnectedClient(Generic[_T]):
    def __init__(self, address: SocketAddress) -> None:
        super().__init__()
        self.__addr: SocketAddress = address

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_packet(self, packet: _T, *, flags: int = 0) -> None:
        raise NotImplementedError

    @property
    def address(self) -> SocketAddress:
        return self.__addr


class _MetaRequestHandler(ABCMeta):
    __Self = TypeVar("__Self", bound="_MetaRequestHandler")

    def __new__(metacls: type[__Self], name: str, bases: tuple[type, ...], namespace: dict[str, Any]) -> __Self:
        try:
            AbstractRequestHandler
        except NameError:
            pass
        else:
            for attr in ["__init__"]:
                if attr in namespace:
                    raise TypeError(f"{attr!r} method must not be overridden")
        return super().__new__(metacls, name, bases, namespace)

    del __Self


class AbstractRequestHandler(Generic[_T], metaclass=_MetaRequestHandler):
    @overload
    def __init__(self, request: _T, client: ConnectedClient[_T], server: AbstractTCPNetworkServer[_T]) -> None:
        ...

    @overload
    def __init__(self, request: _T, client: ConnectedClient[_T], server: AbstractUDPNetworkServer[_T]) -> None:
        ...

    @final
    def __init__(self, request: _T, client: ConnectedClient[_T], server: AbstractNetworkServer[_T]) -> None:
        self.request: _T = request
        self.client: ConnectedClient[_T] = client
        self.server: AbstractNetworkServer[_T] = server
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


class AbstractNetworkServer(Generic[_T], metaclass=ABCMeta):
    __Self = TypeVar("__Self", bound="AbstractNetworkServer[Any]")

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
        elif self.running():
            self.shutdown()
        self.server_close()

    @abstractmethod
    def serve_forever(self, poll_interval: float = ...) -> None:
        raise NotImplementedError

    def serve_forever_in_thread(self, poll_interval: float = 0.5) -> Thread:
        if self.running():
            raise RuntimeError("Server already running")

        @thread
        def run(self: AbstractNetworkServer[Any], poll_interval: float) -> None:
            try:
                self.serve_forever(poll_interval)
            except:
                from traceback import print_exc

                print(f"Exception not handled in {type(self).__name__} running in thread {current_thread().name!r}")
                print_exc()

        if self.__t is not None:
            self.__t.join()
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

    @abstractmethod
    def service_actions(self) -> None:
        raise NotImplementedError

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
    def fileno(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def server_address(self) -> SocketAddress:
        raise NotImplementedError

    @property
    @abstractmethod
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        raise NotImplementedError

    del __Self


class AbstractTCPNetworkServer(AbstractNetworkServer[_T]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
        socket_cls: type[AbstractTCPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPServerSocket,
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        arg: AbstractTCPServerSocket | tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = PicklingNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(protocol_cls)
        socket: AbstractTCPServerSocket
        if isinstance(arg, AbstractTCPServerSocket):
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = arg
        elif isinstance(arg, tuple):
            address: tuple[str, int] | tuple[str, int, int, int] = arg
            socket_cls: type[AbstractTCPServerSocket] = kwargs.pop("socket_cls", PythonTCPServerSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.bind(address, **kwargs)
        else:
            raise TypeError("Invalid arguments")
        self.__socket: AbstractTCPServerSocket = socket
        self.__protocol_cls: type[AbstractNetworkProtocol] = protocol_cls
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

        def new_client(selector: BaseSelector) -> None:
            try:
                client_socket, address = socket.accept()
            except OSError:
                return
            client: TCPNetworkClient[_T] = TCPNetworkClient(client_socket, protocol_cls=self.protocol_cls)
            if not self._verify_new_client(client, address):
                client.close()
                return
            selector.register(client, EVENT_READ, data=parse_requests)
            clients_dict[client] = self.__ConnectedClient(client, address)

        def parse_requests(client: TCPNetworkClient[_T], selector: BaseSelector) -> None:
            if not client.is_connected():
                return
            try:
                for request in client.recv_packets(block=True, flags=self.recv_flags):
                    connected_client: ConnectedClient[_T] = clients_dict[client]
                    try:
                        self._process_request(request, connected_client)
                    except Exception:
                        self._handle_error(connected_client)
            except DisconnectedClientError:
                shutdown_client(client, selector)
            except:
                shutdown_client(client, selector)
                raise

        def shutdown_client(client: TCPNetworkClient[_T], selector: BaseSelector) -> None:
            client.close()
            with suppress(KeyError):
                selector.unregister(client)
            clients_dict.pop(client, None)

        def remove_closed_clients(selector: BaseSelector) -> None:
            with self.__lock:
                for client in filter(lambda client: not client.is_connected(), tuple(clients_dict)):
                    with suppress(KeyError):
                        selector.unregister(client)
                    clients_dict.pop(client, None)

        with _Selector() as selector:
            selector.register(self, EVENT_READ, data=lambda _, selector: new_client(selector))
            try:
                while self.running():
                    ready = selector.select(poll_interval)
                    if not self.running():
                        break
                    with self.__lock:
                        for key, _ in ready:
                            callback: Callable[[Any, BaseSelector], None] = key.data
                            callback(key.fileobj, selector)
                        remove_closed_clients(selector)
                    self.service_actions()
            finally:
                try:
                    with self.__lock:
                        self.__loop = False
                        for client in tuple(clients_dict):
                            shutdown_client(client, selector)
                finally:
                    clients_dict.clear()
                    self.__is_shutdown.set()

    def running(self) -> bool:
        with self.__lock:
            return self.__loop

    def service_actions(self) -> None:
        pass

    def server_close(self) -> None:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            if socket.is_open():
                socket.close()

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def _verify_new_client(self, client: TCPNetworkClient[_T], address: SocketAddress) -> bool:
        return True

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

    def fileno(self) -> int:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.fileno()

    @property
    def server_address(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @property
    def backlog(self) -> int:
        with self.__lock:
            socket: AbstractTCPServerSocket = self.__socket
            return socket.listening()

    @backlog.setter
    def backlog(self, backlog: int) -> None:
        with self.__lock:
            socket: AbstractTCPServerSocket = self.__socket
            return socket.listen(backlog)

    @property
    def clients(self) -> Sequence[ConnectedClient[_T]]:
        with self.__lock:
            return tuple(self.__clients.values())

    @property
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        return self.__protocol_cls

    @property
    def recv_flags(self) -> int:
        with self.__lock:
            return self.__recv_flags

    @recv_flags.setter
    def recv_flags(self, value: int) -> None:
        with self.__lock:
            self.__recv_flags = int(value)

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
        protocol_cls: type[AbstractNetworkProtocol] = ...,
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
        protocol_cls: type[AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(self, arg: Any, /, request_handler_cls: type[AbstractTCPRequestHandler[_T]], **kwargs: Any) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractTCPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a TCP request handler")
        self.__request_handler_cls: type[AbstractTCPRequestHandler[_T]] = request_handler_cls
        super().__init__(arg, **kwargs)

    def _process_request(self, request: _T, client: ConnectedClient[_T]) -> None:
        self.request_handler_cls(request, client, self)  # type: ignore

    @property
    def request_handler_cls(self) -> type[AbstractTCPRequestHandler[_T]]:
        return self.__request_handler_cls


class AbstractUDPNetworkServer(AbstractNetworkServer[_T]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
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
        *,
        protocol_cls: type[AbstractNetworkProtocol] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        arg: AbstractUDPServerSocket | tuple[str, int] | tuple[str, int, int, int],
        /,
        *,
        protocol_cls: type[AbstractNetworkProtocol] = PicklingNetworkProtocol,
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(protocol_cls)
        socket: AbstractUDPServerSocket
        if isinstance(arg, AbstractUDPServerSocket):
            if kwargs:
                raise TypeError("Invalid arguments")
            socket = arg
        elif isinstance(arg, tuple):
            address: tuple[str, int] | tuple[str, int, int, int] = arg
            socket_cls: type[AbstractUDPServerSocket] = kwargs.pop("socket_cls", PythonUDPServerSocket)
            concreteclasscheck(socket_cls)
            socket = socket_cls.bind(address, **kwargs)
        else:
            raise TypeError("Invalid arguments")
        self.__socket: AbstractUDPServerSocket = socket
        self.__client: UDPNetworkClient[_T] = UDPNetworkClient(socket, protocol_cls=protocol_cls)
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

        client: UDPNetworkClient[_T] = self.__client

        def parse_requests() -> None:
            with self.__lock:
                for request, address in client.recv_packets(block=True, flags=self.recv_flags):
                    connected_client: ConnectedClient[_T] = self.__ConnectedClient(client, address)
                    try:
                        self._process_request(request, connected_client)
                    except Exception:
                        self._handle_error(connected_client)

        with _Selector() as selector:
            selector.register(self, EVENT_READ)
            with self.__lock:
                self.__loop = True
                self.__is_shutdown.clear()
            try:
                while self.running():
                    ready: bool = len(selector.select(poll_interval)) > 0
                    if not self.running():
                        break
                    if ready:
                        parse_requests()
                    self.service_actions()
            finally:
                self.__loop = False
                self.__is_shutdown.set()

    def server_close(self) -> None:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            if socket.is_open():
                socket.close()

    def service_actions(self) -> None:
        pass

    def running(self) -> bool:
        with self.__lock:
            return self.__loop

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

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

    def fileno(self) -> int:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.fileno()

    @property
    def server_address(self) -> SocketAddress:
        with self.__lock:
            socket: AbstractSocket = self.__socket
            return socket.getsockname()

    @property
    def protocol_cls(self) -> type[AbstractNetworkProtocol]:
        with self.__lock:
            client: UDPNetworkClient[_T] = self.__client
            return client.protocol_cls

    @property
    def recv_flags(self) -> int:
        with self.__lock:
            return self.__recv_flags

    @recv_flags.setter
    def recv_flags(self, value: int) -> None:
        with self.__lock:
            self.__recv_flags = int(value)

    class __ConnectedClient(ConnectedClient[_T]):
        def __init__(self, client: UDPNetworkClient[_T], address: SocketAddress) -> None:
            super().__init__(address)
            self.__client: UDPNetworkClient[_T] = client

        def close(self) -> None:
            client: UDPNetworkClient[_T] = self.__client
            return client.close()

        def send_packet(self, packet: _T, *, flags: int = 0) -> None:
            client: UDPNetworkClient[_T] = self.__client
            return client.send_packet(packet, self.address, flags=flags)


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

    def __init__(self, arg: Any, /, request_handler_cls: type[AbstractUDPRequestHandler[_T]], **kwargs: Any) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractUDPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a UDP request handler")
        self.__request_handler_cls: type[AbstractUDPRequestHandler[_T]] = request_handler_cls
        super().__init__(arg, **kwargs)

    def _process_request(self, request: _T, client: ConnectedClient[_T]) -> None:
        self.request_handler_cls(request, client, self)  # type: ignore

    @property
    def request_handler_cls(self) -> type[AbstractUDPRequestHandler[_T]]:
        return self.__request_handler_cls


del _T
