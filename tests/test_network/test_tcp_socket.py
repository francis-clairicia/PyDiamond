# -*- coding: Utf-8 -*-

from __future__ import annotations

from socket import has_dualstack_ipv6, has_ipv6 as HAS_IPV6

from pydiamond.network.socket import (
    AF_INET,
    AF_INET6,
    IPv4SocketAddress,
    IPv6SocketAddress,
    PythonTCPClientSocket,
    PythonTCPServerSocket,
    SocketAddress,
)
from pydiamond.system.threading import Thread, thread_factory

import pytest

from .random_port import random_port


def test_ipv4_client_server_connection() -> None:
    server_started: bool = False
    host: str = "localhost"
    port: int = random_port()

    @thread_factory
    def launch_server() -> None:
        nonlocal server_started
        with PythonTCPServerSocket.bind((host, port), family=AF_INET, backlog=1) as s:
            assert s.is_open()
            assert s.family == AF_INET
            addr: SocketAddress = s.getsockname()
            assert isinstance(addr, IPv4SocketAddress)
            server_started = True
            conn, addr = s.accept()
            with conn:
                assert conn.family == s.family
                while data := conn.recv(1024):
                    conn.send(data)
        assert not s.is_open()

    server_thread: Thread = launch_server()
    try:
        while not server_started:
            continue
        message: bytes = b"Hello, world"
        with PythonTCPClientSocket.connect((host, port), timeout=3) as s:
            assert s.is_open() and s.is_connected()
            assert s.family == AF_INET
            addr: SocketAddress = s.getsockname()
            assert isinstance(addr, IPv4SocketAddress)
            assert s.send(message) == len(message)
            data: bytes = s.recv(1024)
        assert data == message
        assert not s.is_open()
    finally:
        server_thread.join()
        server_started = False


@pytest.mark.skipif(not HAS_IPV6, reason="IPv6 is not supported on this machine")
def test_ipv6_client_server_connection() -> None:
    server_started: bool = False
    host: str = "localhost"
    port: int = random_port()

    @thread_factory
    def launch_server() -> None:
        nonlocal server_started
        with PythonTCPServerSocket.bind((host, port), family=AF_INET6, backlog=1) as s:
            assert s.is_open()
            assert s.family == AF_INET6
            addr: SocketAddress = s.getsockname()
            assert isinstance(addr, IPv6SocketAddress)
            server_started = True
            conn, addr = s.accept()
            with conn:
                assert conn.family == s.family
                while data := conn.recv(1024):
                    conn.send(data)
        assert not s.is_open()

    server_thread: Thread = launch_server()
    try:
        while not server_started:
            continue

        with pytest.raises(OSError):
            with PythonTCPClientSocket.connect((host, port), timeout=3, family=AF_INET) as s:
                ...

        message: bytes = b"Hello, world"
        with PythonTCPClientSocket.connect((host, port), timeout=3) as s:
            assert s.is_open() and s.is_connected()
            assert s.family == AF_INET6
            addr: SocketAddress = s.getsockname()
            assert isinstance(addr, IPv6SocketAddress)
            assert s.send(message) == len(message)
            data: bytes = s.recv(1024)
        assert not s.is_open()
        assert data == message
    finally:
        server_thread.join()
        server_started = False


@pytest.mark.skipif(not has_dualstack_ipv6(), reason="Dualstack IPv6 is not supported on this machine")
def test_dualstack_ipv6_client_server_connection() -> None:
    server_started: bool = False
    host: str = "localhost"
    port: int = random_port()

    @thread_factory
    def launch_server() -> None:
        nonlocal server_started
        with PythonTCPServerSocket.bind((host, port), family=AF_INET6, backlog=1, dualstack_ipv6=True) as s:
            assert s.is_open()
            assert s.family == AF_INET6
            addr: SocketAddress = s.getsockname()
            assert isinstance(addr, IPv6SocketAddress)
            server_started = True
            conn, addr = s.accept()
            with conn:
                assert conn.family == s.family
                while data := conn.recv(1024):
                    conn.send(data)
        assert not s.is_open()

    server_thread: Thread = launch_server()
    try:
        while not server_started:
            continue

        with pytest.raises(OSError):
            with PythonTCPClientSocket.connect((host, port), family=AF_INET) as s:
                ...

        message: bytes = b"Hello, world"
        with PythonTCPClientSocket.connect((host, port), timeout=3, family=AF_INET6) as s:
            assert s.is_open() and s.is_connected()
            assert s.family == AF_INET6
            assert s.send(message) == len(message)
            data: bytes = s.recv(1024)
        assert not s.is_open()
        assert data == message
    finally:
        server_thread.join()
        server_started = False
