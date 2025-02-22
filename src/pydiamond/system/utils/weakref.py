# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Weak references utility module"""

from __future__ import annotations

__all__ = ["weakref_unwrap"]

from collections.abc import Callable
from typing import Any, overload
from weakref import ReferenceType, WeakMethod


@overload
def weakref_unwrap[_T](ref: ReferenceType[_T]) -> _T: ...


@overload
def weakref_unwrap[_T: Callable[..., Any]](ref: WeakMethod[_T]) -> _T: ...


def weakref_unwrap[_T](ref: Callable[[], _T | None]) -> _T:
    obj = ref()
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj
