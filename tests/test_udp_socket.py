# -*- coding: Utf-8 -*

from socket import has_ipv6 as HAS_IPV6

from py_diamond.network.socket import (
    AF_INET,
    AF_INET6,
    SOCK_DGRAM,
    IPv4SocketAddress,
    IPv6SocketAddress,
    PythonUDPClientSocket,
    PythonUDPServerSocket,
    SocketAddress,
)

from .random_port import random_port


def test_ipv4_client_server_connection() -> None:
    host: str = "localhost"
    port: int = random_port()

    with (
        PythonUDPServerSocket.bind((host, port), family=AF_INET) as server,
        PythonUDPClientSocket.create(family=AF_INET) as client,
    ):
        assert server.is_open()
        assert client.is_open()
        assert server.type == client.type == SOCK_DGRAM
        assert server.family == client.family == AF_INET
        server_addr: SocketAddress = server.getsockname()
        client_addr: SocketAddress = client.getsockname()
        assert isinstance(server_addr, IPv4SocketAddress)
        assert isinstance(client_addr, IPv4SocketAddress)

        message: bytes = b"Hello, world"

        assert client.sendto(message, IPv4SocketAddress(host, port)) == len(message)
        datagram = server.recvfrom(1024)
        assert datagram.body == message
        assert isinstance(datagram.sender, IPv4SocketAddress)
        assert datagram.sender.port == client_addr.port
        assert server.sendto(datagram.body, datagram.sender) == len(datagram.body)
        data, sender = client.recvfrom(1024)
        assert data == message
        assert isinstance(sender, IPv4SocketAddress)
        assert sender == server_addr
    assert not server.is_open()
    assert not client.is_open()


if HAS_IPV6:

    def test_ipv6_client_server_connection() -> None:
        host: str = "localhost"
        port: int = random_port()

        with (
            PythonUDPServerSocket.bind((host, port), family=AF_INET6) as server,
            PythonUDPClientSocket.create(family=AF_INET6) as client,
        ):
            assert server.is_open()
            assert client.is_open()
            assert server.type == client.type == SOCK_DGRAM
            assert server.family == client.family == AF_INET6
            server_addr: SocketAddress = server.getsockname()
            client_addr: SocketAddress = client.getsockname()
            assert isinstance(server_addr, IPv6SocketAddress)
            assert isinstance(client_addr, IPv6SocketAddress)

            message: bytes = b"Hello, world"

            assert client.sendto(message, IPv4SocketAddress(host, port)) == len(message)
            datagram = server.recvfrom(1024)
            assert datagram.body == message
            assert isinstance(datagram.sender, IPv6SocketAddress)
            assert datagram.sender.port == client_addr.port
            assert server.sendto(datagram.body, datagram.sender) == len(datagram.body)
            data, sender = client.recvfrom(1024)
            assert data == message
            assert isinstance(sender, IPv6SocketAddress)
            assert sender == server_addr
        assert not server.is_open()
        assert not client.is_open()