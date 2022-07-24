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
    "NetworkPacketDeserializer",
    "NetworkPacketSerializer",
    "NetworkProtocol",
    "ValidationError",
]

from abc import abstractmethod
from typing import Any, Generic, Protocol, TypeVar, runtime_checkable

from ...system.object import ProtocolObjectMeta, final


class ValidationError(Exception):
    pass


_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


@runtime_checkable
class NetworkPacketSerializer(Protocol[_T_contra]):
    @abstractmethod
    def serialize(self, packet: _T_contra) -> bytes:
        raise NotImplementedError


@runtime_checkable
class NetworkPacketDeserializer(Protocol[_T_co]):
    @abstractmethod
    def deserialize(self, data: bytes) -> _T_co:
        raise NotImplementedError


@runtime_checkable
class NetworkProtocol(NetworkPacketSerializer[_T_contra], NetworkPacketDeserializer[_T_co], Protocol[_T_contra, _T_co]):
    pass


_AnyP = TypeVar("_AnyP")
_SP = TypeVar("_SP", bound=NetworkPacketSerializer[Any])
_DP = TypeVar("_DP", bound=NetworkPacketDeserializer[Any])
_P = TypeVar("_P", bound=NetworkProtocol[Any, Any])


class _BaseGenericWrapper(Generic[_AnyP], metaclass=ProtocolObjectMeta):
    def __init__(self, protocol: _AnyP, **kwargs: Any) -> None:
        self.__protocol: _AnyP = protocol
        super().__init__(**kwargs)

    @property
    @final
    def protocol(self) -> _AnyP:
        return self.__protocol


class GenericNetworkPacketSerializerWrapper(
    _BaseGenericWrapper[_SP],
    NetworkPacketSerializer[_T_contra],
    Generic[_T_contra, _SP],
):
    def __init__(self, protocol: _SP, **kwargs: Any) -> None:
        super().__init__(protocol=protocol, **kwargs)


class GenericNetworkPacketDeserializerWrapper(
    _BaseGenericWrapper[_DP],
    NetworkPacketDeserializer[_T_co],
    Generic[_T_co, _DP],
):
    def __init__(self, protocol: _DP, **kwargs: Any) -> None:
        super().__init__(protocol=protocol, **kwargs)


class GenericNetworkProtocolWrapper(
    GenericNetworkPacketSerializerWrapper[_T_contra, _P],
    GenericNetworkPacketDeserializerWrapper[_T_co, _P],
    Generic[_T_contra, _T_co, _P],
):
    def __init__(self, protocol: _P, **kwargs: Any) -> None:
        super().__init__(protocol=protocol, **kwargs)
