# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network module"""

from __future__ import annotations

__all__ = [
    "AbstractForkingTCPNetworkServer",
    "AbstractForkingUDPNetworkServer",
    "AbstractNetworkClient",
    "AbstractNetworkServer",
    "AbstractRequestHandler",
    "AbstractTCPNetworkServer",
    "AbstractThreadingTCPNetworkServer",
    "AbstractThreadingUDPNetworkServer",
    "AbstractUDPNetworkServer",
    "ConnectedClient",
    "ForkingMixIn",
    "ForkingStateLessTCPNetworkServer",
    "ForkingStateLessUDPNetworkServer",
    "StateLessTCPNetworkServer",
    "StateLessUDPNetworkServer",
    "TCPNetworkClient",
    "ThreadingMixIn",
    "ThreadingStateLessTCPNetworkServer",
    "ThreadingStateLessUDPNetworkServer",
    "UDPNetworkClient",
]


############ Package initialization ############
from .client import *
from .server import *
