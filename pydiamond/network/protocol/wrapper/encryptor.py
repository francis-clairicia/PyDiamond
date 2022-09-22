# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

from __future__ import annotations

__all__ = ["EncryptorNetworkProtocol"]

from typing import Any, Generic, TypeVar

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from typing_extensions import assert_never

from ....system.object import final
from ....system.utils.abc import concreteclass
from ..abc import NetworkProtocol, ValidationError
from ..stream import AutoSeparatedStreamNetworkProtocol, _BaseAutoSeparatedPacket
from .generic import GenericNetworkProtocolWrapper

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
class EncryptorNetworkProtocol(
    _BaseEncryptor,
    GenericNetworkProtocolWrapper[_ST_contra, _DT_co],
    AutoSeparatedStreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(protocol=protocol, key=key)

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        return self.key.encrypt(self.protocol.serialize(packet))

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = self.key.decrypt(data)
        except InvalidToken as exc:
            raise ValidationError("Invalid token") from exc
        packet: _DT_co = self.protocol.deserialize(data)
        return packet
