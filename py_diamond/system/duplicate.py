# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""NoDuplicate objects module"""

from __future__ import annotations

__all__ = ["NoDuplicate", "NoDuplicateMeta"]


from typing import Any

from .non_copyable import NonCopyable, NonCopyableMeta
from .utils.functools import cache


class NoDuplicateMeta(NonCopyableMeta):
    @cache
    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        return super().__call__(*args, **kwargs)


class NoDuplicate(NonCopyable, metaclass=NoDuplicateMeta):
    __slots__ = ()
