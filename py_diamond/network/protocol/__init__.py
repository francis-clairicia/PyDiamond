# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkProtocol",
    "AbstractStreamNetworkProtocol",
    "AutoParsedStreamNetworkProtocol",
    "AutoSeparatedStreamNetworkProtocol",
    "BZ2CompressorProtocol",
    "EncryptorProtocol",
    "GzipCompressorProtocol",
    "JSONNetworkProtocol",
    "PicklingNetworkProtocol",
    "SafePicklingNetworkProtocol",
    "StreamNetworkPacketHandler",
    "ValidationError",
    "ZlibCompressorProtocol",
]


############ Package initialization ############
from .base import AbstractNetworkProtocol, ValidationError
from .compressor import BZ2CompressorProtocol, GzipCompressorProtocol, ZlibCompressorProtocol
from .encryptor import EncryptorProtocol
from .json import JSONNetworkProtocol
from .pickle import PicklingNetworkProtocol, SafePicklingNetworkProtocol
from .stream import (
    AbstractStreamNetworkProtocol,
    AutoParsedStreamNetworkProtocol,
    AutoSeparatedStreamNetworkProtocol,
    StreamNetworkPacketHandler,
)
