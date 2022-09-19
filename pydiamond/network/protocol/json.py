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

from collections import Counter
from io import IOBase
from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import IO, Generator, Generic, TypeVar

from ...system.object import final
from ...system.utils.abc import concreteclass
from .abc import ValidationError
from .stream import (
    IncrementalDeserializeError,
    NetworkPacketIncrementalDeserializer,
    NetworkPacketIncrementalSerializer,
    StreamNetworkProtocol,
)

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


@concreteclass
class JSONPacketSerializer(NetworkPacketIncrementalSerializer[_ST_contra]):
    def __init__(self) -> None:
        super().__init__()

    @final
    def serialize(self, packet: _ST_contra) -> bytes:
        encoder = self.get_encoder()
        encoding: str = "ascii" if encoder.ensure_ascii else "utf-8"
        return encoder.encode(packet).encode(encoding)

    @final
    def incremental_serialize(self, packet: _ST_contra) -> Generator[bytes, None, None]:
        encoder = self.get_encoder()
        encoding: str = "ascii" if encoder.ensure_ascii else "utf-8"
        for chunk in encoder.iterencode(packet):
            yield chunk.encode(encoding)

    @final
    def incremental_serialize_to(self, file: IOBase | IO[bytes], packet: _ST_contra) -> None:
        return NetworkPacketIncrementalSerializer.incremental_serialize_to(self, file, packet)

    def get_encoder(self) -> JSONEncoder:
        return JSONEncoder(
            skipkeys=False,
            ensure_ascii=False,  # Unicode are accepted
            check_circular=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),  # Compact JSON (w/o whitespaces)
            default=None,
        )


@concreteclass
class JSONPacketDeserializer(NetworkPacketIncrementalDeserializer[_DT_co]):
    def __init__(self) -> None:
        super().__init__()

    @final
    def deserialize(self, data: bytes) -> _DT_co:
        try:
            document: str = data.decode(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise ValidationError("Unicode decode error") from exc
        decoder = self.get_decoder()
        try:
            packet: _DT_co = decoder.decode(document)
        except JSONDecodeError as exc:
            raise ValidationError("JSON decode error") from exc
        return packet

    @final
    def incremental_deserialize(self) -> Generator[None, bytes, tuple[_DT_co, bytes]]:
        import struct

        def escaped(partial_document: bytes) -> bool:
            return ((len(partial_document) - len(partial_document.rstrip(b"\\"))) % 2) == 1

        encoding: str = "utf-8"
        enclosure_counter: Counter[bytes] = Counter()
        partial_document: bytes = b""
        while True:
            complete_document: bytes = b""
            while not complete_document:
                if not partial_document:
                    enclosure_counter.clear()
                chunk: bytes = yield
                char: bytes
                for nb_chars, char in enumerate(struct.unpack(f"{len(chunk)}c", chunk), start=1):
                    match char:
                        case b'"' if not escaped(partial_document):
                            enclosure_counter[b'"'] = 0 if enclosure_counter[b'"'] == 1 else 1
                        case _ if enclosure_counter[b'"'] > 0:
                            partial_document += char
                            continue
                        case b"{" | b"[":
                            enclosure_counter[char] += 1
                        case b"}":
                            enclosure_counter[b"{"] -= 1
                        case b"]":
                            enclosure_counter[b"["] -= 1
                        case b" " | b"\t" | b"\n" | b"\r":  # Optimization: Skip spaces
                            continue
                        case _ if not enclosure_counter:  # No enclosure, only value
                            # Directly refused because we can't known when data is valid
                            raise IncrementalDeserializeError(
                                "Do not received beginning of a string/array/object",
                                data_with_error=chunk,
                                remaining_data=partial_document,
                            )
                    partial_document += char
                    if enclosure_counter[next(iter(enclosure_counter))] <= 0:  # 1st found is closed
                        complete_document = partial_document
                        partial_document = chunk[nb_chars:]
                        break
            decoder = self.get_decoder()
            packet: _DT_co
            try:
                document: str = complete_document.decode(encoding)
            except UnicodeDecodeError as exc:
                raise IncrementalDeserializeError(
                    f"Unicode decode error: {exc}",
                    data_with_error=complete_document,
                    remaining_data=partial_document,
                ) from exc
            try:
                packet, end = decoder.raw_decode(document)
            except JSONDecodeError as exc:
                raise IncrementalDeserializeError(
                    f"JSON decode error: {exc}",
                    data_with_error=complete_document,
                    remaining_data=partial_document,
                ) from exc
            return packet, (document[end:].encode(encoding) + partial_document).lstrip(b" \t\n\r")

    def get_decoder(self) -> JSONDecoder:
        return JSONDecoder(object_hook=None, object_pairs_hook=None, strict=True)


@concreteclass
class JSONNetworkProtocol(
    JSONPacketSerializer[_ST_contra],
    JSONPacketDeserializer[_DT_co],
    StreamNetworkProtocol[_ST_contra, _DT_co],
    Generic[_ST_contra, _DT_co],
):
    pass
