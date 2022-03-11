# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Enum utility module"""

__all__ = ["AutoLowerNameEnum", "AutoUpperNameEnum", "StrEnum"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import Enum
from typing import Any, TypeVar

_StrEnumSelf = TypeVar("_StrEnumSelf", bound="StrEnum")


class StrEnum(str, Enum):
    value: str

    def __new__(cls: type[_StrEnumSelf], value: str | _StrEnumSelf) -> _StrEnumSelf:
        return super().__new__(cls, value)


class AutoLowerNameEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> Any:
        return name.lower()


class AutoUpperNameEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> Any:
        return name.upper()


del _StrEnumSelf
