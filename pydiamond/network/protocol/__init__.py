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
    "BZ2CompressorPacketDeserializer",
    "BZ2CompressorPacketSerializer",
    "EncryptorNetworkProtocol",
    "EncryptorPacketDeserializer",
    "EncryptorPacketSerializer",
    "FixedPacketSizeDeserializer",
    "FixedPacketSizeSerializer",
    "FixedPacketSizeStreamNetworkProtocol",
    "GenericNetworkPacketDeserializerWrapper",
    "GenericNetworkPacketSerializerWrapper",
    "GenericNetworkProtocolWrapper",
    "GzipCompressorNetworkProtocol",
    "GzipCompressorPacketDeserializer",
    "GzipCompressorPacketSerializer",
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
    "SafePicklePacketDeserializer",
    "SafePicklePacketSerializer",
    "StreamNetworkProtocol",
    "ValidationError",
    "ZlibCompressorNetworkProtocol",
    "ZlibCompressorPacketDeserializer",
    "ZlibCompressorPacketSerializer",
]


############ Package initialization ############
from .abc import *
from .json import *
from .pickle import *
from .stream import *
from .struct import *
from .wrapper import *
