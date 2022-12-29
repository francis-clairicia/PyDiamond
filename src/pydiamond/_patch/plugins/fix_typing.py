# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

from __future__ import annotations

__all__ = []  # type: list[str]

import sys
from typing import Any

from .._base import BasePatch


class OverrideFinalFunctionPatch(BasePatch):
    def run(self) -> None:
        if sys.version_info < (3, 11):
            import typing

            try:
                import typing_extensions
            except ImportError:
                setattr(typing, "final", OverrideFinalFunctionPatch.final)
            else:
                setattr(typing, "final", typing_extensions.final)

    @staticmethod
    def final(f: Any) -> Any:
        try:
            f.__final__ = True
        except (AttributeError, TypeError):
            # Skip the attribute silently if it is not writable.
            # AttributeError happens if the object has __slots__ or a
            # read-only property, TypeError if it's a builtin class.
            pass
        return f
