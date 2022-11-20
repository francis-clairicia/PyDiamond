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
from typing import TYPE_CHECKING, Any, Callable, Final, Generic, Iterator, Sequence, TypeAlias, TypeVar, overload
from weakref import WeakKeyDictionary

from ...system.object import Object, final
from ...system.threading import Thread, thread_factory
from ...system.utils.contextlib import dsuppress
from ..client import TCPNetworkClient, UDPNetworkClient
from ..protocol.abc import NetworkProtocol
from ..protocol.exceptions import DeserializeError
from ..protocol.stream.abc import StreamNetworkProtocol
from ..socket import AF_INET, SocketAddress, create_server, guess_best_buffer_size, new_socket_address
from ..tools.stream import StreamNetworkDataConsumer, StreamNetworkDataProducer

_RequestT = TypeVar("_RequestT")
_ResponseT = TypeVar("_ResponseT")


class ConnectedClient(Generic[_ResponseT], Object):
    __slots__ = ("__addr", "__transaction_lock", "__weakref__")

    def __init__(self, address: SocketAddress) -> None:
        super().__init__()
        self.__addr: SocketAddress = address
        self.__transaction_lock = RLock()

    def __repr__(self) -> str:
        return f"<connected client with address {self.__addr} at {id(self):#x}{' closed' if self.closed else ''}>"

    @final
    @contextmanager
    def transaction(self) -> Iterator[None]:
        with self.__transaction_lock:
            yield

    def shutdown(self) -> None:
        with self.transaction():
            if not self.closed:
                try:
                    self.flush()
                finally:
                    self.close()

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def send_packet(self, packet: _ResponseT) -> None:
        raise NotImplementedError

    def send_packets(self, *packets: _ResponseT) -> None:
        with self.transaction():
            send_packet = self.send_packet
            for packet in packets:
                send_packet(packet)

    @abstractmethod
    def flush(self) -> None:
        raise NotImplementedError

    @property
    @abstractmethod
    def closed(self) -> bool:
        raise NotImplementedError

    @property
    @final
    def address(self) -> SocketAddress:
        return self.__addr


class AbstractNetworkServer(Object, Generic[_RequestT, _ResponseT]):
    __slots__ = ("__t",)

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractNetworkServer[Any, Any]")

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
        def run(self: AbstractNetworkServer[_RequestT, _ResponseT], poll_interval: float, **kwargs: Any) -> None:
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

    @final
    def handle_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        def process_request(client: ConnectedClient[_ResponseT]) -> None:
            return self.process_request(request, client)

        return self.__process_request_hook__(process_request, client, self.handle_error)

    def __process_request_hook__(
        self,
        process_request: Callable[[ConnectedClient[Any]], None],
        client: ConnectedClient[Any],
        error_handler: Callable[[ConnectedClient[Any]], None],
    ) -> None:
        try:
            return process_request(client)
        except Exception:
            error_handler(client)

    @abstractmethod
    def process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        raise NotImplementedError

    def handle_error(self, client: ConnectedClient[Any]) -> None:
        from sys import exc_info, stderr
        from traceback import print_exc

        if exc_info() == (None, None, None):
            return

        print("-" * 40, file=stderr)
        print(f"Exception occurred during processing of request from {client.address}", file=stderr)
        print_exc(file=stderr)
        print("-" * 40, file=stderr)

    @property
    @abstractmethod
    def address(self) -> SocketAddress:
        raise NotImplementedError


NetworkProtocolFactory: TypeAlias = Callable[[], NetworkProtocol[_ResponseT, _RequestT]]

StreamNetworkProtocolFactory: TypeAlias = Callable[[], StreamNetworkProtocol[_ResponseT, _RequestT]]


class AbstractTCPNetworkServer(AbstractNetworkServer[_RequestT, _ResponseT], Generic[_RequestT, _ResponseT]):
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
        "__tcp_no_delay",
        "__buffered_write",
        "__send_flags",
        "__recv_flags",
    )

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT],
        *,
        family: int = AF_INET,
        backlog: int | None = None,
        reuse_port: bool = False,
        dualstack_ipv6: bool = False,
        verify_client_in_thread: bool = False,
        send_flags: int = 0,
        recv_flags: int = 0,
        buffered_write: bool = False,
        disable_nagle_algorithm: bool = False,
    ) -> None:
        if not callable(protocol_cls):
            raise TypeError("Invalid arguments")
        send_flags = int(send_flags)
        recv_flags = int(recv_flags)
        super().__init__()
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
        self.__send_flags: int = send_flags
        self.__recv_flags: int = recv_flags
        self.__tcp_no_delay: bool = bool(disable_nagle_algorithm)
        self.__buffered_write: bool = bool(buffered_write)

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        poll_interval = float(poll_interval)

        with self.__lock:
            self._check_not_closed()
            if self.running():
                raise RuntimeError("Server already running")
            self.__is_shutdown.clear()
            self.__selector = _Selector()
            self.__loop = True

        tcp_no_delay: Final[bool] = self.__tcp_no_delay
        buffered_write: Final[bool] = self.__buffered_write

        handle_request = AbstractNetworkServer.handle_request

        server_socket: Final[Socket] = self.__socket
        select_lock: Final[RLock] = RLock()

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
            try:
                with TCPNetworkClient(socket, protocol=protocol, give=False) as client:
                    accepted = self.verify_new_client(client, address)
            except Exception:
                import traceback

                traceback.print_exc()
                with suppress(Exception):
                    socket.close()
                return
            except BaseException:
                socket.close()
                raise
            if not accepted:
                with suppress(Exception):
                    socket.close()
                return

            def close_client(socket: Socket) -> None:
                shutdown_client(socket, from_client=True)

            def flush_client_data(socket: Socket) -> None:
                with select_lock:
                    return flush_queue(socket)

            def client_is_closed(socket: Socket) -> bool:
                return socket not in self.__clients

            key_data = _SelectorKeyData(
                protocol=protocol,
                socket=socket,
                address=address,
                flush=flush_client_data,
                on_close=close_client,
                is_closed=client_is_closed,
                flush_on_send=not buffered_write,
            )
            key_data.consumer.feed(client._get_buffer())
            del client
            selector_event_mask: int = EVENT_READ
            if buffered_write:
                selector_event_mask |= EVENT_WRITE
            with self.__lock:
                self.__clients[socket] = key_data.client
                selector.register(socket, selector_event_mask, key_data)

        verify_client_in_thread = thread_factory(daemon=True, auto_start=True)(verify_client)

        def new_client() -> None:
            try:
                client_socket, address = server_socket.accept()
                client_socket.settimeout(None)
            except OSError:
                return
            if tcp_no_delay:
                from socket import IPPROTO_TCP, TCP_NODELAY

                try:
                    client_socket.setsockopt(IPPROTO_TCP, TCP_NODELAY, True)
                except BaseException:
                    client_socket.close()
                    raise
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
                    continue
                try:
                    data = socket.recv(key_data.chunk_size, self.__recv_flags)
                except OSError:
                    shutdown_client(socket, from_client=False)
                    self.handle_error(client)
                else:
                    if not data:  # Closed connection (EOF)
                        shutdown_client(socket, from_client=False)
                        continue
                    key_data.consumer.feed(data)

        def process_requests() -> None:
            for key in selector_client_keys():
                key_data: _SelectorKeyData[_RequestT, _ResponseT] = key.data
                client = key_data.client
                if client.closed:
                    continue
                request: _RequestT
                try:
                    request = key_data.consumer.next(on_error="raise")
                except DeserializeError:
                    try:
                        self.bad_request(client)
                    except Exception:
                        self.handle_error(client)
                    continue
                except StopIteration:  # Not enough data
                    continue
                try:
                    handle_request(self, request, client)
                except Exception:
                    self.handle_error(client)

        def send_responses(ready: Sequence[SelectorKey]) -> None:
            data: bytes
            for key in list(ready):
                socket: Socket = key.fileobj  # type: ignore[assignment]
                key_data: _SelectorKeyData[_RequestT, _ResponseT] = key.data
                client = key_data.client

                if client.closed:
                    continue
                with key_data.send_lock:
                    try:
                        data = key_data.pop_data_to_send(read_all=False)
                    except Exception:
                        self.handle_error(client)
                        continue
                    if not data:
                        continue
                    try:
                        nb_bytes_sent = socket.send(data, self.__send_flags)
                    except BlockingIOError as exc:
                        try:
                            character_written: int = exc.characters_written
                        except AttributeError:
                            pass
                        else:
                            if character_written > 0:
                                key_data.unsent_data = data[character_written:]
                    except OSError:
                        shutdown_client(socket, from_client=False)
                        self.handle_error(client)
                    else:
                        if nb_bytes_sent < len(data):
                            key_data.unsent_data = data[nb_bytes_sent:]

        def flush_queue(socket: Socket) -> None:
            key_data: _SelectorKeyData[_RequestT, _ResponseT]
            try:
                key_data = selector.get_key(socket).data
            except KeyError:
                return
            with key_data.send_lock:
                data: bytes = key_data.pop_data_to_send(read_all=True)
                if data:
                    return socket.sendall(data, self.__send_flags)

        def shutdown_client(socket: Socket, *, from_client: bool) -> None:
            self.__clients.pop(socket, None)
            key_data: _SelectorKeyData[_RequestT, _ResponseT]
            if from_client:
                with select_lock:
                    with suppress(Exception):
                        flush_queue(socket)
                    try:
                        key = selector.unregister(socket)
                    except KeyError:
                        return
            else:
                try:
                    key = selector.unregister(socket)
                except KeyError:
                    return
            for key_sequences in ready.values():
                if key in key_sequences:
                    key_sequences.remove(key)
            with suppress(Exception):
                try:
                    if not from_client:
                        socket.shutdown(SHUT_WR)
                finally:
                    socket.close()
            key_data = key.data
            client = key_data.client
            try:
                self.on_disconnect(client)
            except Exception:
                self.handle_error(client)

        def remove_closed_clients() -> None:
            for key in selector_client_keys():
                socket: Socket = key.fileobj  # type: ignore[assignment]
                try:
                    socket.getpeername()
                except OSError:  # Broken connection
                    shutdown_client(socket, from_client=False)

        def destroy_all_clients() -> None:
            for key in selector_client_keys():
                socket: Socket = key.fileobj  # type: ignore[assignment]
                shutdown_client(socket, from_client=False)

        try:
            with self.__selector as selector:
                selector.register(server_socket, EVENT_READ)
                try:
                    while self.__loop:
                        with select_lock:
                            ready = select()
                        if not self.__loop:
                            break  # type: ignore[unreachable]
                        with self.__lock:
                            receive_requests(ready.get(EVENT_READ, ()))
                            process_requests()
                            self.service_actions()
                            send_responses(ready.get(EVENT_WRITE, ()))
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
        self._check_not_closed()
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True

    def bad_request(self, client: ConnectedClient[_ResponseT]) -> None:
        pass

    def on_disconnect(self, client: ConnectedClient[_ResponseT]) -> None:
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

    def protocol(self) -> StreamNetworkProtocol[_ResponseT, _RequestT]:
        return self.__protocol_cls()

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
            raise RuntimeError("Closed server")

    @property
    @final
    def address(self) -> SocketAddress:
        return self.__addr

    @property
    @final
    def send_flags(self) -> int:
        return self.__send_flags

    @property
    @final
    def recv_flags(self) -> int:
        return self.__recv_flags

    @property
    @final
    def clients(self) -> Sequence[ConnectedClient[_ResponseT]]:
        self._check_not_closed()
        with self.__lock:
            return tuple(filter(lambda client: not client.closed, self.__clients.values()))


@dataclass(init=False, slots=True)
class _SelectorKeyData(Generic[_RequestT, _ResponseT]):
    producer: StreamNetworkDataProducer[_ResponseT]
    consumer: StreamNetworkDataConsumer[_RequestT]
    chunk_size: int
    client: ConnectedClient[_ResponseT]
    unsent_data: bytes
    send_lock: RLock

    def __init__(
        self,
        *,
        protocol: StreamNetworkProtocol[_ResponseT, _RequestT],
        socket: Socket,
        address: SocketAddress,
        flush: Callable[[Socket], None],
        on_close: Callable[[Socket], None],
        is_closed: Callable[[Socket], bool],
        flush_on_send: bool,
    ) -> None:
        self.producer = StreamNetworkDataProducer(protocol)
        self.consumer = StreamNetworkDataConsumer(protocol)
        self.chunk_size = guess_best_buffer_size(socket)
        self.client = self.__ConnectedTCPClient(
            producer=self.producer,
            socket=socket,
            address=address,
            flush=flush,
            on_close=on_close,
            is_closed=is_closed,
            flush_on_send=flush_on_send,
        )
        self.unsent_data = b""
        self.send_lock = RLock()

    def pop_data_to_send(self, *, read_all: bool) -> bytes:
        data, self.unsent_data = self.unsent_data, b""
        if read_all:
            data += self.producer.read(-1)
        elif (chunk_size_to_produce := self.chunk_size - len(data)) > 0:
            data += self.producer.read(chunk_size_to_produce)
        elif chunk_size_to_produce < 0:
            data, self.unsent_data = data[: self.chunk_size], data[self.chunk_size :]
        return data

    @final
    class __ConnectedTCPClient(ConnectedClient[_ResponseT]):
        __slots__ = ("__p", "__s", "__flush", "__flush_on_send", "__on_close", "__is_closed")

        def __init__(
            self,
            *,
            producer: StreamNetworkDataProducer[_ResponseT],
            socket: Socket,
            address: SocketAddress,
            flush: Callable[[Socket], None],
            on_close: Callable[[Socket], None],
            is_closed: Callable[[Socket], bool],
            flush_on_send: bool,
        ) -> None:
            super().__init__(address)
            self.__p: StreamNetworkDataProducer[_ResponseT] = producer
            self.__s: Socket | None = socket
            self.__flush: Callable[[Socket], None] = flush
            self.__on_close: Callable[[Socket], None] = on_close
            self.__is_closed: Callable[[Socket], bool] = is_closed
            self.__flush_on_send: bool = flush_on_send

        def close(self) -> None:
            with self.transaction():
                socket = self.__s
                self.__s = None
                if socket is not None and not self.__is_closed(socket):
                    self.__on_close(socket)

        def shutdown(self) -> None:
            with self.transaction():
                socket = self.__s
                self.__s = None
                if socket is not None and not self.__is_closed(socket):
                    try:
                        self.__flush(socket)
                    finally:
                        try:
                            socket.shutdown(SHUT_WR)
                        except OSError:
                            pass
                        finally:
                            self.__on_close(socket)

        def send_packet(self, packet: _ResponseT) -> None:
            with self.transaction():
                socket = self.__check_not_closed()
                self.__p.queue(packet)
                if self.__flush_on_send:
                    self.__flush(socket)

        def send_packets(self, *packets: _ResponseT) -> None:
            with self.transaction():
                socket = self.__check_not_closed()
                self.__p.queue(*packets)
                if self.__flush_on_send:
                    self.__flush(socket)

        def flush(self) -> None:
            with self.transaction():
                socket = self.__check_not_closed()
                return self.__flush(socket)

        def __check_not_closed(self) -> Socket:
            socket = self.__s
            if socket is None or self.__is_closed(socket):
                self.__s = None
                raise RuntimeError("Closed client")
            return socket

        @property
        def closed(self) -> bool:
            return (socket := self.__s) is None or self.__is_closed(socket)


class AbstractUDPNetworkServer(AbstractNetworkServer[_RequestT, _ResponseT], Generic[_RequestT, _ResponseT]):
    __slots__ = (
        "__server",
        "__addr",
        "__lock",
        "__loop",
        "__is_shutdown",
        "__protocol_cls",
    )

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT],
        *,
        family: int = AF_INET,
        reuse_port: bool = False,
        max_packet_size: int = 0,
        send_flags: int = 0,
        recv_flags: int = 0,
    ) -> None:
        protocol = protocol_cls()
        if not isinstance(protocol, NetworkProtocol):
            raise TypeError("Invalid arguments")
        send_flags = int(send_flags)
        recv_flags = int(recv_flags)
        socket = create_server(
            address,
            family=family,
            type=SOCK_DGRAM,
            backlog=None,
            reuse_port=reuse_port,
            dualstack_ipv6=False,
        )
        self.__server: UDPNetworkClient[_ResponseT, _RequestT] = UDPNetworkClient(
            protocol=protocol,
            socket=socket,
            give=True,
            max_packet_size=max_packet_size,
            send_flags=send_flags,
            recv_flags=recv_flags,
        )
        self.__addr: SocketAddress = self.__server.getsockname()
        self.__lock: RLock = RLock()
        self.__loop: bool = False
        self.__is_shutdown: Event = Event()
        self.__is_shutdown.set()
        self.__protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = protocol_cls
        super().__init__()

    @dsuppress(KeyboardInterrupt)
    def serve_forever(self, poll_interval: float = 0.5) -> None:
        from ..client import UDPInvalidPacket

        poll_interval = float(poll_interval)

        with self.__lock:
            self._check_not_closed()
            if self.running():
                raise RuntimeError("Server already running")
            self.__is_shutdown.clear()
            self.__loop = True

        server: UDPNetworkClient[_ResponseT, _RequestT] = self.__server
        make_connected_client = self.__ConnectedUDPClient

        handle_request = AbstractNetworkServer.handle_request

        def parse_requests() -> None:
            bad_request_address: SocketAddress | None = None
            try:
                packets = server.recv_packets(timeout=0, on_error="raise")
            except UDPInvalidPacket as exc:
                bad_request_address = exc.sender
                packets = exc.already_deserialized_packets
            process_requests(packets)
            if bad_request_address is not None:
                connected_client = make_connected_client(server, bad_request_address)
                try:
                    self.bad_request(connected_client)
                except Exception:
                    self.handle_error(connected_client)
                finally:
                    connected_client.close()

        def process_requests(packets: list[tuple[_RequestT, SocketAddress]]) -> None:
            for request, address in packets:
                connected_client = make_connected_client(server, address)
                try:
                    handle_request(self, request, connected_client)
                except Exception:
                    self.handle_error(connected_client)
                finally:
                    connected_client.close()

        with _Selector() as selector:
            selector.register(server, EVENT_READ)
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

    def running(self) -> bool:
        with self.__lock:
            return not self.__is_shutdown.is_set()

    def shutdown(self) -> None:
        with self.__lock:
            self.__loop = False
        self.__is_shutdown.wait()

    def send_packet(self, address: SocketAddress, packet: _ResponseT) -> None:
        self._check_not_closed()
        self.__server.send_packet(address, packet)

    def send_packets(self, address: SocketAddress, *packets: _ResponseT) -> None:
        self._check_not_closed()
        self.__server.send_packet(address, *packets)

    def bad_request(self, client: ConnectedClient[_ResponseT]) -> None:
        pass

    def protocol(self) -> NetworkProtocol[_ResponseT, _RequestT]:
        return self.__protocol_cls()

    @overload
    def getsockopt(self, __level: int, __optname: int, /) -> int:
        ...

    @overload
    def getsockopt(self, __level: int, __optname: int, __buflen: int, /) -> bytes:
        ...

    def getsockopt(self, *args: int) -> int | bytes:
        self._check_not_closed()
        return self.__server.getsockopt(*args)

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: int | bytes, /) -> None:
        ...

    @overload
    def setsockopt(self, __level: int, __optname: int, __value: None, __optlen: int, /) -> None:
        ...

    def setsockopt(self, *args: Any) -> None:
        self._check_not_closed()
        return self.__server.setsockopt(*args)

    @final
    def _check_not_closed(self) -> None:
        if self.__server.closed:
            raise RuntimeError("Closed server")

    @property
    @final
    def address(self) -> SocketAddress:
        return self.__addr

    @property
    @final
    def send_flags(self) -> int:
        return self.__server.default_send_flags

    @property
    @final
    def recv_flags(self) -> int:
        return self.__server.default_recv_flags

    @final
    class __ConnectedUDPClient(ConnectedClient[_ResponseT]):
        __slots__ = ("__s",)

        def __init__(
            self,
            server: UDPNetworkClient[_ResponseT, Any] | None,
            address: SocketAddress,
        ) -> None:
            super().__init__(address)
            self.__s: UDPNetworkClient[_ResponseT, Any] | None = server

        def close(self) -> None:
            with self.transaction():
                self.__s = None

        def send_packet(self, packet: _ResponseT) -> None:
            with self.transaction():
                server: UDPNetworkClient[_ResponseT, Any] | None = self.__s
                if server is None:
                    raise RuntimeError("Closed client")
                server.send_packet(self.address, packet)

        def send_packets(self, *packets: _ResponseT) -> None:
            if not packets:
                return
            with self.transaction():
                server: UDPNetworkClient[_ResponseT, Any] | None = self.__s
                if server is None:
                    raise RuntimeError("Closed client")
                server.send_packets(self.address, *packets)

        def flush(self) -> None:
            if self.closed:
                raise RuntimeError("Closed client")

        @property
        def closed(self) -> bool:
            return self.__s is None
