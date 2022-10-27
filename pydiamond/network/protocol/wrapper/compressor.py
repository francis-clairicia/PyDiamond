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

# import bz2
# import gzip
# import zlib
from typing import Any, Generic, TypeVar

from ....system.object import ProtocolObjectMeta, final
from ....system.utils.abc import concreteclass
from ..abc import NetworkProtocol
from ..stream import AutoParsedStreamNetworkProtocol
from .generic import GenericNetworkProtocolWrapper

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)

# TODO: Incremental compression/decompression
# TODO: Do not use AutoParsedStreamNetworkProtocol


class _BaseCompressor(metaclass=ProtocolObjectMeta):
    def __init__(self, *, compresslevel: int, **kwargs: Any) -> None:
        self.__compresslevel: int
        raise NotImplementedError

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
        raise NotImplementedError

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError


@concreteclass
class GzipCompressorNetworkProtocol(
    _BaseCompressor,
    GenericNetworkProtocolWrapper[_ST_contra, _DT_co],
    AutoParsedStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError


@concreteclass
class ZlibCompressorNetworkProtocol(
    _BaseCompressor,
    GenericNetworkProtocolWrapper[_ST_contra, _DT_co],
    AutoParsedStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], *, compresslevel: int = 9) -> None:
        super().__init__(protocol=protocol, compresslevel=compresslevel)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError
