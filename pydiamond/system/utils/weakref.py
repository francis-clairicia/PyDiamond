# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Weak references utility module"""

from __future__ import annotations

__all__ = ["weakref_unwrap"]

from typing import Any, Callable, TypeVar, overload
from weakref import ReferenceType, WeakMethod

_T = TypeVar("_T")
_Func = TypeVar("_Func", bound=Callable[..., Any])


@overload
def weakref_unwrap(ref: ReferenceType[_T]) -> _T:
    ...


@overload
def weakref_unwrap(ref: WeakMethod[_Func]) -> _Func:
    ...


def weakref_unwrap(ref: Callable[[], _T | None]) -> _T:
    obj = ref()
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj
