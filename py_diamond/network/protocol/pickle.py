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
    @classmethod
    def serialize(cls, packet: Any) -> bytes:
        return pickletools_optimize(pickle_dumps(packet, protocol=cls.get_pickle_dump_protocol()))

    @classmethod
    def deserialize(cls, data: bytes) -> Any:
        return pickle_loads(data)

    @classmethod
    def parse_received_data(cls, buffer: bytes) -> Generator[bytes, None, bytes]:
        while (idx := buffer.find(STOP_OPCODE)) >= 0:
            yield buffer[: idx + len(STOP_OPCODE)]
            buffer = buffer[idx + len(STOP_OPCODE) :]
        return buffer

    @classmethod
    def verify_received_data(cls, data: bytes) -> None:
        super().verify_received_data(data)
        if STOP_OPCODE not in data:
            raise ValidationError("Missing 'STOP' pickle opcode in data")

    @classmethod
    def handle_deserialize_error(
        cls, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        if issubclass(exc_type, UnpicklingError):
            return True
        return super().handle_deserialize_error(data, exc_type, exc_value, tb)

    @classmethod
    def get_pickle_dump_protocol(cls) -> int:
        return HIGHEST_PROTOCOL
