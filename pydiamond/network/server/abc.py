# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network server abstract base classes module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkServer",
    "AbstractTCPNetworkServer",
    "AbstractUDPNetworkServer",
    "ConnectedClient",
]

from abc import abstractmethod
from contextlib import suppress
from selectors import EVENT_READ, BaseSelector
from socket import SOCK_DGRAM, SOCK_STREAM, socket as Socket
from threading import Event, RLock, current_thread
from typing import TYPE_CHECKING, Any, Callable, Generic, Sequence, TypeAlias, TypeVar

from ...system.object import Object, final
from ...system.threading import Thread, thread_factory
from ...system.utils.functools import dsuppress
from ..client import DisconnectedClientError, TCPNetworkClient, UDPNetworkClient
from ..protocol.abc import NetworkProtocol
from ..protocol.pickle import PickleNetworkProtocol
from ..protocol.stream import StreamNetworkProtocol
from ..selector import DefaultSelector as _Selector
from ..socket import AF_INET, SocketAddress, create_server, new_socket_address

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


class AbstractNetworkServer(Object):
    __slots__ = ("__t",)

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
        **kwargs: Any,
    ) -> Thread:
        if self.running():
            raise RuntimeError("Server already running")

        @thread_factory(daemon=daemon, name=name)
        def run(self: AbstractNetworkServer, poll_interval: float, **kwargs: Any) -> None:
            self.serve_forever(poll_interval, **kwargs)

        t: Thread | None = self.__t
        if t is not None and t.is_alive():
            t.join()
        self.__t = t = run(self, poll_interval, **kwargs)
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

StreamNetworkProtocolFactory: TypeAlias = Callable[[], StreamNetworkProtocol[_ResponseT, _RequestT]]


class AbstractTCPNetworkServer(AbstractNetworkServer, Generic[_RequestT, _ResponseT]):
    __slots__ = (
        "__socket",
        "__addr",
        "__protocol_cls",
        "__closed",
        "__lock",
        "__loop",
        "__is_shutdown",
        "__is_shutdown",
        "__clients",
    )

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
        backlog: int | None = None,
        reuse_port: bool = False,
        dualstack_ipv6: bool = False,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT] = PickleNetworkProtocol,
    ) -> None:
        if not callable(protocol_cls):
            raise TypeError("Invalid arguments")
        self.__socket: Socket = create_server(
            address,
            family=family,
            type=SOCK_STREAM,
            backlog=backlog,
            reuse_port=reuse_port,
            dualstack_ipv6=dualstack_ipv6,
        )
        self.__addr: SocketAddress = new_socket_address(self.__socket.getsockname(), self.__socket.family)
        self.__closed: bool = False
        self.__protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT] = protocol_cls
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__clients: dict[TCPNetworkClient[_ResponseT, _RequestT], ConnectedClient[_ResponseT]] = {}
        super().__init__()

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        if self.running():
            raise RuntimeError("Server already running")
        with self.__lock:
            self.__loop = True
            self.__is_shutdown.clear()
        socket: Socket = self.__socket
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
            address = new_socket_address(address, client_socket.family)
            protocol = self.__protocol_cls()
            client: TCPNetworkClient[_ResponseT, _RequestT] = TCPNetworkClient(client_socket, protocol=protocol, give=True)
            verify_client(client, address)

        def parse_requests(client: TCPNetworkClient[_ResponseT, _RequestT]) -> None:
            if not client.is_connected():
                return
            try:
                connected_client: ConnectedClient[_ResponseT] = clients_dict[client]
                for request in client.recv_packets(timeout=None):  # TODO: Handle one packet per loop
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
            if self.__closed:
                return
            self.__closed = True
            self.__socket.close()
            del self.__socket

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def _verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True

    @property
    @final
    def server_address(self) -> SocketAddress:
        return self.__addr

    @final
    def listen(self, backlog: int) -> None:
        return self.__socket.listen(backlog)

    @property
    @final
    def clients(self) -> Sequence[ConnectedClient[_ResponseT]]:
        with self.__lock:
            return tuple(self.__clients.values())

    @final
    class __ConnectedClient(ConnectedClient[_ResponseT]):
        def __init__(self, client: TCPNetworkClient[_ResponseT, Any], address: SocketAddress) -> None:
            super().__init__(address)
            self.__client: TCPNetworkClient[_ResponseT, Any] = client

        def close(self) -> None:
            return self.__client.close()

        def send_packet(self, packet: _ResponseT, *, flags: int = 0) -> None:
            if flags != 0:
                raise NotImplementedError("flags not implemented")
            return self.__client.send_packet(packet)


class AbstractUDPNetworkServer(AbstractNetworkServer, Generic[_RequestT, _ResponseT]):
    __slots__ = (
        "__client",
        "__addr",
        "__lock",
        "__loop",
        "__is_shutdown",
        "__is_shutdown",
        "__recv_flags",
    )

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
        reuse_port: bool = False,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = PickleNetworkProtocol,
    ) -> None:
        protocol = protocol_cls()
        if not isinstance(protocol, NetworkProtocol):
            raise TypeError("Invalid arguments")
        socket = create_server(
            address,
            family=family,
            type=SOCK_DGRAM,
            backlog=None,
            reuse_port=reuse_port,
            dualstack_ipv6=False,
        )
        self.__client: UDPNetworkClient[_ResponseT, _RequestT] = UDPNetworkClient(socket, protocol=protocol, give=True)
        self.__addr: SocketAddress = self.__client.getsockname()
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
                for request, address in client.recv_packets(timeout=None, flags=self.recv_flags):
                    connected_client: ConnectedClient[_ResponseT] = self.__ConnectedClient(client, address)
                    try:
                        self._process_request(request, connected_client)
                    except DisconnectedClientError:
                        raise
                    except Exception:
                        self._handle_error(connected_client)

        with _Selector() as selector:
            selector.register(self.__client, EVENT_READ)
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
            self.__client.close()

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
            return self.__addr

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
