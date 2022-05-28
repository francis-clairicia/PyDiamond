# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""json-based network packet protocol module"""

__all__ = ["JSONNetworkProtocol"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from json import JSONDecodeError, JSONDecoder, JSONEncoder
from typing import Any

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import AutoParsedStreamNetworkProtocol, ValidationError


@concreteclass
class JSONNetworkProtocol(AutoParsedStreamNetworkProtocol):
    @final
    def serialize(self, packet: Any) -> bytes:
        encoder = self.get_encoder()
        return encoder.encode(packet).encode("utf-8")

    @final
    def deserialize(self, data: bytes) -> Any:
        decoder = self.get_decoder()
        try:
            return decoder.decode(data.decode("utf-8"))
        except (UnicodeDecodeError, JSONDecodeError) as exc:
            raise ValidationError("JSON decode error") from exc

    def get_encoder(self) -> JSONEncoder:
        return JSONEncoder(
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),  # Compact JSON (w/o whitespaces)
            default=None,
        )

    def get_decoder(self) -> JSONDecoder:
        return JSONDecoder(object_hook=None, object_pairs_hook=None, strict=True)
