# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Weak references utility module"""

from __future__ import annotations

__all__ = ["weakref_unwrap"]


from typing import TypeVar
from weakref import ReferenceType

_T = TypeVar("_T")


def weakref_unwrap(ref: ReferenceType[_T]) -> _T:
    obj = ref()
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj
