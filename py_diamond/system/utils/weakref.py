# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Weak references utility module"""

from __future__ import annotations

__all__ = ["weakref_unwrap"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TypeVar
from weakref import ReferenceType as WeakReferenceType

_T = TypeVar("_T")


def weakref_unwrap(ref: WeakReferenceType[_T]) -> _T:
    obj = ref()
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj
