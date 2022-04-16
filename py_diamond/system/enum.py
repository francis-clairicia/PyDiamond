# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Enum utility module"""

from __future__ import annotations

__all__ = ["AutoLowerNameEnum", "AutoUpperNameEnum", "StrEnum"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import sys
from enum import Enum
from typing import TYPE_CHECKING, Any

if sys.version_info >= (3, 11):
    from enum import StrEnum

else:

    if TYPE_CHECKING:
        from _typeshed import Self

    def __int_enum_monkeypatch() -> None:
        from enum import IntEnum

        setattr(IntEnum, "__str__", int.__str__)
        setattr(IntEnum, "__format__", int.__format__)

    __int_enum_monkeypatch()
    del __int_enum_monkeypatch

    class StrEnum(str, Enum):
        value: str

        if TYPE_CHECKING:

            def __new__(cls: type[Self], value: str | Self) -> Self:
                ...

        if not TYPE_CHECKING:

            __str__ = str.__str__
            __format__ = str.__format__


class AutoLowerNameEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> Any:
        return name.lower()


class AutoUpperNameEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> Any:
        return name.upper()
