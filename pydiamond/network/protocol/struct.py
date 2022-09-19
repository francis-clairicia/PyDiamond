# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""struct.Struct-based network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractStructNetworkProtocol",
    "AbstractStructPacketDeserializer",
    "AbstractStructPacketSerializer",
]

from abc import abstractmethod
from struct import Struct, error as StructError
from typing import Any, Generic, TypeVar, final

from .abc import ValidationError
from .stream import (
    FixedPacketSizeDeserializer,
    FixedPacketSizeSerializer,
    FixedPacketSizeStreamNetworkProtocol,
    _BaseFixedPacketSize,
)

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


class _BaseStructPacket(_BaseFixedPacketSize):
    def __init__(self, format: str, **kwargs: Any) -> None:
        if format[0] not in {"@", "=", "<", ">", "!"}:
            format = f"!{format}"  # network byte order
        struct = Struct(format)
        super().__init__(struct.size, **kwargs)
        self.__s: Struct = struct

    @property
    def struct(self) -> Struct:
        return self.__s


class AbstractStructPacketSerializer(_BaseStructPacket, FixedPacketSizeSerializer[_ST_contra]):
    def __init__(self, format: str) -> None:
        super().__init__(format)

    @abstractmethod
    def to_tuple(self, packet: _ST_contra) -> tuple[Any, ...]:
        raise NotImplementedError

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        tuple_value = self.to_tuple(packet)
        try:
            return self.struct.pack(*tuple_value)
        except StructError as exc:
            raise ValidationError("Invalid value") from exc


class AbstractStructPacketDeserializer(_BaseStructPacket, FixedPacketSizeDeserializer[_DT_co]):
    def __init__(self, format: str) -> None:
        super().__init__(format)

    @abstractmethod
    def from_tuple(self, t: tuple[Any, ...]) -> _DT_co:
        raise NotImplementedError

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            packet_tuple: tuple[Any, ...] = self.struct.unpack(data)
        except StructError as exc:
            raise ValidationError("Invalid value") from exc
        return self.from_tuple(packet_tuple)


class AbstractStructNetworkProtocol(
    AbstractStructPacketSerializer[_ST_contra],
    AbstractStructPacketDeserializer[_DT_co],
    FixedPacketSizeStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    pass
