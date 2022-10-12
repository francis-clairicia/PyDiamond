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
from collections import defaultdict, deque
from contextlib import contextmanager, suppress
from dataclasses import dataclass
from selectors import EVENT_READ, EVENT_WRITE, BaseSelector, DefaultSelector as _Selector, SelectorKey
from socket import SHUT_WR, SOCK_DGRAM, SOCK_STREAM, socket as Socket
from threading import Event, RLock, current_thread
from typing import TYPE_CHECKING, Any, Callable, Generic, Iterator, Sequence, TypeAlias, TypeVar, overload
from weakref import WeakKeyDictionary

from ...system.object import Object, final
from ...system.threading import Thread, thread_factory
from ...system.utils.functools import dsuppress
from ..client import TCPNetworkClient, UDPNetworkClient
from ..protocol.abc import NetworkProtocol
from ..protocol.pickle import PickleNetworkProtocol
from ..protocol.stream import StreamNetworkProtocol
from ..socket import AF_INET, SocketAddress, create_server, guess_best_buffer_size, new_socket_address
from ..tools.stream import StreamNetworkDataConsumer, StreamNetworkDataProducer

_RequestT = TypeVar("_RequestT")
_ResponseT = TypeVar("_ResponseT")


class ConnectedClient(Generic[_ResponseT], Object):
    __slots__ = ("__addr", "__weakref__")

    def __init__(self, address: SocketAddress) -> None:
        super().__init__()
        self.__addr: SocketAddress = address

    def __repr__(self) -> str:
        return f"<connected client with address {self.__addr} at {id(self):#x}{' closed' if self.closed else ''}>"

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_packet(self, packet: _ResponseT) -> None:
        raise NotImplementedError

    def send_packets(self, *packets: _ResponseT) -> None:
        send_packet = self.send_packet
        for packet in packets:
            send_packet(packet)

    @abstractmethod
    def detach(self) -> Socket:
        raise NotImplementedError

    @property
    @abstractmethod
    def closed(self) -> bool:
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
    def address(self) -> SocketAddress:
        raise NotImplementedError


class _AbstractNetworkServerImpl(AbstractNetworkServer):
    __slots__ = ()

    def _handle_error(self, client: ConnectedClient[_ResponseT]) -> None:
        from sys import stderr
        from traceback import print_exc

        print("-" * 40, file=stderr)
        print(f"Exception occurred during processing of request from {client.address}", file=stderr)
        print_exc(file=stderr)
        print("-" * 40, file=stderr)


NetworkProtocolFactory: TypeAlias = Callable[[], NetworkProtocol[_ResponseT, _RequestT]]

StreamNetworkProtocolFactory: TypeAlias = Callable[[], StreamNetworkProtocol[_ResponseT, _RequestT]]


class AbstractTCPNetworkServer(_AbstractNetworkServerImpl, Generic[_RequestT, _ResponseT]):
    __slots__ = (
        "__socket",
        "__addr",
        "__protocol_cls",
        "__closed",
        "__lock",
        "__loop",
        "__is_shutdown",
        "__clients",
        "__selector",
        "__default_backlog",
        "__verify_in_thread",
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
        verify_client_in_thread: bool = False,
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
        self.__default_backlog: int | None = backlog
        self.__addr: SocketAddress = new_socket_address(self.__socket.getsockname(), self.__socket.family)
        self.__closed: bool = False
        self.__protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT] = protocol_cls
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__clients: WeakKeyDictionary[Socket, ConnectedClient[_ResponseT]] = WeakKeyDictionary()
        self.__selector: BaseSelector
        self.__verify_in_thread: bool = bool(verify_client_in_thread)
        super().__init__()

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        poll_interval = float(poll_interval)

        with self.__lock:
            self._check_closed()
            if self.running():
                raise RuntimeError("Server already running")
            self.__is_shutdown.clear()
            self.__selector = _Selector()
            self.__loop = True

        server_socket: Socket = self.__socket

        def select() -> dict[int, deque[SelectorKey]]:
            ready: defaultdict[int, deque[SelectorKey]] = defaultdict(deque)
            for key, events in selector.select(timeout=poll_interval):
                for mask in {EVENT_READ, EVENT_WRITE}:
                    if events & mask:
                        ready[mask].append(key)
            return ready

        def selector_client_keys() -> list[SelectorKey]:
            return [key for key in selector.get_map().values() if key.fileobj is not server_socket]

        def verify_client(socket: Socket, address: SocketAddress) -> None:
            protocol = self.__protocol_cls()
            with TCPNetworkClient(socket, protocol=protocol, give=False) as client:
                accepted = self._verify_new_client(client, address)
            if not accepted:
                socket.close()
                return
            key_data = _SelectorKeyData(
                protocol=protocol,
                socket=socket,
                address=address,
            )
            key_data.consumer.feed(client._get_buffer())
            key_data.extra_queue = client.flush_queue()
            del client
            with self.__lock:
                self.__clients[socket] = key_data.client
                selector.register(socket, EVENT_READ | EVENT_WRITE, key_data)

        verify_client_in_thread = thread_factory(daemon=True, auto_start=True)(verify_client)

        def new_client() -> None:
            try:
                client_socket, address = server_socket.accept()
            except OSError:
                return
            address = new_socket_address(address, client_socket.family)
            if self.__verify_in_thread:
                verify_client_in_thread(client_socket, address)
            else:
                verify_client(client_socket, address)

        def receive_requests(ready: Sequence[SelectorKey]) -> None:
            for key in list(ready):
                socket: Socket = key.fileobj  # type: ignore[assignment]
                if socket is server_socket:
                    new_client()
                    continue
                key_data: _SelectorKeyData[_RequestT, _ResponseT] = key.data
                client = key_data.client
                data: bytes
                if client.closed:
                    shutdown_client(socket)
                    continue
                try:
                    data = socket.recv(key_data.chunk_size)
                except Exception:
                    try:
                        client.close()
                        self._handle_error(client)
                    finally:
                        shutdown_client(socket)
                else:
                    if not data:  # Closed connection (EOF)
                        shutdown_client(socket)
                        continue
                    key_data.consumer.feed(data)

        def process_requests(ready: Sequence[SelectorKey]) -> None:
            for key in selector_client_keys():
                key_data: _SelectorKeyData[_RequestT, _ResponseT] = key.data
                client = key_data.client
                if client.closed:
                    continue
                request: _RequestT
                if key_data.extra_queue:
                    request = key_data.extra_queue.popleft()
                else:
                    if key not in ready:
                        continue
                    try:
                        request = next(key_data.consumer)
                    except StopIteration:  # Not enough data
                        continue
                try:
                    self._process_request(request, client)
                except Exception:
                    self._handle_error(client)

        def send_responses(ready: Sequence[SelectorKey]) -> None:
            for key in list(ready):
                key_data: _SelectorKeyData[_RequestT, _ResponseT] = key.data
                producer = key_data.producer
                if not producer:  # There is nothing to send
                    continue
                socket: Socket = key.fileobj  # type: ignore[assignment]
                client = key_data.client
                data: bytes
                if client.closed:
                    with suppress(Exception):
                        data = producer.read()
                        if data:
                            socket.sendall(data)
                    shutdown_client(socket)
                    continue
                try:
                    data = producer.read(key_data.chunk_size)
                except Exception:
                    self._handle_error(client)
                    continue
                if not data:
                    continue
                try:
                    socket.sendall(data)
                except Exception:
                    try:
                        client.close()
                        self._handle_error(client)
                    finally:
                        shutdown_client(socket)

        def shutdown_client(socket: Socket) -> None:
            if (client := self.__clients.pop(socket, None)):
                if not client.closed:
                    client.close()
                try:
                    self._on_disconnect(client)
                except Exception:
                    self._handle_error(client)
            try:
                key = selector.unregister(socket)
            except KeyError:
                return
            for key_sequences in ready.values():
                if key in key_sequences:
                    key_sequences.remove(key)
            with suppress(Exception):
                try:
                    socket.shutdown(SHUT_WR)
                finally:
                    socket.close()

        def remove_closed_clients() -> None:
            for key in selector_client_keys():
                socket: Socket = key.fileobj  # type: ignore[assignment]
                try:
                    socket.getpeername()
                except OSError:  # Broken connection
                    shutdown_client(socket)
                key_data: _SelectorKeyData[_RequestT, _ResponseT] = key.data
                if key_data.client.closed:
                    shutdown_client(socket)

        def destroy_all_clients() -> None:
            for key in selector_client_keys():
                socket: Socket = key.fileobj  # type: ignore[assignment]
                shutdown_client(socket)

        try:
            with self.__selector as selector:
                selector.register(server_socket, EVENT_READ)
                try:
                    while self.__loop:
                        ready = select()
                        if not self.__loop:
                            break  # type: ignore[unreachable]
                        with self.__lock:
                            receive_requests(ready.get(EVENT_READ, ()))
                            process_requests(ready.get(EVENT_READ, ()))
                            send_responses(ready.get(EVENT_WRITE, ()))
                            self.service_actions()
                            remove_closed_clients()
                finally:
                    with self.__lock:
                        destroy_all_clients()
        finally:
            with self.__lock:
                del self.__selector
                self.__loop = False
                self.__is_shutdown.set()

    @final
    def running(self) -> bool:
        return not self.__is_shutdown.is_set()

    def service_actions(self) -> None:
        pass

    @abstractmethod
    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        raise NotImplementedError

    def server_close(self) -> None:
        with self.__lock:
            if not self.__is_shutdown.is_set():
                raise RuntimeError("Cannot close running server. Use shutdown() first")
            if self.__closed:
                return
            self.__closed = True
            self.__socket.close()
            del self.__socket

    def shutdown(self) -> None:
        self._check_closed()
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def _verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True

    def _on_disconnect(self, client: ConnectedClient[_ResponseT]) -> None:
        pass

    @contextmanager
    def stop_listening(self) -> Iterator[None]:
        if not self.__loop:
            raise RuntimeError("Server is not running")
        selector: BaseSelector = self.__selector
        server_socket: Socket = self.__socket
        key: SelectorKey | None
        with self.__lock:
            try:
                key = selector.unregister(server_socket)
            except KeyError:
                key = None
        if key is None:
            yield
            return
        try:
            server_socket.listen(0)
            yield
        finally:
            if self.__loop:
                default_backlog: int | None = self.__default_backlog
                if default_backlog is None:
                    server_socket.listen()
                else:
                    server_socket.listen(default_backlog)
                with self.__lock:
                    selector.register(key.fileobj, key.events, key.data)

    def new_protocol(self) -> StreamNetworkProtocol[_ResponseT, _RequestT]:
        return self.__protocol_cls()

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
            raise RuntimeError("Closed server")

    @property
    @final
    def address(self) -> SocketAddress:
        self._check_closed()
        return self.__addr

    @property
    @final
    def clients(self) -> Sequence[ConnectedClient[_ResponseT]]:
        self._check_closed()
        with self.__lock:
            return tuple(filter(lambda client: not client.closed, self.__clients.values()))


@dataclass(init=False)
class _SelectorKeyData(Generic[_RequestT, _ResponseT]):
    producer: StreamNetworkDataProducer[_ResponseT]
    consumer: StreamNetworkDataConsumer[_RequestT]
    chunk_size: int
    client: ConnectedClient[_ResponseT]
    extra_queue: deque[_RequestT]

    def __init__(
        self,
        *,
        protocol: StreamNetworkProtocol[_ResponseT, _RequestT],
        socket: Socket,
        address: SocketAddress,
    ) -> None:
        self.producer = StreamNetworkDataProducer(protocol)
        self.consumer = StreamNetworkDataConsumer(protocol)
        self.chunk_size = guess_best_buffer_size(socket)
        self.client = self.__ConnectedClient(self.producer, socket, address)
        self.extra_queue = deque()

    @final
    class __ConnectedClient(ConnectedClient[_ResponseT]):
        __slots__ = ("__p", "__s", "__lock")

        def __init__(
            self,
            producer: StreamNetworkDataProducer[_ResponseT],
            socket: Socket,
            address: SocketAddress,
        ) -> None:
            super().__init__(address)
            self.__p: StreamNetworkDataProducer[_ResponseT] | None = producer
            self.__s: Socket | None = socket
            self.__lock = RLock()

        def close(self) -> None:
            with self.__lock:
                self.__p = None
                self.__s = None

        def send_packet(self, packet: _ResponseT) -> None:
            with self.__lock:
                if self.__p is None:
                    raise RuntimeError("Closed client")
                self.__p.queue(packet)

        def send_packets(self, *packets: _ResponseT) -> None:
            with self.__lock:
                if self.__p is None:
                    raise RuntimeError("Closed client")
                self.__p.queue(*packets)

        def detach(self) -> Socket:
            with self.__lock:
                socket = self.__s
                producer = self.__p
                if socket is None or producer is None:
                    raise RuntimeError("Closed client")
                fd: int = socket.detach()
                if fd < 0:
                    raise OSError("Closed socket")
                socket = Socket(fileno=fd)
                self.close()
                try:
                    # Flush all buffer before return
                    if data := producer.read():
                        socket.sendall(data)
                except BaseException:
                    socket.close()
                    raise
                return socket

        @property
        def closed(self) -> bool:
            return self.__p is None


class AbstractUDPNetworkServer(_AbstractNetworkServerImpl, Generic[_RequestT, _ResponseT]):
    __slots__ = (
        "__server",
        "__addr",
        "__lock",
        "__loop",
        "__is_shutdown",
        "__is_shutdown",
        "__flags",
        "__protocol_cls",
    )

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
        reuse_port: bool = False,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = PickleNetworkProtocol,
        flags: int = 0,
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
        self.__server: UDPNetworkClient[_ResponseT, _RequestT] = UDPNetworkClient(socket, protocol=protocol, give=True)
        self.__addr: SocketAddress = self.__server.getsockname()
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__flags: int = int(flags)
        self.__protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = protocol_cls
        super().__init__()

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        poll_interval = float(poll_interval)

        with self.__lock:
            self._check_closed()
            if self.running():
                raise RuntimeError("Server already running")
            self.__is_shutdown.clear()
            self.__loop = True

        server: UDPNetworkClient[_ResponseT, _RequestT] = self.__server
        make_connected_client = self.__ConnectedClient

        write_queue: deque[tuple[_ResponseT, SocketAddress]] = deque()

        def parse_requests() -> None:
            flags: int = self.__flags
            for request, address in server.recv_packets(timeout=None, flags=flags):
                connected_client = make_connected_client(write_queue, address)
                try:
                    self._process_request(request, connected_client)
                except Exception:
                    self._handle_error(connected_client)
                finally:
                    connected_client.close()

        def send_a_response() -> None:
            flags: int = self.__flags
            try:
                response, address = write_queue.popleft()
            except IndexError:
                return
            try:
                server.send_packet(address, response, flags=flags)
            except Exception:
                connected_client: ConnectedClient[_ResponseT] = make_connected_client(None, address)
                self._handle_error(connected_client)

        with _Selector() as selector:
            selector.register(server, EVENT_READ | EVENT_WRITE)
            try:
                while self.__loop:
                    ready: int
                    try:
                        ready = selector.select(timeout=poll_interval)[0][1]
                    except IndexError:
                        ready = 0
                    if not self.__loop:
                        break  # type: ignore[unreachable]
                    with self.__lock:
                        if ready & EVENT_READ:
                            parse_requests()
                        if ready & EVENT_WRITE and write_queue:
                            send_a_response()
                        self.service_actions()
            finally:
                with self.__lock:
                    self.__loop = False
                    self.__is_shutdown.set()

    def server_close(self) -> None:
        with self.__lock:
            if not self.__is_shutdown.is_set():
                raise RuntimeError("Cannot close running server. Use shutdown() first")
            if not self.__server.closed:
                self.__server.close()

    def service_actions(self) -> None:
        pass

    @abstractmethod
    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        raise NotImplementedError

    def running(self) -> bool:
        with self.__lock:
            return not self.__is_shutdown.is_set()

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def new_protocol(self) -> NetworkProtocol[_ResponseT, _RequestT]:
        return self.__protocol_cls()

    @overload
    def getsockopt(self, __level: int, __optname: int, /) -> int:
        ...

    @overload
    def getsockopt(self, __level: int, __optname: int, __buflen: int, /) -> bytes:
        ...

    def getsockopt(self, *args: int) -> int | bytes:
        self._check_closed()
        return self.__server.getsockopt(*args)

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: int | bytes, /) -> None:
        ...

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: None, __optlen: int, /) -> None:
        ...

    def setsockopt(self, *args: Any) -> None:
        self._check_closed()
        return self.__server.setsockopt(*args)

    @final
    def _check_closed(self) -> None:
        if self.__server.closed:
            raise RuntimeError("Closed server")

    @property
    @final
    def address(self) -> SocketAddress:
        with self.__lock:
            return self.__addr

    @property
    @final
    def flags(self) -> int:
        with self.__lock:
            return self.__flags

    @final
    class __ConnectedClient(ConnectedClient[_ResponseT]):
        __slots__ = ("__q", "__lock")

        def __init__(self, queue: deque[tuple[_ResponseT, SocketAddress]] | None, address: SocketAddress) -> None:
            super().__init__(address)
            self.__q: deque[tuple[_ResponseT, SocketAddress]] | None = queue
            self.__lock = RLock()

        def close(self) -> None:
            with self.__lock:
                self.__q = None

        def send_packet(self, packet: _ResponseT) -> None:
            with self.__lock:
                if self.__q is None:
                    raise RuntimeError("Closed client")
                self.__q.append((packet, self.address))

        def send_packets(self, *packets: _ResponseT) -> None:
            if not packets:
                return
            with self.__lock:
                if self.__q is None:
                    raise RuntimeError("Closed client")
                self.__q.extend((p, self.address) for p in packets)

        def detach(self) -> Socket:
            raise NotImplementedError("detach() not available")

        @property
        def closed(self) -> bool:
            return self.__q is None
