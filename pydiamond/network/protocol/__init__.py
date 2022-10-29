# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractStructNetworkProtocol",
    "AutoParsedStreamNetworkProtocol",
    "AutoSeparatedStreamNetworkProtocol",
    "BZ2CompressorNetworkProtocol",
    "EncryptorNetworkProtocol",
    "FixedPacketSizeStreamNetworkProtocol",
    "GzipCompressorNetworkProtocol",
    "JSONNetworkProtocol",
    "NamedTupleNetworkProtocol",
    "NetworkPacketDeserializer",
    "NetworkPacketIncrementalDeserializer",
    "NetworkPacketIncrementalSerializer",
    "NetworkPacketSerializer",
    "NetworkProtocol",
    "NetworkProtocolComposite",
    "PickleNetworkProtocol",
    "SafePickleNetworkProtocol",
    "StreamNetworkProtocol",
    "StreamNetworkProtocolComposite",
    "ValidationError",
    "ZlibCompressorNetworkProtocol",
]


############ Package initialization ############
from .abc import *
from .composite import *
from .json import *
from .pickle import *
from .stream import *
from .struct import *
from .wrapper import *
