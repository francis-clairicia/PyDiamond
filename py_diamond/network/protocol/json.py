# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""json-based network packet protocol module"""

from __future__ import annotations

__all__ = [
    "JSONNetworkProtocol",
    "JSONPacketDeserializer",
    "JSONPacketSerializer",
]

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Generic, TypeVar

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import ValidationError
from .stream import AutoParsedPacketDeserializer, AutoParsedPacketSerializer, AutoParsedStreamNetworkProtocol

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)


@concreteclass
class JSONPacketSerializer(AutoParsedPacketSerializer[_T_contra]):
    @final
    def serialize(self, packet: _T_contra) -> bytes:
        serializer = self.get_json_serializer()
        return serializer.encode(packet).encode(self.get_encoding())

    def get_json_serializer(self) -> JSONEncoder:
        return JSONEncoder(
            skipkeys=False,
            ensure_ascii=False,  # Unicode are accepted
            check_circular=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),  # Compact JSON (w/o whitespaces)
            default=None,
        )

    def get_encoding(self) -> str:
        return "utf-8"


@concreteclass
class JSONPacketDeserializer(AutoParsedPacketDeserializer[_T_co]):
    @final
    def deserialize(self, data: bytes) -> _T_co:
        try:
            document: str = data.decode(self.get_encoding())
        except UnicodeDecodeError as exc:
            raise ValidationError("Unicode decode error") from exc
        deserializer = self.get_json_deserializer()
        try:
            packet: _T_co = deserializer.decode(document)
        except JSONDecodeError as exc:
            raise ValidationError("JSON decode error") from exc
        return packet

    def get_json_deserializer(self) -> JSONDecoder:
        return JSONDecoder(object_hook=None, object_pairs_hook=None, strict=True)

    def get_encoding(self) -> str:
        return "utf-8"


@concreteclass
class JSONNetworkProtocol(
    JSONPacketSerializer[_T_contra],
    JSONPacketDeserializer[_T_co],
    AutoParsedStreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co],
):
    pass
