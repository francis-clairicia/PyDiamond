# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network socket module"""

__all__ = [
    "AF_INET",
    "AF_INET6",
    "AbstractSocket",
    "AbstractTCPClientSocket",
    "AbstractTCPServerSocket",
    "AbstractTCPSocket",
    "AbstractUDPClientSocket",
    "AbstractUDPServerSocket",
    "AbstractUDPSocket",
    "AddressFamily",
    "IPv4SocketAddress",
    "IPv6SocketAddress",
    "PythonTCPClientSocket",
    "PythonTCPServerSocket",
    "PythonUDPClientSocket",
    "PythonUDPServerSocket",
    "ReceivedDatagram",
    "SHUT_RD",
    "SHUT_RDWR",
    "SHUT_WR",
    "SOCK_DGRAM",
    "SOCK_STREAM",
    "ShutdownFlag",
    "SocketAddress",
    "SocketKind",
    "SocketMeta",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractTCPServerSocket,
    AbstractTCPSocket,
    AbstractUDPClientSocket,
    AbstractUDPServerSocket,
    AbstractUDPSocket,
    IPv4SocketAddress,
    IPv6SocketAddress,
    ReceivedDatagram,
    SocketAddress,
    SocketMeta,
)
from .constants import (
    AF_INET,
    AF_INET6,
    SHUT_RD,
    SHUT_RDWR,
    SHUT_WR,
    SOCK_DGRAM,
    SOCK_STREAM,
    AddressFamily,
    ShutdownFlag,
    SocketKind,
)
from .python import PythonTCPClientSocket, PythonTCPServerSocket, PythonUDPClientSocket, PythonUDPServerSocket
