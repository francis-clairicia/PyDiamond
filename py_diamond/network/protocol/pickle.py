# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pickle-based network packet protocol module"""

__all__ = ["PicklingNetworkProtocol"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from pickle import HIGHEST_PROTOCOL, STOP as STOP_OPCODE, UnpicklingError, dumps as pickle_dumps, loads as pickle_loads
from pickletools import optimize as pickletools_optimize
from types import TracebackType
from typing import Any, Generator

from ...system.utils import concreteclass
from .base import AbstractNetworkProtocol, ValidationError


@concreteclass
class PicklingNetworkProtocol(AbstractNetworkProtocol):
    def serialize(self, packet: Any) -> bytes:
        return pickletools_optimize(pickle_dumps(packet, protocol=self.get_pickler_dump_protocol()))

    def deserialize(self, data: bytes) -> Any:
        return pickle_loads(data)

    def parse_received_data(self, buffer: bytes) -> Generator[bytes, None, bytes]:
        while (idx := buffer.find(STOP_OPCODE)) >= 0:
            idx += len(STOP_OPCODE)
            yield buffer[:idx]
            buffer = buffer[idx:]
        return buffer

    def verify_received_data(self, data: bytes) -> None:
        super().verify_received_data(data)
        if STOP_OPCODE not in data:
            raise ValidationError("Missing 'STOP' pickle opcode in data")

    def handle_deserialize_error(
        self, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        if issubclass(exc_type, UnpicklingError):
            return True
        return super().handle_deserialize_error(data, exc_type, exc_value, tb)

    def get_pickler_dump_protocol(self) -> int:
        return HIGHEST_PROTOCOL
