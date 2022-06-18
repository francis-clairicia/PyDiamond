# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""json-based network packet protocol module"""

from __future__ import annotations

__all__ = ["JSONNetworkProtocol"]


from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import ValidationError
from .stream import AutoParsedStreamNetworkProtocol


@concreteclass
class JSONNetworkProtocol(AutoParsedStreamNetworkProtocol):
    @final
    def serialize(self, packet: Any) -> bytes:
        serializer = self.get_json_serializer()
        return serializer.encode(packet).encode(self.get_encoding())

    @final
    def deserialize(self, data: bytes) -> Any:
        try:
            document: str = data.decode(self.get_encoding())
        except UnicodeDecodeError as exc:
            raise ValidationError("Unicode decode error") from exc
        deserializer = self.get_json_deserializer()
        try:
            return deserializer.decode(document)
        except JSONDecodeError as exc:
            raise ValidationError("JSON decode error") from exc

    def get_json_serializer(self) -> JSONEncoder:
        return JSONEncoder(
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),  # Compact JSON (w/o whitespaces)
            default=None,
        )

    def get_json_deserializer(self) -> JSONDecoder:
        return JSONDecoder(object_hook=None, object_pairs_hook=None, strict=True)

    def get_encoding(self) -> str:
        return "utf-8"
