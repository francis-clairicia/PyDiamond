# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Enum utility module"""

from __future__ import annotations

__all__ = ["AutoLowerNameEnum", "AutoUpperNameEnum", "StrEnum"]

import enum
from enum import StrEnum
from typing import Any

from ..object import ObjectMeta


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
