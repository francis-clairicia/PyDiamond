# -*- coding: Utf-8 -*-

from __future__ import annotations

from socket import AF_INET, SOCK_DGRAM, socket as Socket
from typing import Any

from pydiamond.network.client import UDPNetworkClient
from pydiamond.network.protocol import PickleNetworkProtocol, SafePickleNetworkProtocol

from cryptography.fernet import Fernet


def test_default(udp_server: tuple[str, int]) -> None:
    with UDPNetworkClient[Any, Any]() as client:
        client.send_packet(udp_server, {"data": [5, 2]})
        assert client.recv_packet()[0] == {"data": [5, 2]}
        client.send_packet(udp_server, "Hello")
        assert client.recv_packet()[0] == "Hello"
        assert len(client.recv_packets(timeout=0)) == 0
        assert client.recv_packet_no_block() is None


def test_custom_socket(udp_server: tuple[str, int]) -> None:
    with Socket(AF_INET, SOCK_DGRAM) as socket:
        socket.bind(("", 0))
        client: UDPNetworkClient[Any, Any] = UDPNetworkClient(socket)
        client.send_packet(udp_server, {"data": [5, 2]})
        assert client.recv_packet()[0] == {"data": [5, 2]}
        client.send_packet(udp_server, "Hello")
        assert client.recv_packet()[0] == "Hello"


def test_custom_protocol(udp_server: tuple[str, int]) -> None:
    with UDPNetworkClient[Any, Any](protocol=SafePickleNetworkProtocol(Fernet.generate_key())) as client:
        client.send_packet(udp_server, {"data": [5, 2]})
        assert client.recv_packet()[0] == {"data": [5, 2]}
        client.send_packet(udp_server, "Hello")
        assert client.recv_packet()[0] == "Hello"


def test_several_successive_send(udp_server: tuple[str, int]) -> None:
    with UDPNetworkClient[Any, Any](protocol=PickleNetworkProtocol()) as client:
        client.send_packet(udp_server, {"data": [5, 2]})
        client.send_packet(udp_server, "Hello")
        client.send_packet(udp_server, 132)
        assert client.recv_packet()[0] == {"data": [5, 2]}
        assert client.recv_packet()[0] == "Hello"
        assert client.recv_packet()[0] == 132
