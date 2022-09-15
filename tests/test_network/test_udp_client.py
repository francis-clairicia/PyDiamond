# -*- coding: Utf-8 -*-

from __future__ import annotations

from selectors import EVENT_READ, DefaultSelector
from threading import Event
from typing import Any

from pydiamond.network.client import UDPNetworkClient
from pydiamond.network.protocol import PickleNetworkProtocol, SafePickleNetworkProtocol
from pydiamond.network.socket import IPv4SocketAddress, PythonUDPClientSocket, PythonUDPServerSocket
from pydiamond.system.threading import Thread, thread_factory

from cryptography.fernet import Fernet

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
        with UDPNetworkClient[Any, Any]() as client:
            client.send_packet(address, {"data": [5, 2]})
            assert client.recv_packet()[0] == {"data": [5, 2]}
            client.send_packet(address, "Hello")
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
            client: UDPNetworkClient[Any, Any] = UDPNetworkClient(socket)
            client.send_packet(address, {"data": [5, 2]})
            assert client.recv_packet()[0] == {"data": [5, 2]}
            client.send_packet(address, "Hello")
            assert client.recv_packet()[0] == "Hello"
    finally:
        shutdow_requested.set()
        server_thread.join()


def test_custom_protocol() -> None:
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
        with UDPNetworkClient[Any, Any](protocol=SafePickleNetworkProtocol(Fernet.generate_key())) as client:
            client.send_packet(address, {"data": [5, 2]})
            assert client.recv_packet()[0] == {"data": [5, 2]}
            client.send_packet(address, "Hello")
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
        with UDPNetworkClient[Any, Any](protocol=PickleNetworkProtocol()) as client:
            client.send_packet(address, {"data": [5, 2]})
            client.send_packet(address, "Hello")
            client.send_packet(address, 132)
            assert client.recv_packet()[0] == {"data": [5, 2]}
            assert client.recv_packet()[0] == "Hello"
            assert client.recv_packet()[0] == 132
    finally:
        shutdow_requested.set()
        server_thread.join()
