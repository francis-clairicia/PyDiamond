# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""json-based network packet protocol module"""

__all__ = ["JSONNetworkProtocol"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from json import JSONDecodeError, dumps as json_dumps, loads as json_loads
from types import TracebackType
from typing import Any, ClassVar

from ...system.utils import concreteclass
from .base import AutoParsedNetworkProtocol


@concreteclass
class JSONNetworkProtocol(AutoParsedNetworkProtocol):
    SEPARATOR: ClassVar[bytes] = b"\0"

    @classmethod
    def serialize(cls, packet: Any) -> bytes:
        return json_dumps(packet).encode("utf-8")

    @classmethod
    def deserialize(cls, data: bytes) -> Any:
        return json_loads(data.decode("utf-8"))

    @classmethod
    def handle_deserialize_error(
        cls, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        if issubclass(exc_type, JSONDecodeError):
            return True
        return super().handle_deserialize_error(data, exc_type, exc_value, tb)
