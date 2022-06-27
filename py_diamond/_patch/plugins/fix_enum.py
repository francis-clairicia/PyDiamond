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

        from enum import IntEnum

        for attr in ("__repr__", "__str__", "__format__"):
            setattr(IntEnum, attr, getattr(int, attr))
