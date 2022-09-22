# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractStructNetworkProtocol",
    "AbstractStructPacketDeserializer",
    "AbstractStructPacketSerializer",
    "AutoParsedPacketDeserializer",
    "AutoParsedPacketSerializer",
    "AutoParsedStreamNetworkProtocol",
    "AutoSeparatedPacketDeserializer",
    "AutoSeparatedPacketSerializer",
    "AutoSeparatedStreamNetworkProtocol",
    "BZ2CompressorNetworkProtocol",
    "EncryptorNetworkProtocol",
    "FixedPacketSizeDeserializer",
    "FixedPacketSizeSerializer",
    "FixedPacketSizeStreamNetworkProtocol",
    "GenericNetworkProtocolWrapper",
    "GzipCompressorNetworkProtocol",
    "JSONNetworkProtocol",
    "JSONPacketDeserializer",
    "JSONPacketSerializer",
    "NetworkPacketDeserializer",
    "NetworkPacketIncrementalDeserializer",
    "NetworkPacketIncrementalSerializer",
    "NetworkPacketSerializer",
    "NetworkProtocol",
    "PickleNetworkProtocol",
    "PicklePacketDeserializer",
    "PicklePacketSerializer",
    "SafePickleNetworkProtocol",
    "StreamNetworkProtocol",
    "ValidationError",
    "ZlibCompressorNetworkProtocol",
]


############ Package initialization ############
from .abc import *
from .json import *
from .pickle import *
from .stream import *
from .struct import *
from .wrapper import *
