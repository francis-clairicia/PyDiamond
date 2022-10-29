# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = [
    "NetworkPacketDeserializer",
    "NetworkPacketSerializer",
    "NetworkProtocol",
    "ValidationError",
]

from abc import abstractmethod
from typing import Protocol, TypeVar, runtime_checkable


class ValidationError(Exception):
    pass


_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@runtime_checkable
class NetworkPacketSerializer(Protocol[_ST_contra]):
    __slots__ = ()

    @abstractmethod
    def serialize(self, packet: _ST_contra) -> bytes:
        raise NotImplementedError


@runtime_checkable
class NetworkPacketDeserializer(Protocol[_DT_co]):
    __slots__ = ()

    @abstractmethod
    def deserialize(self, data: bytes) -> _DT_co:
        raise NotImplementedError


@runtime_checkable
class NetworkProtocol(NetworkPacketSerializer[_ST_contra], NetworkPacketDeserializer[_DT_co], Protocol[_ST_contra, _DT_co]):
    __slots__ = ()
