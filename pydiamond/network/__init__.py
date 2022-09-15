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
    "ConnectedClient",
    "DisconnectedClientError",
    "StateLessTCPNetworkServer",
    "StateLessUDPNetworkServer",
    "TCPClientError",
    "TCPNetworkClient",
    "UDPNetworkClient",
]


############ Package initialization ############
from .client import *
from .server import *
