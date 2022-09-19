# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network packet protocol module"""

from __future__ import annotations

__all__ = [
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
    "ZlibCompressorNetworkProtocol",
    "ZlibCompressorPacketDeserializer",
    "ZlibCompressorPacketSerializer",
]

from .compressor import *
from .encryptor import *
from .generic import *
