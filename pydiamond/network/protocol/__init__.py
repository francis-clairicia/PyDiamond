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
    "DeserializeError",
    "EncryptorNetworkProtocol",
    "FixedPacketSizeStreamNetworkProtocol",
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
    "ZlibCompressorNetworkProtocol",
]


############ Package initialization ############
from .abc import *
from .composite import *
from .exceptions import *
from .json import *
from .pickle import *
from .stream import *
from .struct import *
from .wrapper import *
