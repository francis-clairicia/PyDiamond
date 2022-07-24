# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

from __future__ import annotations

__all__ = [
    "BZ2CompressorNetworkProtocol",
    "BZ2CompressorPacketDeserializer",
    "BZ2CompressorPacketSerializer",
    "GzipCompressorNetworkProtocol",
    "GzipCompressorPacketDeserializer",
    "GzipCompressorPacketSerializer",
    "ZlibCompressorNetworkProtocol",
    "ZlibCompressorPacketDeserializer",
    "ZlibCompressorPacketSerializer",
]

import bz2
import gzip
import zlib
from typing import Any, Generic, TypeVar

from ...system.object import ObjectMeta, final
from ...system.utils.abc import concreteclass
from .base import (
    GenericNetworkPacketDeserializerWrapper,
    GenericNetworkPacketSerializerWrapper,
    GenericNetworkProtocolWrapper,
    NetworkPacketDeserializer,
    NetworkPacketSerializer,
    NetworkProtocol,
    ValidationError,
)
from .stream import AutoParsedPacketDeserializer, AutoParsedPacketSerializer, StreamNetworkProtocol

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)
_SP = TypeVar("_SP", bound=NetworkPacketSerializer[Any])
_DP = TypeVar("_DP", bound=NetworkPacketDeserializer[Any])
_P = TypeVar("_P", bound=NetworkProtocol[Any, Any])

# TODO: Incremental compression/decompression
# TODO: Do not use AutoParsedStreamNetworkProtocol


class _BaseCompressor(metaclass=ObjectMeta):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)


class _BaseCompressorSerializer(_BaseCompressor):
    def __init__(self, *, compresslevel: int, **kwargs: Any) -> None:
        self.__compresslevel: int = compresslevel
        super().__init__(**kwargs)

    @property
    @final
    def compresslevel(self) -> int:
        return self.__compresslevel


@concreteclass
class BZ2CompressorPacketSerializer(
    _BaseCompressorSerializer,
    GenericNetworkPacketSerializerWrapper[_T_contra, _SP],
    AutoParsedPacketSerializer[_T_contra],
    Generic[_T_contra, _SP],
):
    def __init__(self, protocol: _SP, *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return bz2.compress(data, compresslevel=self.compresslevel)


@concreteclass
class BZ2CompressorPacketDeserializer(
    _BaseCompressor,
    GenericNetworkPacketDeserializerWrapper[_T_co, _DP],
    AutoParsedPacketDeserializer[_T_co],
    Generic[_T_co, _DP],
):
    def __init__(self, protocol: _DP) -> None:
        super().__init__(protocol=protocol)

    @final
    def deserialize(self, data: bytes) -> _T_co:
        try:
            data = bz2.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occurred") from exc
        packet: _T_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class BZ2CompressorNetworkProtocol(
    GenericNetworkProtocolWrapper[_T_contra, _T_co, _P],
    BZ2CompressorPacketSerializer[_T_contra, _P],
    BZ2CompressorPacketDeserializer[_T_co, _P],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co, _P],
):
    def __init__(self, protocol: _P, *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)


@concreteclass
class GzipCompressorPacketSerializer(
    _BaseCompressorSerializer,
    GenericNetworkPacketSerializerWrapper[_T_contra, _SP],
    AutoParsedPacketSerializer[_T_contra],
    Generic[_T_contra, _SP],
):
    def __init__(self, protocol: _SP, *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return gzip.compress(data, compresslevel=self.compresslevel)


@concreteclass
class GzipCompressorPacketDeserializer(
    _BaseCompressor,
    GenericNetworkPacketDeserializerWrapper[_T_co, _DP],
    AutoParsedPacketDeserializer[_T_co],
    Generic[_T_co, _DP],
):
    def __init__(self, protocol: _DP) -> None:
        super().__init__(protocol=protocol)

    @final
    def deserialize(self, data: bytes) -> _T_co:
        try:
            data = gzip.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occurred") from exc
        packet: _T_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class GzipCompressorNetworkProtocol(
    GenericNetworkProtocolWrapper[_T_contra, _T_co, _P],
    GzipCompressorPacketSerializer[_T_contra, _P],
    GzipCompressorPacketDeserializer[_T_co, _P],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co, _P],
):
    def __init__(self, protocol: _P, *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)


@concreteclass
class ZlibCompressorPacketSerializer(
    _BaseCompressorSerializer,
    GenericNetworkPacketSerializerWrapper[_T_contra, _SP],
    AutoParsedPacketSerializer[_T_contra],
    Generic[_T_contra, _SP],
):
    def __init__(self, protocol: _SP, *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return zlib.compress(data, level=self.compresslevel)


@concreteclass
class ZlibCompressorPacketDeserializer(
    _BaseCompressor,
    GenericNetworkPacketDeserializerWrapper[_T_co, _DP],
    AutoParsedPacketDeserializer[_T_co],
    Generic[_T_co, _DP],
):
    def __init__(self, protocol: _DP) -> None:
        super().__init__(protocol=protocol)

    @final
    def deserialize(self, data: bytes) -> _T_co:
        try:
            data = zlib.decompress(data)
        except zlib.error as exc:
            raise ValidationError("zlib.error occurred") from exc
        packet: _T_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class ZlibCompressorNetworkProtocol(
    GenericNetworkProtocolWrapper[_T_contra, _T_co, _P],
    BZ2CompressorPacketSerializer[_T_contra, _P],
    BZ2CompressorPacketDeserializer[_T_co, _P],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co, _P],
):
    def __init__(self, protocol: _P, *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)
