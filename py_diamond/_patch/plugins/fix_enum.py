# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

from __future__ import annotations

__all__ = []  # type: list[str]

import sys

from .._base import BasePatch


class IntEnumMonkeyPatch(BasePatch):
    def run(self) -> None:
        if sys.version_info >= (3, 11):
            return

        from enum import IntEnum, IntFlag

        for attr in ("__str__", "__format__"):
            for enum_cls in (IntEnum, IntFlag):
                setattr(enum_cls, attr, getattr(int, attr))
