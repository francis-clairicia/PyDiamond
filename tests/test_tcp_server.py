# -*- coding: Utf-8 -*

from random import randrange
from time import sleep
from typing import Any, ClassVar, Generator

from py_diamond.network.client import TCPNetworkClient
from py_diamond.network.protocol import AbstractNetworkProtocol, ValidationError
from py_diamond.network.server import AbstractTCPRequestHandler, TCPNetworkServer
from py_diamond.network.socket import SocketAddress
from py_diamond.system.threading import Thread


class _BroadcastRequestHandler(AbstractTCPRequestHandler[Any]):
    def handle(self) -> None:
        request: Any = self.request
        for client in filter(lambda client: client is not self.client, self.server.clients):
            client.send_packet(request)


def test_serve_forever_default() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with TCPNetworkServer(address, _BroadcastRequestHandler) as server:
        assert not server.running()
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forever_context_shut_down() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with TCPNetworkServer(address, _BroadcastRequestHandler) as server:
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
    t.join()
    assert not server.running()


def test_serve_forever_in_thread_default() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with TCPNetworkServer(address, _BroadcastRequestHandler) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forver_in_thread_context_shut_down() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with TCPNetworkServer(address, _BroadcastRequestHandler) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
    assert not server.running()
    assert not t.is_alive()


class _TestServiceActionServer(TCPNetworkServer[Any]):
    def service_actions(self) -> None:
        super().service_actions()
        self.service_actions_called: bool = True


def test_service_actions() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with _TestServiceActionServer(address, _BroadcastRequestHandler) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.3)
    assert getattr(server, "service_actions_called", False)


def test_client_connection() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with TCPNetworkServer(address, _BroadcastRequestHandler, backlog=1) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.1)
        assert len(server.clients) == 0
        with TCPNetworkClient[Any](address):
            sleep(0.3)
            assert len(server.clients) == 1
        sleep(0.3)
        assert len(server.clients) == 0


class _TestWelcomeServer(TCPNetworkServer[Any]):
    def _verify_new_client(self, client: TCPNetworkClient[Any], address: SocketAddress) -> bool:
        client.send_packet("Welcome !")
        return True


def test_welcome_connection() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with _TestWelcomeServer(address, _BroadcastRequestHandler, backlog=1) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        with TCPNetworkClient[Any](address) as client:
            assert client.recv_packet() == "Welcome !"


def test_multiple_connections() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with _TestWelcomeServer(address, _BroadcastRequestHandler) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        with (
            TCPNetworkClient[Any](address) as client_1,
            TCPNetworkClient[Any](address) as client_2,
            TCPNetworkClient[Any](address) as client_3,
        ):
            assert client_1.recv_packet() == "Welcome !"
            assert client_2.recv_packet() == "Welcome !"
            assert client_3.recv_packet() == "Welcome !"
            assert len(server.clients) == 3


class _IntegerNetworkProtocol(AbstractNetworkProtocol):
    BYTES_LENGTH: ClassVar[int] = 8

    @classmethod
    def verify_packet_to_send(cls, packet: Any) -> None:
        super().verify_packet_to_send(packet)
        if not isinstance(packet, int):
            raise ValidationError

    @classmethod
    def serialize(cls, packet: int) -> bytes:
        return packet.to_bytes(cls.BYTES_LENGTH, byteorder="big", signed=True)

    @classmethod
    def deserialize(cls, data: bytes) -> int:
        return int.from_bytes(data, byteorder="big", signed=True)

    @classmethod
    def parse_received_data(cls, buffer: bytes) -> Generator[bytes, None, bytes]:
        bytes_length: int = cls.BYTES_LENGTH
        while len(buffer) >= bytes_length:
            yield buffer[:bytes_length]
            buffer = buffer[bytes_length:]
        return buffer

    @classmethod
    def verify_received_data(cls, data: bytes) -> None:
        if len(data) != cls.BYTES_LENGTH:
            raise ValidationError


def test_request_handling() -> None:
    address: tuple[str, int] = ("localhost", randrange(10000, 65536))

    with TCPNetworkServer(address, _BroadcastRequestHandler, protocol_cls=_IntegerNetworkProtocol) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        with (
            TCPNetworkClient[int](address, protocol_cls=_IntegerNetworkProtocol) as client_1,
            TCPNetworkClient[int](address, protocol_cls=_IntegerNetworkProtocol) as client_2,
            TCPNetworkClient[int](address, protocol_cls=_IntegerNetworkProtocol) as client_3,
        ):
            client_1.send_packet(350)
            sleep(0.2)
            assert client_2.recv_packet() == 350
            assert client_3.recv_packet() == 350
            assert client_1.recv_packet_no_wait() is None
            client_2.send_packet(-634)
            sleep(0.2)
            assert client_1.recv_packet() == -634
            assert client_3.recv_packet() == -634
            assert client_2.recv_packet_no_wait() is None
            client_3.send_packet(0)
            sleep(0.2)
            assert client_1.recv_packet() == 0
            assert client_2.recv_packet() == 0
            assert client_3.recv_packet_no_wait() is None
            client_1.send_packet(350)
            client_2.send_packet(-634)
            client_3.send_packet(0)
            sleep(0.5)
            assert list(client_1.recv_packets()) == [-634, 0]
            assert list(client_2.recv_packets()) == [350, 0]
            assert list(client_3.recv_packets()) == [350, -634]
