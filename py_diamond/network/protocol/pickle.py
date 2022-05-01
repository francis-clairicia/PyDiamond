# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pickle-based network packet protocol module"""

__all__ = ["PicklingNetworkProtocol"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from io import BytesIO
from pickle import HIGHEST_PROTOCOL, STOP as STOP_OPCODE, Pickler, Unpickler, UnpicklingError
from pickletools import optimize as pickletools_optimize
from types import TracebackType
from typing import IO, Any, Generator

from ...system.object import final
from ...system.utils import concreteclass
from .base import AbstractNetworkProtocol, ValidationError


@concreteclass
class PicklingNetworkProtocol(AbstractNetworkProtocol):
    @final
    def serialize(self, packet: Any) -> bytes:
        buffer = BytesIO()
        pickler = self.get_pickler(buffer)
        pickler.dump(packet)
        return pickletools_optimize(buffer.getvalue())

    @final
    def deserialize(self, data: bytes) -> Any:
        buffer = BytesIO(data)
        unpickler = self.get_unpickler(buffer)
        return unpickler.load()

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

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        return Pickler(buffer, protocol=HIGHEST_PROTOCOL, fix_imports=True, buffer_callback=None)

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        return Unpickler(buffer, fix_imports=True, encoding="utf-8", errors="strict", buffers=None)
