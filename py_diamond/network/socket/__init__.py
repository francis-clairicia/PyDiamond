# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
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
    "AbstractUDPSocket",
    "AddressFamily",
    "IPv4SocketAddress",
    "IPv6SocketAddress",
    "MetaSocket",
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
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractTCPServerSocket,
    AbstractTCPSocket,
    AbstractUDPSocket,
    IPv4SocketAddress,
    IPv6SocketAddress,
    MetaSocket,
    ReceivedDatagram,
    SocketAddress,
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
