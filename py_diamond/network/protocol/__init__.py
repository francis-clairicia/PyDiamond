# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network packet protocol module"""

__all__ = [
    "AbstractNetworkProtocol",
    "AutoParsedStreamNetworkProtocol",
    "BZ2CompressorProtocol",
    "GzipCompressorProtocol",
    "JSONNetworkProtocol",
    "PicklingNetworkProtocol",
    "SecuredNetworkProtocol",
    "SecuredNetworkProtocolMeta",
    "ValidationError",
    "ZlibCompressorProtocol",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .base import (
    AbstractNetworkProtocol,
    AutoParsedStreamNetworkProtocol,
    SecuredNetworkProtocol,
    SecuredNetworkProtocolMeta,
    ValidationError,
)
from .compressor import BZ2CompressorProtocol, GzipCompressorProtocol, ZlibCompressorProtocol
from .json import JSONNetworkProtocol
from .pickle import PicklingNetworkProtocol
