# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

__all__ = ["BZ2CompressorProtocol", "GzipCompressorProtocol", "ZlibCompressorProtocol"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import bz2
import gzip
import zlib
from typing import Any

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import AbstractNetworkProtocol, AutoParsedStreamNetworkProtocol, ValidationError


@concreteclass
class BZ2CompressorProtocol(AutoParsedStreamNetworkProtocol):
    def __init__(self, protocol: AbstractNetworkProtocol, *, compresslevel: int = 9) -> None:
        super().__init__()
        self.__protocol: AbstractNetworkProtocol = protocol
        self.__compresslevel: int = compresslevel

    @final
    def serialize(self, packet: Any) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return bz2.compress(data, compresslevel=self.compresslevel)

    @final
    def deserialize(self, data: bytes) -> Any:
        try:
            data = bz2.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occured") from exc
        return self.protocol.deserialize(data)

    @property
    @final
    def protocol(self) -> AbstractNetworkProtocol:
        return self.__protocol

    @property
    @final
    def compresslevel(self) -> int:
        return self.__compresslevel


@concreteclass
class GzipCompressorProtocol(AutoParsedStreamNetworkProtocol):
    def __init__(self, protocol: AbstractNetworkProtocol, *, compresslevel: int = 9) -> None:
        super().__init__()
        self.__protocol: AbstractNetworkProtocol = protocol
        self.__compresslevel: int = compresslevel

    @final
    def serialize(self, packet: Any) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return gzip.compress(data, compresslevel=self.compresslevel)

    @final
    def deserialize(self, data: bytes) -> Any:
        try:
            data = gzip.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occured") from exc
        return self.protocol.deserialize(data)

    @property
    @final
    def protocol(self) -> AbstractNetworkProtocol:
        return self.__protocol

    @property
    @final
    def compresslevel(self) -> int:
        return self.__compresslevel


@concreteclass
class ZlibCompressorProtocol(AutoParsedStreamNetworkProtocol):
    def __init__(self, protocol: AbstractNetworkProtocol, *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__()
        self.__protocol: AbstractNetworkProtocol = protocol
        self.__compresslevel: int = compresslevel

    @final
    def serialize(self, packet: Any) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return zlib.compress(data, level=self.compresslevel)

    @final
    def deserialize(self, data: bytes) -> Any:
        try:
            data = zlib.decompress(data)
        except zlib.error as exc:
            raise ValidationError("zlib.error occured") from exc
        return self.protocol.deserialize(data)

    @property
    @final
    def protocol(self) -> AbstractNetworkProtocol:
        return self.__protocol

    @property
    @final
    def compresslevel(self) -> int:
        return self.__compresslevel
