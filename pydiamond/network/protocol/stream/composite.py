# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
""" network packet protocol composite module"""

from __future__ import annotations

__all__ = ["StreamNetworkProtocolComposite"]

from typing import Generator, TypeVar, final

from ....system.object import Object, ProtocolObjectMeta
from ....system.utils.abc import concreteclass
from .abc import NetworkPacketIncrementalDeserializer, NetworkPacketIncrementalSerializer, StreamNetworkProtocol

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@concreteclass
class StreamNetworkProtocolComposite(StreamNetworkProtocol[_ST_contra, _DT_co], Object, metaclass=ProtocolObjectMeta):
    __slots__ = ("__s", "__d")

    def __init__(
        self,
        serializer: NetworkPacketIncrementalSerializer[_ST_contra],
        deserializer: NetworkPacketIncrementalDeserializer[_DT_co],
    ) -> None:
        super().__init__()
        assert isinstance(serializer, NetworkPacketIncrementalSerializer)
        assert isinstance(deserializer, NetworkPacketIncrementalDeserializer)
        self.__s: NetworkPacketIncrementalSerializer[_ST_contra] = serializer
        self.__d: NetworkPacketIncrementalDeserializer[_DT_co] = deserializer

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        return self.__s.serialize(packet)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        return self.__d.deserialize(data)

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        return self.__s.incremental_serialize(packet)

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        return self.__d.incremental_deserialize()

    def get_serializer(self) -> NetworkPacketIncrementalSerializer[_ST_contra]:
        return self.__s

    def get_deserializer(self) -> NetworkPacketIncrementalDeserializer[_DT_co]:
        return self.__d
