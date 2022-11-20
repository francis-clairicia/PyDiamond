# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
""" network packet protocol composite module"""

from __future__ import annotations

__all__ = ["NetworkProtocolComposite"]

from typing import TypeVar, final

from ...system.utils.abc import concreteclass
from .abc import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@concreteclass
class NetworkProtocolComposite(NetworkProtocol[_ST_contra, _DT_co]):
    __slots__ = ("__s", "__d")

    def __init__(self, serializer: NetworkPacketSerializer[_ST_contra], deserializer: NetworkPacketDeserializer[_DT_co]) -> None:
        super().__init__()
        assert isinstance(serializer, NetworkPacketSerializer)
        assert isinstance(deserializer, NetworkPacketDeserializer)
        self.__s: NetworkPacketSerializer[_ST_contra] = serializer
        self.__d: NetworkPacketDeserializer[_DT_co] = deserializer

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        return self.__s.serialize(packet)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        return self.__d.deserialize(data)

    def get_serializer(self) -> NetworkPacketSerializer[_ST_contra]:
        return self.__s

    def get_deserializer(self) -> NetworkPacketDeserializer[_DT_co]:
        return self.__d
