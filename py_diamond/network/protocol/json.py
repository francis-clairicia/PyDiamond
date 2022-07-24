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

import re
from collections import Counter
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import IO, Generator, Generic, TypeVar

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import ValidationError
from .stream import NetworkPacketIncrementalDeserializer, NetworkPacketIncrementalSerializer, StreamNetworkProtocol

_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)

WHITESPACE: re.Pattern[str]
try:
    from json.decoder import WHITESPACE  # type: ignore[attr-defined,no-redef]
except ImportError:
    WHITESPACE = re.compile(r"[ \t\n\r]*", re.VERBOSE | re.MULTILINE | re.DOTALL)


@concreteclass
class JSONPacketSerializer(NetworkPacketIncrementalSerializer[_T_contra]):
    def __init__(self) -> None:
        super().__init__()

    @final
    def serialize(self, packet: _T_contra) -> bytes:
        serializer = self.get_json_serializer()
        return serializer.encode(packet).encode(self.get_encoding())

    @final
    def incremental_serialize(self, packet: _T_contra) -> Generator[bytes, None, None]:
        serializer = self.get_json_serializer()
        encoding: str = self.get_encoding()
        for chunk in serializer.iterencode(packet):
            yield chunk.encode(encoding)

    @final
    def incremental_serialize_to(self, file: IO[bytes], packet: _T_contra) -> None:
        return NetworkPacketIncrementalSerializer.incremental_serialize_to(self, file, packet)

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
class JSONPacketDeserializer(NetworkPacketIncrementalDeserializer[_T_co]):
    def __init__(self) -> None:
        super().__init__()

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

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_T_co, bytes]]:
        document: str = ""
        encoding: str = self.get_encoding()
        while True:
            try:
                document += (yield).decode(encoding)
            except UnicodeDecodeError:
                document = ""
                continue
            try:
                packet, end = self.raw_decode(document)
            except EOFError:
                continue
            except JSONDecodeError:
                document = ""
                continue
            return packet, document[end:].encode(encoding)

    def raw_decode(self, document: str) -> tuple[_T_co, int]:
        w = WHITESPACE.match
        counter: Counter[str] = Counter()

        start_idx: int = w(document, 0).end()  # type: ignore[union-attr]
        for index, char in enumerate(document[start_idx:]):
            match char:
                case '"' if index == 0 or document[start_idx + index - 1] != "\\":
                    counter['"'] = 0 if counter['"'] == 1 else 1
                case _ if counter['"'] > 0:
                    continue
                case "{" | "[":
                    counter[char] += 1
                case "}":
                    counter["{"] -= 1
                case "]":
                    counter["["] -= 1
                case _ if index == 0:
                    break
                case _:
                    continue
            if counter[next(iter(counter))] <= 0:
                break
        else:
            if counter:
                raise EOFError

        del counter

        deserializer = self.get_json_deserializer()
        packet: _T_co
        packet, end = deserializer.raw_decode(document, idx=start_idx)
        end = w(document, end).end()  # type: ignore[union-attr]
        return packet, end

    def get_json_deserializer(self) -> JSONDecoder:
        return JSONDecoder(object_hook=None, object_pairs_hook=None, strict=True)

    def get_encoding(self) -> str:
        return "utf-8"


@concreteclass
class JSONNetworkProtocol(
    JSONPacketSerializer[_T_contra],
    JSONPacketDeserializer[_T_co],
    StreamNetworkProtocol[_T_contra, _T_co],
    Generic[_T_contra, _T_co],
):
    pass
