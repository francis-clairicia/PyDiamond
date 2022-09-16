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

from .base import ValidationError
from .stream import (
    FixedPacketSizeDeserializer,
    FixedPacketSizeSerializer,
    FixedPacketSizeStreamNetworkProtocol,
    _BaseFixedPacketSize,
)

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


class _BaseStructPacket(_BaseFixedPacketSize):
    def __init__(self, format: str, **kwargs: Any) -> None:
        struct = Struct(format)
        super().__init__(struct.size, **kwargs)
        self.__s: Struct = struct

    @property
    def struct(self) -> Struct:
        return self.__s


class AbstractStructPacketSerializer(_BaseStructPacket, FixedPacketSizeSerializer[_T_contra]):
    @abstractmethod
    def to_tuple(self, packet: _T_contra) -> tuple[Any, ...]:
        raise NotImplementedError

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        tuple_value = self.to_tuple(packet)
        try:
            return self.struct.pack(*tuple_value)
        except StructError as exc:
            raise ValidationError("Invalid value") from exc


class AbstractStructPacketDeserializer(_BaseStructPacket, FixedPacketSizeDeserializer[_T_co]):
    @abstractmethod
    def from_tuple(self, t: tuple[Any, ...]) -> _T_co:
        raise NotImplementedError

    @final
    def deserialize(self, data: bytes) -> _T_co:
        try:
            packet_tuple: tuple[Any, ...] = self.struct.unpack(data)
        except StructError as exc:
            raise ValidationError("Invalid value") from exc
        return self.from_tuple(packet_tuple)


class AbstractStructNetworkProtocol(
    AbstractStructPacketSerializer[_T_contra],
    AbstractStructPacketDeserializer[_T_co],
    FixedPacketSizeStreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co],
):
    pass
