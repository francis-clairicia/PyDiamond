# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = [
    "GenericNetworkPacketDeserializerWrapper",
    "GenericNetworkPacketSerializerWrapper",
    "GenericNetworkProtocolWrapper",
]

from typing import Any, Generic, TypeVar

from ....system.object import ProtocolObjectMeta
from ..abc import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol


class ValidationError(Exception):
    pass


_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


_AnyP = TypeVar("_AnyP")


class _BaseGenericWrapper(Generic[_AnyP], metaclass=ProtocolObjectMeta):
    def __init__(self, protocol: _AnyP, **kwargs: Any) -> None:
        self.__protocol: _AnyP = protocol
        super().__init__(**kwargs)

    @property
    def protocol(self) -> _AnyP:
        return self.__protocol


class GenericNetworkPacketSerializerWrapper(
    _BaseGenericWrapper[NetworkPacketSerializer[_ST_contra]],
    NetworkPacketSerializer[_ST_contra],
    Generic[_ST_contra],
):
    def __init__(self, protocol: NetworkPacketSerializer[_ST_contra], **kwargs: Any) -> None:
        super().__init__(protocol=protocol, **kwargs)


class GenericNetworkPacketDeserializerWrapper(
    _BaseGenericWrapper[NetworkPacketDeserializer[_DT_co]],
    NetworkPacketDeserializer[_DT_co],
    Generic[_DT_co],
):
    def __init__(self, protocol: NetworkPacketDeserializer[_DT_co], **kwargs: Any) -> None:
        super().__init__(protocol=protocol, **kwargs)


class GenericNetworkProtocolWrapper(
    _BaseGenericWrapper[NetworkProtocol[_ST_contra, _DT_co]],
    NetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], **kwargs: Any) -> None:
        super().__init__(protocol=protocol, **kwargs)
