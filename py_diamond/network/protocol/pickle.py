# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pickle-based network packet protocol module"""

from __future__ import annotations

__all__ = ["PicklingNetworkProtocol"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from io import BufferedReader, BytesIO
from pickle import HIGHEST_PROTOCOL, STOP as STOP_OPCODE, Pickler, Unpickler, UnpicklingError
from pickletools import optimize as pickletools_optimize
from typing import IO, Any, Generator

from ...system.object import final
from ...system.utils.abc import concreteclass
from .base import AbstractStreamNetworkProtocol, ValidationError


@concreteclass
class PicklingNetworkProtocol(AbstractStreamNetworkProtocol):
    @final
    def serialize(self, packet: Any) -> bytes:
        buffer = BytesIO()
        pickler = self.get_pickler(buffer)
        pickler.dump(packet)
        return pickletools_optimize(buffer.getvalue())

    @final
    def deserialize(self, data: bytes) -> Any:
        if STOP_OPCODE not in data:
            raise ValidationError("Missing 'STOP' pickle opcode in data")
        buffer = BytesIO(data)
        unpickler = self.get_unpickler(buffer)
        try:
            return unpickler.load()
        except UnpicklingError as exc:
            raise ValidationError("Unpickling error") from exc

    def parse_received_data(self, buffer: BufferedReader) -> Generator[bytes, None, None]:
        data = BytesIO()
        while chunk := buffer.peek(4096):
            if (idx := chunk.find(STOP_OPCODE)) < 0:
                data.write(buffer.read(4096))
                continue
            data.write(buffer.read(idx + len(STOP_OPCODE)))
            data.flush()
            yield data.getvalue()
            # As we can't delete underlying bytes, we recreate a new empty BytesIO object
            data.close()
            data = BytesIO()

    def get_pickler(self, buffer: IO[bytes]) -> Pickler:
        return Pickler(buffer, protocol=HIGHEST_PROTOCOL, fix_imports=False, buffer_callback=None)

    def get_unpickler(self, buffer: IO[bytes]) -> Unpickler:
        return Unpickler(buffer, fix_imports=False, encoding="utf-8", errors="strict", buffers=None)
