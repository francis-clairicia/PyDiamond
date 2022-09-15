# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network socket module"""

from __future__ import annotations

__all__ = [
    "AF_INET",
    "AF_INET6",
    "AddressFamily",
    "SHUT_RD",
    "SHUT_RDWR",
    "SHUT_WR",
    "ShutdownFlag",
]

import socket
from enum import IntEnum, unique
from typing import Final, Literal


@unique
class AddressFamily(IntEnum):
    AF_INET = socket.AF_INET
    AF_INET6 = socket.AF_INET6

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"

    __str__ = __repr__


@unique
class ShutdownFlag(IntEnum):
    SHUT_RD = socket.SHUT_RD
    SHUT_RDWR = socket.SHUT_RDWR
    SHUT_WR = socket.SHUT_WR

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"

    __str__ = __repr__


AF_INET: Final[Literal[AddressFamily.AF_INET]] = AddressFamily.AF_INET
AF_INET6: Final[Literal[AddressFamily.AF_INET6]] = AddressFamily.AF_INET6
SHUT_RD: Final[Literal[ShutdownFlag.SHUT_RD]] = ShutdownFlag.SHUT_RD
SHUT_RDWR: Final[Literal[ShutdownFlag.SHUT_RDWR]] = ShutdownFlag.SHUT_RDWR
SHUT_WR: Final[Literal[ShutdownFlag.SHUT_WR]] = ShutdownFlag.SHUT_WR


del socket
