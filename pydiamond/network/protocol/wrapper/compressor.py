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
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from ....system.object import ObjectMeta, final
from ....system.utils.abc import concreteclass
from ..abc import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol, ValidationError
from ..stream import AutoParsedPacketDeserializer, AutoParsedPacketSerializer, StreamNetworkProtocol
from .generic import GenericNetworkPacketDeserializerWrapper, GenericNetworkPacketSerializerWrapper

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)

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
    GenericNetworkPacketSerializerWrapper[_ST_contra],
    AutoParsedPacketSerializer[_ST_contra],
    Generic[_ST_contra],
):
    def __init__(self, protocol: NetworkPacketSerializer[_ST_contra], *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return bz2.compress(data, compresslevel=self.compresslevel)


@concreteclass
class BZ2CompressorPacketDeserializer(
    _BaseCompressor,
    GenericNetworkPacketDeserializerWrapper[_DT_co],
    AutoParsedPacketDeserializer[_DT_co],
    Generic[_DT_co],
):
    def __init__(self, protocol: NetworkPacketDeserializer[_DT_co]) -> None:
        super().__init__(protocol=protocol)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = bz2.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occurred") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class BZ2CompressorNetworkProtocol(
    BZ2CompressorPacketSerializer[_ST_contra],
    BZ2CompressorPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    if TYPE_CHECKING:

        @property
        def protocol(self) -> NetworkProtocol[_ST_contra, _DT_co]:
            ...


@concreteclass
class GzipCompressorPacketSerializer(
    _BaseCompressorSerializer,
    GenericNetworkPacketSerializerWrapper[_ST_contra],
    AutoParsedPacketSerializer[_ST_contra],
    Generic[_ST_contra],
):
    def __init__(self, protocol: NetworkPacketSerializer[_ST_contra], *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return gzip.compress(data, compresslevel=self.compresslevel)


@concreteclass
class GzipCompressorPacketDeserializer(
    _BaseCompressor,
    GenericNetworkPacketDeserializerWrapper[_DT_co],
    AutoParsedPacketDeserializer[_DT_co],
    Generic[_DT_co],
):
    def __init__(self, protocol: NetworkPacketDeserializer[_DT_co]) -> None:
        super().__init__(protocol=protocol)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = gzip.decompress(data)
        except Exception as exc:  # TODO: Find the appropriate exceptions
            raise ValidationError("Unrelated exception occurred") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class GzipCompressorNetworkProtocol(
    GzipCompressorPacketSerializer[_ST_contra],
    GzipCompressorPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    if TYPE_CHECKING:

        @property
        def protocol(self) -> NetworkProtocol[_ST_contra, _DT_co]:
            ...


@concreteclass
class ZlibCompressorPacketSerializer(
    _BaseCompressorSerializer,
    GenericNetworkPacketSerializerWrapper[_ST_contra],
    AutoParsedPacketSerializer[_ST_contra],
    Generic[_ST_contra],
):
    def __init__(self, protocol: NetworkPacketSerializer[_ST_contra], *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        data: bytes = self.protocol.serialize(packet)
        return zlib.compress(data, level=self.compresslevel)


@concreteclass
class ZlibCompressorPacketDeserializer(
    _BaseCompressor,
    GenericNetworkPacketDeserializerWrapper[_DT_co],
    AutoParsedPacketDeserializer[_DT_co],
    Generic[_DT_co],
):
    def __init__(self, protocol: NetworkPacketDeserializer[_DT_co]) -> None:
        super().__init__(protocol=protocol)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = zlib.decompress(data)
        except zlib.error as exc:
            raise ValidationError("zlib.error occurred") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class ZlibCompressorNetworkProtocol(
    BZ2CompressorPacketSerializer[_ST_contra],
    BZ2CompressorPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = zlib.Z_BEST_COMPRESSION) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    if TYPE_CHECKING:

        @property
        def protocol(self) -> NetworkProtocol[_ST_contra, _DT_co]:
            ...
