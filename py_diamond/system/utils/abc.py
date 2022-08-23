# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract classes utility module"""

from __future__ import annotations

__all__ = [
    "concreteclass",
    "concreteclasscheck",
    "concreteclassmethod",
    "isabstractclass",
    "isabstractmethod",
    "isconcreteclass",
]

from functools import wraps
from inspect import isabstract as isabstractclass
from typing import Any, Callable, Concatenate, ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")

_TT = TypeVar("_TT", bound=type)


def concreteclassmethod(func: Callable[Concatenate[_TT, _P], _R]) -> Callable[Concatenate[_TT, _P], _R]:
    @wraps(func)
    def wrapper(cls: _TT, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        concreteclasscheck(cls)
        return func(cls, *args, **kwargs)

    return wrapper


def concreteclass(cls: _TT) -> _TT:
    concreteclasscheck(cls)
    return cls


def concreteclasscheck(cls: Any) -> None:
    if not isinstance(cls, type):
        raise TypeError("'cls' must be a type")
    if not isconcreteclass(cls):
        abstractmethods: Any = getattr(cls, "__abstractmethods__")
        raise TypeError(f"{cls.__name__} is an abstract class (abstract methods: {', '.join(abstractmethods)})")


def isconcreteclass(cls: type) -> bool:
    return not isabstractclass(cls)


def isabstractmethod(func: Any) -> bool:
    return bool(getattr(func, "__isabstractmethod__", False))
