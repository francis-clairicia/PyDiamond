# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

from __future__ import annotations

__all__ = ["EncryptorNetworkProtocol"]

from typing import TypeVar

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from typing_extensions import assert_never

from ....system.object import final
from ....system.utils.abc import concreteclass
from ..abc import NetworkProtocol, ValidationError
from ..stream.abc import AutoSeparatedStreamNetworkProtocol

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@concreteclass
class EncryptorNetworkProtocol(AutoSeparatedStreamNetworkProtocol[_ST_contra, _DT_co]):
    __slots__ = ("__key", "__ttl", "__protocol")

    def __init__(
        self,
        protocol: NetworkProtocol[_ST_contra, _DT_co],
        key: str | bytes | Fernet | MultiFernet,
        ttl: int | None = None,
    ) -> None:
        super().__init__(separator=b"\r\n", keepends=False)
        self.__protocol: NetworkProtocol[_ST_contra, _DT_co] = protocol
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
        self.__ttl: int | None = ttl

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        return self.__key.encrypt(self.__protocol.serialize(packet))

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            data = self.__key.decrypt(data, self.__ttl)
        except InvalidToken as exc:
            raise ValidationError("Invalid token") from exc
        return self.__protocol.deserialize(data)

    @property
    @final
    def key(self) -> MultiFernet:
        return self.__key

    @property
    @final
    def ttl(self) -> int | None:
        return self.__ttl

    @property
    def protocol(self) -> NetworkProtocol[_ST_contra, _DT_co]:
        return self.__protocol
