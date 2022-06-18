# -*- coding: Utf-8 -*-

from __future__ import annotations

from functools import partial
from selectors import EVENT_READ, DefaultSelector
from threading import Event
from typing import Any, Generator

from py_diamond.network.client import TCPNetworkClient
from py_diamond.network.protocol import (
    AbstractStreamNetworkProtocol,
    EncryptorProtocol,
    JSONNetworkProtocol,
    PicklingNetworkProtocol,
    SafePicklingNetworkProtocol,
    ValidationError,
)
from py_diamond.network.socket import PythonTCPClientSocket, PythonTCPServerSocket
from py_diamond.system.threading import Thread, thread_factory

import pytest

from .random_port import random_port

generate_key = EncryptorProtocol.generate_key


@thread_factory
def launch_server(host: str, port: int, server_started_event: Event, shutdow_requested: Event) -> None:
    with PythonTCPServerSocket.bind((host, port), backlog=1) as s, DefaultSelector() as selector:
        server_started_event.set()
        with s.accept()[0] as conn:
            selector.register(conn, EVENT_READ)
            while not shutdow_requested.is_set():
                if selector.select(0.1):
                    if not (data := conn.recv(1024)):
                        break
                    conn.send(data)


def test_default() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    try:
        server_started.wait()
        with TCPNetworkClient[Any]((host, port)) as client:
            client.send_packet({"data": [5, 2]})
            assert client.recv_packet() == {"data": [5, 2]}
            client.send_packet("Hello")
            assert client.recv_packet() == "Hello"
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
    try:
        server_started.wait()
        with PythonTCPClientSocket.connect((host, port)) as s:
            client: TCPNetworkClient[Any] = TCPNetworkClient(s)
            client.send_packet({"data": [5, 2]})
            assert client.recv_packet() == {"data": [5, 2]}
            client.send_packet("Hello")
            assert client.recv_packet() == "Hello"
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
    server_started.wait()
    try:
        with TCPNetworkClient[Any]((host, port), protocol=SafePicklingNetworkProtocol(generate_key())) as client:
            client.send_packet({"data": [5, 2]})
            assert client.recv_packet() == {"data": [5, 2]}
            client.send_packet("Hello")
            assert client.recv_packet() == "Hello"
    finally:
        shutdow_requested.set()
        server_thread.join()


class StringNetworkProtocol(AbstractStreamNetworkProtocol):
    def incremental_serialize(self, packet: str) -> Generator[bytes, None, None]:
        if not isinstance(packet, str):
            raise ValidationError("Invalid string")
        yield from map(partial(str.encode, encoding="ascii"), packet.splitlines(True))

    def incremental_deserialize(self, initial_bytes: bytes) -> Generator[Any, bytes | None, None]:
        data: str = initial_bytes.decode("ascii")
        del initial_bytes
        while True:
            packet: Any
            new_chunk: bytes | None
            if "\n" in data:
                packet, _, data = data.partition("\n")
            else:
                packet = self.NO_PACKET
            new_chunk = yield packet
            if new_chunk:
                data += new_chunk.decode("ascii")
            del new_chunk


def test_multiple_requests() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    try:
        server_started.wait()
        with PythonTCPClientSocket.connect((host, port)) as s:
            client: TCPNetworkClient[str] = TCPNetworkClient(s, protocol=StringNetworkProtocol())
            client.send_packet("A\nB\nC\nD\n")
            assert list(client.recv_packets()) == ["A", "B", "C", "D"]
            client.send_packet("E\nF\nG\nH\nI")
            assert client.recv_packet() == "E"
            assert client.recv_packet() == "F"
            assert list(client.recv_packets()) == ["G", "H"]
            client.send_packet("J\n")
            assert client.recv_packet() == "IJ"

            with pytest.raises(ValidationError):
                client.send_packet(5)  # type: ignore[arg-type]

    finally:
        shutdow_requested.set()
        server_thread.join()


def test_several_successive_send_using_pickling_protocol() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    try:
        server_started.wait()
        with TCPNetworkClient[Any]((host, port), protocol=PicklingNetworkProtocol()) as client:
            client.send_packet({"data": [5, 2]})
            client.send_packet("Hello")
            client.send_packet(132)
            assert client.recv_packet() == {"data": [5, 2]}
            assert client.recv_packet() == "Hello"
            assert client.recv_packet() == 132
    finally:
        shutdow_requested.set()
        server_thread.join()


def test_several_successive_send_using_json_protocol() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    try:
        server_started.wait()
        with TCPNetworkClient[Any]((host, port), protocol=JSONNetworkProtocol()) as client:
            client.send_packet({"data": [5, 2]})
            client.send_packet("Hello")
            client.send_packet(132)
            assert client.recv_packet() == {"data": [5, 2]}
            assert client.recv_packet() == "Hello"
            assert client.recv_packet() == 132
    finally:
        shutdow_requested.set()
        server_thread.join()


def test_several_successive_send_using_secured_pickling_protocol() -> None:
    server_started: Event = Event()
    shutdow_requested: Event = Event()
    host: str = "localhost"
    port: int = random_port()

    server_started.clear()
    shutdow_requested.clear()
    server_thread: Thread = launch_server(host, port, server_started, shutdow_requested)
    try:
        server_started.wait()
        with TCPNetworkClient[Any]((host, port), protocol=SafePicklingNetworkProtocol(generate_key())) as client:
            client.send_packet({"data": [5, 2]})
            client.send_packet("Hello")
            client.send_packet(132)
            assert client.recv_packet() == {"data": [5, 2]}
            assert client.recv_packet() == "Hello"
            assert client.recv_packet() == 132
    finally:
        shutdow_requested.set()
        server_thread.join()
