# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkClient",
    "AbstractNetworkServer",
    "AbstractRequestHandler",
    "AbstractTCPNetworkServer",
    "AbstractTCPRequestHandler",
    "AbstractUDPNetworkServer",
    "AbstractUDPRequestHandler",
    "ClientError",
    "ConnectedClient",
    "DisconnectedClientError",
    "TCPNetworkClient",
    "TCPNetworkServer",
    "UDPNetworkClient",
    "UDPNetworkServer",
]


############ Package initialization ############
from .client import AbstractNetworkClient, ClientError, DisconnectedClientError, TCPNetworkClient, UDPNetworkClient
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
