# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

from __future__ import annotations

__all__ = [
    "EncryptorNetworkProtocol",
    "EncryptorPacketDeserializer",
    "EncryptorPacketSerializer",
]

from typing import Any, Generic, TypeVar

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from typing_extensions import assert_never

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import (
    GenericNetworkPacketDeserializerWrapper,
    GenericNetworkPacketSerializerWrapper,
    GenericNetworkProtocolWrapper,
    NetworkPacketDeserializer,
    NetworkPacketSerializer,
    NetworkProtocol,
    ValidationError,
)
from .stream import (
    AutoSeparatedPacketDeserializer,
    AutoSeparatedPacketSerializer,
    StreamNetworkProtocol,
    _BaseAutoSeparatedPacket,
)

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)
_SP = TypeVar("_SP", bound=NetworkPacketSerializer[Any])
_DP = TypeVar("_DP", bound=NetworkPacketDeserializer[Any])
_P = TypeVar("_P", bound=NetworkProtocol[Any, Any])


class _BaseEncryptor(_BaseAutoSeparatedPacket):
    def __init__(self, key: str | bytes | Fernet | MultiFernet, **kwargs: Any) -> None:
        self.__key: MultiFernet
        match key:
            case MultiFernet():
                self.__key = key
            case Fernet():
                self.__key = MultiFernet([key])
            case str() | bytes():
                self.__key = MultiFernet([Fernet(key)])
            case _:
                assert_never(key)
        super().__init__(separator=b"\r\n", keepends=False, **kwargs)

    @property
    @final
    def key(self) -> MultiFernet:
        return self.__key


@concreteclass
class EncryptorPacketSerializer(
    _BaseEncryptor,
    GenericNetworkPacketSerializerWrapper[_T_contra, _SP],
    AutoSeparatedPacketSerializer[_T_contra],
    Generic[_T_contra, _SP],
):
    def __init__(self, protocol: _SP, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        return self.key.encrypt(self.protocol.serialize(packet))


@concreteclass
class EncryptorPacketDeserializer(
    _BaseEncryptor,
    GenericNetworkPacketDeserializerWrapper[_T_co, _DP],
    AutoSeparatedPacketDeserializer[_T_co],
    Generic[_T_co, _DP],
):
    def __init__(self, protocol: _DP, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)

    @final
    def deserialize(self, data: bytes) -> _T_co:
        try:
            data = self.key.decrypt(data)
        except InvalidToken as exc:
            raise ValidationError("Invalid token") from exc
        packet: _T_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class EncryptorNetworkProtocol(
    GenericNetworkProtocolWrapper[_T_contra, _T_co, _P],
    EncryptorPacketSerializer[_T_contra, _P],
    EncryptorPacketDeserializer[_T_co, _P],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co, _P],
):
    def __init__(self, protocol: _P, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)
