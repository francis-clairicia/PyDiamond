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
from types import TracebackType
from typing import TYPE_CHECKING, Any, final

from ...system.utils import cached_property_read_only as cached_property, concreteclass
from .base import AutoParsedNetworkProtocol

if not TYPE_CHECKING:
    from ...system.object import final as final


@concreteclass
class JSONNetworkProtocol(AutoParsedNetworkProtocol):
    @final
    def serialize(self, packet: Any) -> bytes:
        return self.encoder.encode(packet).encode("utf-8")

    @final
    def deserialize(self, data: bytes) -> Any:
        return self.decoder.decode(data.decode("utf-8"))

    def handle_deserialize_error(
        self, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        if issubclass(exc_type, JSONDecodeError):
            return True
        return super().handle_deserialize_error(data, exc_type, exc_value, tb)

    @cached_property
    def encoder(self) -> JSONEncoder:
        return JSONEncoder(
            skipkeys=False,
            ensure_ascii=True,
            check_circular=True,
            allow_nan=True,
            indent=None,
            separators=(",", ":"),  # Compact JSON (w/o whitespaces)
            default=None,
        )

    @cached_property
    def decoder(self) -> JSONDecoder:
        return JSONDecoder(object_hook=None, object_pairs_hook=None)
