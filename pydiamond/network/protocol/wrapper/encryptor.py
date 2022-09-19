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

from typing import TYPE_CHECKING, Any, Generic, TypeVar

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from typing_extensions import assert_never

from ....system.object import final
from ....system.utils.abc import concreteclass
from ..abc import NetworkPacketDeserializer, NetworkPacketSerializer, NetworkProtocol, ValidationError
from ..stream import (
    AutoSeparatedPacketDeserializer,
    AutoSeparatedPacketSerializer,
    StreamNetworkProtocol,
    _BaseAutoSeparatedPacket,
)
from .generic import GenericNetworkPacketDeserializerWrapper, GenericNetworkPacketSerializerWrapper

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


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
    GenericNetworkPacketSerializerWrapper[_ST_contra],
    AutoSeparatedPacketSerializer[_ST_contra],
    Generic[_ST_contra],
):
    def __init__(self, protocol: NetworkPacketSerializer[_ST_contra], key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        return self.key.encrypt(self.protocol.serialize(packet))


@concreteclass
class EncryptorPacketDeserializer(
    _BaseEncryptor,
    GenericNetworkPacketDeserializerWrapper[_DT_co],
    AutoSeparatedPacketDeserializer[_DT_co],
    Generic[_DT_co],
):
    def __init__(self, protocol: NetworkPacketDeserializer[_DT_co], key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = self.key.decrypt(data)
        except InvalidToken as exc:
            raise ValidationError("Invalid token") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet


@concreteclass
class EncryptorNetworkProtocol(
    EncryptorPacketSerializer[_ST_contra],
    EncryptorPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)

    if TYPE_CHECKING:

        @property
        def protocol(self) -> NetworkProtocol[_ST_contra, _DT_co]:
            ...
