# -*- coding: Utf-8 -*-

from __future__ import annotations

from functools import partial
from socket import AF_INET, SOCK_STREAM, socket as Socket
from typing import Any, Generator

from pydiamond.network.client import TCPNetworkClient
from pydiamond.network.protocol import (
    JSONNetworkProtocol,
    PickleNetworkProtocol,
    SafePickleNetworkProtocol,
    StreamNetworkProtocol,
    ValidationError,
)

import pytest
from cryptography.fernet import Fernet


def test_default(tcp_server: tuple[str, int]) -> None:
    with TCPNetworkClient[Any, Any](tcp_server) as client:
        client.send_packet({"data": [5, 2]})
        assert client.recv_packet() == {"data": [5, 2]}
        client.send_packet("Hello")
        assert client.recv_packet() == "Hello"
        assert len(client.recv_packets(timeout=0)) == 0
        assert client.recv_packet_no_block() is None


def test_custom_socket(tcp_server: tuple[str, int]) -> None:
    with Socket(AF_INET, SOCK_STREAM) as s:
        s.connect(tcp_server)
        client: TCPNetworkClient[Any, Any] = TCPNetworkClient(s)
        client.send_packet({"data": [5, 2]})
        assert client.recv_packet() == {"data": [5, 2]}
        client.send_packet("Hello")
        assert client.recv_packet() == "Hello"


def test_custom_protocol(tcp_server: tuple[str, int]) -> None:
    with TCPNetworkClient[Any, Any](tcp_server, protocol=SafePickleNetworkProtocol(Fernet.generate_key())) as client:
        client.send_packet({"data": [5, 2]})
        assert client.recv_packet() == {"data": [5, 2]}
        client.send_packet("Hello")
        assert client.recv_packet() == "Hello"


class StringNetworkProtocol(StreamNetworkProtocol[str, str]):
    def incremental_serialize(self, packet: str) -> Generator[bytes, None, None]:
        if not isinstance(packet, str):
            raise ValidationError("Invalid string")
        yield from map(partial(str.encode, encoding="ascii"), packet.splitlines(True))

    def incremental_deserialize(self) -> Generator[None, bytes, tuple[str, bytes]]:
        data: str = str()
        while True:
            data += (yield).decode("ascii")
            if "\n" in data:
                packet, _, data = data.partition("\n")
                return packet, data.encode("ascii")


def test_multiple_requests(tcp_server: tuple[str, int]) -> None:
    with TCPNetworkClient(tcp_server, protocol=StringNetworkProtocol()) as client:
        client.send_packet("A\nB\nC\nD\n")
        assert client.recv_packets() == ["A", "B", "C", "D"]
        client.send_packet("E\nF\nG\nH\nI")
        assert client.recv_packet() == "E"
        assert client.recv_packet() == "F"
        assert client.recv_packets() == ["G", "H"]
        client.send_packet("J\n")
        assert client.recv_packet() == "IJ"

        with pytest.raises(ValidationError):
            client.send_packet(5)  # type: ignore[arg-type]


def test_several_successive_send_using_pickling_protocol(tcp_server: tuple[str, int]) -> None:
    with TCPNetworkClient[Any, Any](tcp_server, protocol=PickleNetworkProtocol()) as client:
        client.send_packet({"data": [5, 2]})
        client.send_packet("Hello")
        client.send_packet(132)
        assert client.recv_packet() == {"data": [5, 2]}
        assert client.recv_packet() == "Hello"
        assert client.recv_packet() == 132


def test_several_successive_send_using_json_protocol(tcp_server: tuple[str, int]) -> None:
    with TCPNetworkClient[Any, Any](tcp_server, protocol=JSONNetworkProtocol()) as client:
        client.send_packet({"data": [5, 2]})
        client.send_packet("Hello")
        client.send_packet([132])
        assert client.recv_packet() == {"data": [5, 2]}
        assert client.recv_packet() == "Hello"
        assert client.recv_packet() == [132]


def test_several_successive_send_using_secured_pickling_protocol(tcp_server: tuple[str, int]) -> None:
    with TCPNetworkClient[Any, Any](tcp_server, protocol=SafePickleNetworkProtocol(Fernet.generate_key())) as client:
        client.send_packet({"data": [5, 2]})
        client.send_packet("Hello")
        client.send_packet(132)
        assert client.recv_packet() == {"data": [5, 2]}
        assert client.recv_packet() == "Hello"
        assert client.recv_packet() == 132
