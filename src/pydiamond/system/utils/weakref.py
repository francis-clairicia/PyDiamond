# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Weak references utility module"""

from __future__ import annotations

__all__ = ["weakref_unwrap"]

from collections.abc import Callable
from typing import Any, TypeVar, overload
from weakref import ReferenceType, WeakMethod

_T = TypeVar("_T")
_Func = TypeVar("_Func", bound=Callable[..., Any])


@overload
def weakref_unwrap(ref: ReferenceType[_T]) -> _T: ...


@overload
def weakref_unwrap(ref: WeakMethod[_Func]) -> _Func: ...


def weakref_unwrap(ref: Callable[[], _T | None]) -> _T:
    obj = ref()
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj
