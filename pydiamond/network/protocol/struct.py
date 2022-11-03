# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""struct.Struct-based network packet protocol module"""

from __future__ import annotations

__all__ = ["AbstractStructNetworkProtocol", "NamedTupleNetworkProtocol"]

from abc import abstractmethod
from struct import Struct, error as StructError
from typing import Any, NamedTuple, TypeVar, final

from ...system.utils.abc import concreteclass
from ...system.utils.collections import is_namedtuple_class
from .exceptions import DeserializeError
from .stream.abc import FixedPacketSizeStreamNetworkProtocol

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


class AbstractStructNetworkProtocol(FixedPacketSizeStreamNetworkProtocol[_ST_contra, _DT_co]):
    __slots__ = ("__s",)

    def __init__(self, format: str) -> None:
        if format[0] not in {"@", "=", "<", ">", "!"}:
            format = f"!{format}"  # network byte order
        struct = Struct(format)
        super().__init__(struct.size)
        self.__s: Struct = struct

    @abstractmethod
    def to_tuple(self, packet: _ST_contra) -> tuple[Any, ...]:
        raise NotImplementedError

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        struct = self.__s
        tuple_value = self.to_tuple(packet)
        return struct.pack(*tuple_value)

    @abstractmethod
    def from_tuple(self, t: tuple[Any, ...]) -> _DT_co:
        raise NotImplementedError

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        struct = self.__s
        if len(data) != struct.size:
            raise DeserializeError("Invalid data size")
        try:
            packet_tuple: tuple[Any, ...] = struct.unpack(data)
        except StructError as exc:
            raise DeserializeError(f"Invalid value: {exc}") from exc
        return self.from_tuple(packet_tuple)

    @property
    @final
    def struct(self) -> Struct:
        return self.__s


_NT = TypeVar("_NT", bound=NamedTuple)


@concreteclass
class NamedTupleNetworkProtocol(AbstractStructNetworkProtocol[_NT, _NT]):
    __slots__ = ("__namedtuple_cls",)

    def __init__(self, format: str, namedtuple_cls: type[_NT]) -> None:
        super().__init__(format)
        if not is_namedtuple_class(namedtuple_cls):
            raise TypeError("Expected namedtuple class")
        self.__namedtuple_cls: type[_NT] = namedtuple_cls

    @final
    def to_tuple(self, packet: _NT) -> tuple[Any, ...]:
        assert isinstance(packet, self.__namedtuple_cls)
        return packet

    @final
    def from_tuple(self, t: tuple[Any, ...]) -> _NT:
        return self.__namedtuple_cls._make(t)
