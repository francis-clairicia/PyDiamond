# -*- coding: Utf-8 -*-

from __future__ import annotations

from functools import partial
from selectors import EVENT_READ, DefaultSelector
from threading import Event
from typing import Any, Generator

from pydiamond.network.client import TCPNetworkClient
from pydiamond.network.protocol import (
    JSONNetworkProtocol,
    PickleNetworkProtocol,
    SafePickleNetworkProtocol,
    StreamNetworkProtocol,
    ValidationError,
)
from pydiamond.network.socket import PythonTCPClientSocket, PythonTCPServerSocket
from pydiamond.system.threading import Thread, thread_factory

import pytest
from cryptography.fernet import Fernet

from .random_port import random_port


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
        with TCPNetworkClient[Any, Any]((host, port)) as client:
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
            client: TCPNetworkClient[Any, Any] = TCPNetworkClient(s)
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
        with TCPNetworkClient[Any, Any]((host, port), protocol=SafePickleNetworkProtocol(Fernet.generate_key())) as client:
            client.send_packet({"data": [5, 2]})
            assert client.recv_packet() == {"data": [5, 2]}
            client.send_packet("Hello")
            assert client.recv_packet() == "Hello"
    finally:
        shutdow_requested.set()
        server_thread.join()


class StringNetworkProtocol(StreamNetworkProtocol[str, str]):
    def incremental_serialize(self, packet: str) -> Generator[bytes, None, None]:
        if not isinstance(packet, str):
            raise ValidationError("Invalid string")
        yield from map(partial(str.encode, encoding="ascii"), packet.splitlines(True))

    def incremental_deserialize(self) -> Generator[None, bytes, tuple[Any, bytes]]:
        data: str = str()
        while True:
            data += (yield).decode("ascii")
            if "\n" in data:
                packet, _, data = data.partition("\n")
                return packet, data.encode("ascii")


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
            client: TCPNetworkClient[str, str] = TCPNetworkClient(s, protocol=StringNetworkProtocol())
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
        with TCPNetworkClient[Any, Any]((host, port), protocol=PickleNetworkProtocol()) as client:
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
        with TCPNetworkClient[Any, Any]((host, port), protocol=JSONNetworkProtocol()) as client:
            client.send_packet({"data": [5, 2]})
            client.send_packet("Hello")
            client.send_packet([132])
            assert client.recv_packet() == {"data": [5, 2]}
            assert client.recv_packet() == "Hello"
            assert client.recv_packet() == [132]
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
        with TCPNetworkClient[Any, Any]((host, port), protocol=SafePickleNetworkProtocol(Fernet.generate_key())) as client:
            client.send_packet({"data": [5, 2]})
            client.send_packet("Hello")
            client.send_packet(132)
            assert client.recv_packet() == {"data": [5, 2]}
            assert client.recv_packet() == "Hello"
            assert client.recv_packet() == 132
    finally:
        shutdow_requested.set()
        server_thread.join()
