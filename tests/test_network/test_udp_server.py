# -*- coding: Utf-8 -*-

from __future__ import annotations

from time import sleep
from typing import Any, ClassVar, Generator

from py_diamond.network.client import UDPNetworkClient
from py_diamond.network.protocol import AbstractNetworkProtocol, ValidationError
from py_diamond.network.server import AbstractUDPRequestHandler, UDPNetworkServer
from py_diamond.network.socket import IPv4SocketAddress
from py_diamond.system.threading import Thread

from .random_port import random_port


class _MirrorRequestHandler(AbstractUDPRequestHandler[Any]):
    def handle(self) -> None:
        self.client.send_packet(self.request)


def test_serve_forever_default() -> None:
    address: tuple[str, int] = ("localhost", random_port())

    with UDPNetworkServer(address, _MirrorRequestHandler) as server:
        assert not server.running()
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forever_context_shut_down() -> None:
    address: tuple[str, int] = ("localhost", random_port())

    with UDPNetworkServer(address, _MirrorRequestHandler) as server:
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
    t.join()
    assert not server.running()


def test_serve_forever_in_thread_default() -> None:
    address: tuple[str, int] = ("localhost", random_port())

    with UDPNetworkServer(address, _MirrorRequestHandler) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forver_in_thread_context_shut_down() -> None:
    address: tuple[str, int] = ("localhost", random_port())

    with UDPNetworkServer(address, _MirrorRequestHandler) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
    assert not server.running()
    assert not t.is_alive()


class _TestServiceActionServer(UDPNetworkServer[Any]):
    def service_actions(self) -> None:
        super().service_actions()
        self.service_actions_called: bool = True


def test_service_actions() -> None:
    address: tuple[str, int] = ("localhost", random_port())

    with _TestServiceActionServer(address, _MirrorRequestHandler) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.3)
    assert getattr(server, "service_actions_called", False)


class _IntegerNetworkProtocol(AbstractNetworkProtocol):
    BYTES_LENGTH: ClassVar[int] = 8

    def serialize(self, packet: int) -> bytes:
        if not isinstance(packet, int):
            raise ValidationError
        return packet.to_bytes(self.BYTES_LENGTH, byteorder="big", signed=True)

    def deserialize(self, data: bytes) -> int:
        return int.from_bytes(data, byteorder="big", signed=True)

    def parse_received_data(self, buffer: bytes) -> Generator[bytes, None, bytes]:
        bytes_length: int = self.BYTES_LENGTH
        while len(buffer) >= bytes_length:
            yield buffer[:bytes_length]
            buffer = buffer[bytes_length:]
        return buffer

    def verify_received_data(self, data: bytes) -> None:
        if len(data) != self.BYTES_LENGTH:
            raise ValidationError


def test_request_handling() -> None:
    address: IPv4SocketAddress = IPv4SocketAddress("localhost", random_port())

    with UDPNetworkServer(address, _MirrorRequestHandler, protocol_cls=_IntegerNetworkProtocol) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        with (
            UDPNetworkClient[int](protocol=server.protocol_cls()) as client_1,
            UDPNetworkClient[int](protocol=server.protocol_cls()) as client_2,
            UDPNetworkClient[int](protocol=server.protocol_cls()) as client_3,
        ):
            client_1.send_packet(350, address)
            client_2.send_packet(-634, address)
            client_3.send_packet(0, address)
            sleep(0.2)
            assert client_1.recv_packet()[0] == 350
            assert client_2.recv_packet()[0] == -634
            assert client_3.recv_packet()[0] == 0
