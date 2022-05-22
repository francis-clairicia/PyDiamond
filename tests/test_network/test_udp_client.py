# -*- coding: Utf-8 -*

from selectors import EVENT_READ, DefaultSelector
from threading import Event
from typing import Any

from py_diamond.network.client import UDPNetworkClient
from py_diamond.network.protocol import PicklingNetworkProtocol, SecuredNetworkProtocol
from py_diamond.network.socket import IPv4SocketAddress, PythonUDPClientSocket, PythonUDPServerSocket
from py_diamond.system.threading import Thread, thread_factory

from .random_port import random_port


@thread_factory
def launch_server(host: str, port: int, server_started: Event, shutdown_requested: Event) -> None:
    with PythonUDPServerSocket.bind((host, port)) as server, DefaultSelector() as selector:
        selector.register(server, EVENT_READ)
        server_started.set()
        while not shutdown_requested.is_set():
            if selector.select(0.1):
                data, addr = server.recvfrom()
                server.sendto(data, addr)


def test_default() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    address: IPv4SocketAddress = IPv4SocketAddress(host, port)
    try:
        server_started.wait()
        with UDPNetworkClient[Any]() as client:
            client.send_packet({"data": [5, 2]}, address)
            assert client.recv_packet()[0] == {"data": [5, 2]}
            client.send_packet("Hello", address)
            assert client.recv_packet()[0] == "Hello"
            assert len(list(client.recv_packets(block=False))) == 0
            assert client.recv_packet_no_wait() is None
    finally:
        shutdow_requested.set()
        server_thread.join()


def test_custom_socket() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    address: IPv4SocketAddress = IPv4SocketAddress(host, port)
    try:
        server_started.wait()
        with PythonUDPClientSocket.create() as socket:
            client: UDPNetworkClient[Any] = UDPNetworkClient(socket)
            client.send_packet({"data": [5, 2]}, address)
            assert client.recv_packet()[0] == {"data": [5, 2]}
            client.send_packet("Hello", address)
            assert client.recv_packet()[0] == "Hello"
    finally:
        shutdow_requested.set()
        server_thread.join()


def test_custom_protocol() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    class SafePicklingProtocol(SecuredNetworkProtocol):
        SECRET_KEY = SecuredNetworkProtocol.generate_key()

        def get_unsafe_protocol(self) -> PicklingNetworkProtocol:
            return PicklingNetworkProtocol()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    address: IPv4SocketAddress = IPv4SocketAddress(host, port)
    try:
        server_started.wait()
        with UDPNetworkClient[Any](protocol=SafePicklingProtocol()) as client:
            client.send_packet({"data": [5, 2]}, address)
            assert client.recv_packet()[0] == {"data": [5, 2]}
            client.send_packet("Hello", address)
            assert client.recv_packet()[0] == "Hello"
    finally:
        shutdow_requested.set()
        server_thread.join()


def test_several_successive_send() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    address: IPv4SocketAddress = IPv4SocketAddress(host, port)
    try:
        server_started.wait()
        with UDPNetworkClient[Any](protocol=PicklingNetworkProtocol()) as client:
            client.send_packet({"data": [5, 2]}, address)
            client.send_packet("Hello", address)
            client.send_packet(132, address)
            assert client.recv_packet()[0] == {"data": [5, 2]}
            assert client.recv_packet()[0] == "Hello"
            assert client.recv_packet()[0] == 132
    finally:
        shutdow_requested.set()
        server_thread.join()
