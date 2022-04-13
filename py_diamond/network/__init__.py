# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network module"""

__all__ = [
    "AF_INET",
    "AF_INET6",
    "AbstractNetworkClient",
    "AbstractNetworkProtocol",
    "AbstractNetworkServer",
    "AbstractRequestHandler",
    "AbstractSocket",
    "AbstractTCPClientSocket",
    "AbstractTCPNetworkServer",
    "AbstractTCPRequestHandler",
    "AbstractTCPServerSocket",
    "AbstractTCPSocket",
    "AbstractUDPNetworkServer",
    "AbstractUDPRequestHandler",
    "AbstractUDPSocket",
    "AddressFamily",
    "ClientError",
    "ConnectedClient",
    "DisconnectedClientError",
    "IPv4SocketAddress",
    "IPv6SocketAddress",
    "PicklingNetworkProtocol",
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
    "SecuredNetworkProtocol",
    "SecuredNetworkProtocolMeta",
    "ShutdownFlag",
    "SocketKind",
    "SocketMeta",
    "TCPNetworkClient",
    "TCPNetworkServer",
    "UDPNetworkClient",
    "UDPNetworkServer",
    "ValidationError",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .client import AbstractNetworkClient, ClientError, DisconnectedClientError, TCPNetworkClient, UDPNetworkClient
from .protocol import (
    AbstractNetworkProtocol,
    PicklingNetworkProtocol,
    SecuredNetworkProtocol,
    SecuredNetworkProtocolMeta,
    ValidationError,
)
from .server import (
    AbstractNetworkServer,
    AbstractRequestHandler,
    AbstractTCPNetworkServer,
    AbstractTCPRequestHandler,
    AbstractUDPNetworkServer,
    AbstractUDPRequestHandler,
    ConnectedClient,
    TCPNetworkServer,
    UDPNetworkServer,
)
from .socket import (
    AF_INET,
    AF_INET6,
    SHUT_RD,
    SHUT_RDWR,
    SHUT_WR,
    SOCK_DGRAM,
    SOCK_STREAM,
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractTCPServerSocket,
    AbstractTCPSocket,
    AbstractUDPSocket,
    AddressFamily,
    IPv4SocketAddress,
    IPv6SocketAddress,
    PythonTCPClientSocket,
    PythonTCPServerSocket,
    PythonUDPClientSocket,
    PythonUDPServerSocket,
    ReceivedDatagram,
    ShutdownFlag,
    SocketKind,
    SocketMeta,
)
