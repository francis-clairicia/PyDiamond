# -*- coding: Utf-8 -*-

from __future__ import annotations

from time import sleep
from typing import Any, ClassVar, Generator

from pydiamond.network.client import TCPNetworkClient
from pydiamond.network.protocol import PickleNetworkProtocol, StreamNetworkProtocol
from pydiamond.network.server.abc import AbstractTCPNetworkServer, ConnectedClient
from pydiamond.network.server.concurrency import AbstractForkingTCPNetworkServer, AbstractThreadingTCPNetworkServer
from pydiamond.network.socket import SocketAddress
from pydiamond.system.threading import Thread
from pydiamond.system.utils.os import has_fork

import pytest


class _TestServer(AbstractTCPNetworkServer[Any, Any]):
    def process_request(self, request: Any, client: ConnectedClient[Any]) -> None:
        for c in filter(lambda c: c is not client, self.clients):
            c.send_packet(request)


_RANDOM_HOST_PORT = ("localhost", 0)


def test_serve_forever_default() -> None:
    with _TestServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        assert not server.running()
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forever_context_shut_down() -> None:
    with _TestServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
    t.join()
    assert not server.running()


def test_serve_forever_in_thread_default() -> None:
    with _TestServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forver_in_thread_context_shut_down() -> None:
    with _TestServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
    assert not server.running()
    assert not t.is_alive()


class _TestServiceActionServer(_TestServer):
    def service_actions(self) -> None:
        super().service_actions()
        self.service_actions_called: bool = True


def test_service_actions() -> None:
    with _TestServiceActionServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.3)
    assert getattr(server, "service_actions_called", False)


def test_client_connection() -> None:
    with _TestServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        address = server.address.for_connection()
        server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.1)
        assert len(server.clients) == 0
        with TCPNetworkClient[Any, Any](address, server.protocol()):
            sleep(0.3)
            assert len(server.clients) == 1
        sleep(0.3)
        assert len(server.clients) == 0


class _TestWelcomeServer(_TestServer):
    def verify_new_client(self, client: TCPNetworkClient[Any, Any], address: SocketAddress) -> bool:
        client.send_packet("Welcome !")
        return True


def test_welcome_connection() -> None:
    with _TestWelcomeServer(_RANDOM_HOST_PORT, PickleNetworkProtocol, backlog=1) as server:
        address = server.address.for_connection()
        server.serve_forever_in_thread(poll_interval=0.1)
        with TCPNetworkClient[Any, Any](address, server.protocol()) as client:
            assert client.recv_packet() == "Welcome !"


def test_multiple_connections() -> None:
    with _TestWelcomeServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        address = server.address.for_connection()
        server.serve_forever_in_thread(poll_interval=0)
        with (
            TCPNetworkClient[Any, Any](address, server.protocol()) as client_1,
            TCPNetworkClient[Any, Any](address, server.protocol()) as client_2,
            TCPNetworkClient[Any, Any](address, server.protocol()) as client_3,
        ):
            assert client_1.recv_packet() == "Welcome !"
            assert client_2.recv_packet() == "Welcome !"
            assert client_3.recv_packet() == "Welcome !"
            sleep(0.2)
            assert len(server.clients) == 3


class _IntegerNetworkProtocol(StreamNetworkProtocol[int, int]):
    BYTES_LENGTH: ClassVar[int] = 8

    def incremental_serialize(self, packet: int) -> Generator[bytes, None, None]:
        yield packet.to_bytes(self.BYTES_LENGTH, byteorder="big", signed=True)

    def incremental_deserialize(self) -> Generator[None, bytes, tuple[Any, bytes]]:
        data: bytes = b""
        while True:
            data += yield
            if len(data) >= self.BYTES_LENGTH:
                packet = int.from_bytes(data[: self.BYTES_LENGTH], byteorder="big", signed=True)
                return packet, data[self.BYTES_LENGTH :]


def test_request_handling() -> None:
    with _TestServer(_RANDOM_HOST_PORT, protocol_cls=_IntegerNetworkProtocol) as server:
        address = server.address.for_connection()
        server.serve_forever_in_thread(poll_interval=0)
        with (
            TCPNetworkClient(address, protocol=_IntegerNetworkProtocol()) as client_1,
            TCPNetworkClient(address, protocol=_IntegerNetworkProtocol()) as client_2,
            TCPNetworkClient(address, protocol=_IntegerNetworkProtocol()) as client_3,
        ):
            while len(server.clients) < 3:
                sleep(0.1)
            client_1.send_packet(350)
            sleep(0.3)
            assert client_2.recv_packet() == 350
            assert client_3.recv_packet() == 350
            with pytest.raises(TimeoutError):
                client_1.recv_packet_no_block()
            client_2.send_packet(-634)
            sleep(0.3)
            assert client_1.recv_packet() == -634
            assert client_3.recv_packet() == -634
            with pytest.raises(TimeoutError):
                client_2.recv_packet_no_block()
            client_3.send_packet(0)
            sleep(0.3)
            assert client_1.recv_packet() == 0
            assert client_2.recv_packet() == 0
            with pytest.raises(TimeoutError):
                client_3.recv_packet_no_block()
            client_1.send_packet(350)
            sleep(0.1)
            client_2.send_packet(-634)
            sleep(0.1)
            client_3.send_packet(0)
            sleep(0.3)
            assert client_1.recv_packets() == [-634, 0]
            assert client_2.recv_packets() == [350, 0]
            assert client_3.recv_packets() == [350, -634]


def test_disable_nagle_algorithm() -> None:
    with _TestServer(_RANDOM_HOST_PORT, PickleNetworkProtocol, buffered_write=True, disable_nagle_algorithm=True) as server:
        server.serve_forever_in_thread(poll_interval=0)
        with (
            TCPNetworkClient(server.address.for_connection(), protocol=server.protocol()) as client_1,
            TCPNetworkClient(server.address.for_connection(), protocol=server.protocol()) as client_2,
        ):
            packet = {"data": 1}
            client_1.send_packet(packet)
            assert client_2.recv_packet() == packet


class _TestThreadingServer(AbstractThreadingTCPNetworkServer[Any, Any]):
    def process_request(self, request: Any, client: ConnectedClient[Any]) -> None:
        import threading

        client.send_packet((request, threading.current_thread() is not threading.main_thread()))


def test_threading_server() -> None:
    with _TestThreadingServer(_RANDOM_HOST_PORT, PickleNetworkProtocol) as server:
        server.serve_forever_in_thread(poll_interval=0)
        with TCPNetworkClient[Any, Any](server.address.for_connection(), server.protocol()) as client:
            packet = {"data": 1}
            client.send_packet(packet)
            response: tuple[Any, bool] = client.recv_packet()
            assert response[0] == packet
            assert response[1] is True


class _TestForkingServer(AbstractForkingTCPNetworkServer[Any, Any]):
    def process_request(self, request: Any, client: ConnectedClient[Any]) -> None:
        from os import getpid

        client.send_packet((request, getpid()))


@pytest.mark.skipif(not has_fork(), reason="fork() not supported on this platform")
@pytest.mark.parametrize(
    "buffered_write", [pytest.param(False, id="buffered_write==False"), pytest.param(True, id="buffered_write==True")]
)
def test_forking_server(buffered_write: bool) -> None:
    from os import getpid

    with _TestForkingServer(_RANDOM_HOST_PORT, PickleNetworkProtocol, buffered_write=buffered_write) as server:
        server.serve_forever_in_thread(poll_interval=0)
        with TCPNetworkClient[Any, Any](server.address.for_connection(), server.protocol()) as client:
            packet = {"data": 1}
            client.send_packet(packet)
            response: tuple[Any, int] = client.recv_packet()
            assert response[0] == packet
            assert response[1] != getpid()
            sleep(0.1)
            with pytest.raises(EOFError):
                _ = client.recv_packet()
