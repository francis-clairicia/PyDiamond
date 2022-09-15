# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Enum utility module"""

from __future__ import annotations

__all__ = ["AutoLowerNameEnum", "AutoUpperNameEnum", "StrEnum"]


import enum
import sys
from typing import TYPE_CHECKING, Any

from .object import ObjectMeta

if sys.version_info < (3, 11):
    if TYPE_CHECKING:
        from _typeshed import Self

    class StrEnum(str, enum.Enum):

        if TYPE_CHECKING:

            def __new__(cls: type[Self], value: str | Self) -> Self:
                ...

            @property
            def value(self) -> str:
                ...

else:

    from enum import StrEnum


class AutoLowerNameEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> Any:
        return name.lower()


class AutoUpperNameEnum(StrEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[str]) -> Any:
        return name.upper()


class EnumObjectMeta(ObjectMeta, enum.EnumMeta):
    pass
