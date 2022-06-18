# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Data compressor protocol module"""

from __future__ import annotations

__all__ = ["EncryptorProtocol"]


from typing import Any, TypeVar

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import AbstractNetworkProtocol, GenericNetworkProtocolWrapper, ValidationError
from .stream import AutoSeparatedStreamNetworkProtocol

_P = TypeVar("_P", bound=AbstractNetworkProtocol)


@concreteclass
class EncryptorProtocol(AutoSeparatedStreamNetworkProtocol, GenericNetworkProtocolWrapper[_P]):
    def __init__(self, protocol: _P, key: str | bytes | Fernet | MultiFernet) -> None:
        super().__init__(b"\r\n", keepends=False, protocol=protocol)
        if not isinstance(key, (Fernet, MultiFernet)):
            key = Fernet(key)
        self.__key: Fernet | MultiFernet = key

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    @final
    def serialize(self, packet: Any) -> bytes:
        return self.key.encrypt(self.protocol.serialize(packet))

    @final
    def deserialize(self, data: bytes) -> Any:
        try:
            data = self.key.decrypt(data)
        except InvalidToken as exc:
            raise ValidationError("Invalid token") from exc
        return self.protocol.deserialize(data)

    @property
    @final
    def key(self) -> Fernet | MultiFernet:
        return self.__key
