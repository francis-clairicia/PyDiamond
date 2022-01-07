# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Enum utility module"""

__all__ = ["AutoLowerNameEnum", "AutoUpperNameEnum", "StrEnum"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import Enum
from typing import Any


class StrEnum(str, Enum):
    value: str


class AutoLowerNameEnum(StrEnum):
    def _generate_next_value_(name: str, *args: Any) -> Any:  # type: ignore[override]
        return name.lower()


class AutoUpperNameEnum(StrEnum):
    def _generate_next_value_(name: str, *args: Any) -> Any:  # type: ignore[override]
        return name.upper()
