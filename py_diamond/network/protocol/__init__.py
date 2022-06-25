# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network packet protocol module"""

from __future__ import annotations

__all__ = [
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
    "StreamNetworkPacketHandler",
    "StreamNetworkProtocol",
    "ValidationError",
    "ZlibCompressorNetworkProtocol",
    "ZlibCompressorPacketDeserializer",
    "ZlibCompressorPacketSerializer",
]


############ Package initialization ############
from .base import *
from .compressor import *
from .encryptor import *
from .json import *
from .pickle import *
from .stream import *
