# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

from __future__ import annotations

__all__ = [
    "BZ2CompressorNetworkProtocol",
    "GzipCompressorNetworkProtocol",
    "ZlibCompressorNetworkProtocol",
]

import bz2
import gzip
import zlib
from typing import Any, Generic, TypeVar

from ....system.object import ProtocolObjectMeta, final
from ....system.utils.abc import concreteclass
from ..abc import NetworkProtocol, ValidationError
from ..stream import AutoParsedStreamNetworkProtocol
from .generic import GenericNetworkProtocolWrapper

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)

# TODO: Incremental compression/decompression
# TODO: Do not use AutoParsedStreamNetworkProtocol


class _BaseCompressor(metaclass=ProtocolObjectMeta):
    def __init__(self, *, compresslevel: int, **kwargs: Any) -> None:
        self.__compresslevel: int = compresslevel
        super().__init__(**kwargs)

    @property
    @final
    def compresslevel(self) -> int:
        return self.__compresslevel


@concreteclass
class BZ2CompressorNetworkProtocol(
    _BaseCompressor,
    GenericNetworkProtocolWrapper[_ST_contra, _DT_co],
    AutoParsedStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return bz2.compress(data, compresslevel=self.compresslevel)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = bz2.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occurred") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class GzipCompressorNetworkProtocol(
    _BaseCompressor,
    GenericNetworkProtocolWrapper[_ST_contra, _DT_co],
    AutoParsedStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return gzip.compress(data, compresslevel=self.compresslevel)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = gzip.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occurred") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class ZlibCompressorNetworkProtocol(
    _BaseCompressor,
    GenericNetworkProtocolWrapper[_ST_contra, _DT_co],
    AutoParsedStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return zlib.compress(data, level=self.compresslevel)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = zlib.decompress(data)
        except zlib.error as exc:
            raise ValidationError("zlib.error occurred") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet
