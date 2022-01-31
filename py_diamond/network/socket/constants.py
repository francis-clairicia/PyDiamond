# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
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
    "SOCK_DGRAM",
    "SOCK_STREAM",
    "ShutdownFlag",
    "SocketKind",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import socket
from enum import IntEnum, unique
from typing import Final, Literal


@unique
class AddressFamily(IntEnum):
    AF_INET = socket.AF_INET
    AF_INET6 = socket.AF_INET6

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


@unique
class SocketKind(IntEnum):
    SOCK_DGRAM = socket.SOCK_DGRAM
    SOCK_STREAM = socket.SOCK_STREAM

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


@unique
class ShutdownFlag(IntEnum):
    SHUT_RD = socket.SHUT_RD
    SHUT_RDWR = socket.SHUT_RDWR
    SHUT_WR = socket.SHUT_WR

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


AF_INET: Final[Literal[AddressFamily.AF_INET]] = AddressFamily.AF_INET
AF_INET6: Final[Literal[AddressFamily.AF_INET6]] = AddressFamily.AF_INET6
SOCK_DGRAM: Final[Literal[SocketKind.SOCK_DGRAM]] = SocketKind.SOCK_DGRAM
SOCK_STREAM: Final[Literal[SocketKind.SOCK_STREAM]] = SocketKind.SOCK_STREAM
SHUT_RD: Final[Literal[ShutdownFlag.SHUT_RD]] = ShutdownFlag.SHUT_RD
SHUT_RDWR: Final[Literal[ShutdownFlag.SHUT_RDWR]] = ShutdownFlag.SHUT_RDWR
SHUT_WR: Final[Literal[ShutdownFlag.SHUT_WR]] = ShutdownFlag.SHUT_WR


del socket
