# -*- coding: Utf-8 -*-

from __future__ import annotations

from time import sleep
from typing import Any

from pydiamond.network.client import UDPNetworkClient
from pydiamond.network.server.stateless import (
    AbstractRequestHandler,
    ForkingStateLessUDPNetworkServer,
    StateLessUDPNetworkServer,
    ThreadingStateLessUDPNetworkServer,
)
from pydiamond.system.threading import Thread
from pydiamond.system.utils.os import has_fork

import pytest


class _MirrorRequestHandler(AbstractRequestHandler[Any, Any]):
    def handle(self) -> None:
        self.client.send_packet(self.request)


_RANDOM_HOST_PORT = ("localhost", 0)


def test_serve_forever_default() -> None:
    with StateLessUDPNetworkServer(_RANDOM_HOST_PORT, _MirrorRequestHandler) as server:
        assert not server.running()
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forever_context_shut_down() -> None:
    with StateLessUDPNetworkServer(_RANDOM_HOST_PORT, _MirrorRequestHandler) as server:
        t: Thread = Thread(target=server.serve_forever, args=(0.1,))
        t.start()
        sleep(0.15)
    t.join()
    assert not server.running()


def test_serve_forever_in_thread_default() -> None:
    with StateLessUDPNetworkServer(_RANDOM_HOST_PORT, _MirrorRequestHandler) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
        server.shutdown()
        t.join()
        assert not server.running()


def test_serve_forver_in_thread_context_shut_down() -> None:
    with StateLessUDPNetworkServer(_RANDOM_HOST_PORT, _MirrorRequestHandler) as server:
        t: Thread = server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.15)
        assert server.running()
    assert not server.running()
    assert not t.is_alive()


class _TestServiceActionServer(StateLessUDPNetworkServer[Any, Any]):
    def service_actions(self) -> None:
        super().service_actions()
        self.service_actions_called: bool = True


def test_service_actions() -> None:
    with _TestServiceActionServer(_RANDOM_HOST_PORT, _MirrorRequestHandler) as server:
        server.serve_forever_in_thread(poll_interval=0.1)
        sleep(0.3)
    assert getattr(server, "service_actions_called", False)


from .test_tcp_server import _IntegerNetworkProtocol


def test_request_handling() -> None:
    with StateLessUDPNetworkServer(_RANDOM_HOST_PORT, _MirrorRequestHandler, protocol_cls=_IntegerNetworkProtocol) as server:
        address = server.address
        server.serve_forever_in_thread(poll_interval=0.1)
        with (
            UDPNetworkClient(protocol=_IntegerNetworkProtocol()) as client_1,
            UDPNetworkClient(protocol=_IntegerNetworkProtocol()) as client_2,
            UDPNetworkClient(protocol=_IntegerNetworkProtocol()) as client_3,
        ):
            client_1.send_packet(address, 350)
            client_2.send_packet(address, -634)
            client_3.send_packet(address, 0)
            sleep(0.2)
            assert client_1.recv_packet()[0] == 350
            assert client_2.recv_packet()[0] == -634
            assert client_3.recv_packet()[0] == 0


class _ThreadingServerRequestHandler(AbstractRequestHandler[Any, Any]):
    def handle(self) -> None:
        import threading

        self.client.send_packet((self.request, threading.current_thread() is not threading.main_thread()))


def test_threading_server() -> None:
    with ThreadingStateLessUDPNetworkServer(_RANDOM_HOST_PORT, _ThreadingServerRequestHandler) as server:
        server.serve_forever_in_thread(poll_interval=0)
        with UDPNetworkClient[Any, Any]() as client:
            packet = {"data": 1}
            client.send_packet(server.address, packet)
            response: tuple[Any, bool] = client.recv_packet()[0]
            assert response[0] == packet
            assert response[1] is True


class _ForkingServerRequestHandler(AbstractRequestHandler[Any, Any]):
    def handle(self) -> None:
        from os import getpid

        self.client.send_packet((self.request, getpid()))


@pytest.mark.skipif(not has_fork(), reason="fork() not supported on this platform")
def test_forking_server() -> None:
    from os import getpid

    with ForkingStateLessUDPNetworkServer(_RANDOM_HOST_PORT, _ForkingServerRequestHandler) as server:
        server.serve_forever_in_thread(poll_interval=0)
        with UDPNetworkClient[Any, Any]() as client:
            packet = {"data": 1}
            client.send_packet(server.address, packet)
            response: tuple[Any, int] = client.recv_packet()[0]
            assert response[0] == packet
            assert response[1] != getpid()
