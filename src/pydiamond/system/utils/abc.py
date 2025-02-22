# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract classes utility module"""

from __future__ import annotations

__all__ = [
    "concreteclass",
    "concreteclassmethod",
    "isabstractclass",
    "isabstractmethod",
]

from collections.abc import Callable
from functools import wraps
from inspect import isabstract as isabstractclass
from typing import Any, Concatenate


def concreteclassmethod[_T: type, **_P, _R](func: Callable[Concatenate[_T, _P], _R]) -> Callable[Concatenate[_T, _P], _R]:
    @wraps(func)
    def wrapper(cls: _T, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        concreteclass(cls)
        return func(cls, *args, **kwargs)

    return wrapper


def concreteclass[_T: type](cls: _T) -> _T:
    if not isinstance(cls, type):
        raise TypeError("'cls' must be a type")
    if isabstractclass(cls):
        abstractmethods: Any = getattr(cls, "__abstractmethods__", set())
        raise TypeError(f"{cls.__name__} is an abstract class (abstract methods: {', '.join(abstractmethods)})")
    return cls


def isabstractmethod(func: Any) -> bool:
    return bool(getattr(func, "__isabstractmethod__", False))
