# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Iteration utility module"""

from __future__ import annotations

__all__ = ["flatten"]


from itertools import chain
from typing import Any, Iterable, Iterator, Literal as L, TypeVar, overload

_T = TypeVar("_T")


@overload
def flatten(iterable: Iterable[Iterable[_T]]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[_T]], *, level: L[1]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[_T]]], *, level: L[2]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[Iterable[_T]]]], *, level: L[3]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[Iterable[Iterable[_T]]]]], *, level: L[4]) -> Iterator[_T]:
    ...


def flatten(iterable: Any, *, level: int = 1) -> Iterator[Any]:
    if level == 1:
        return chain.from_iterable(iterable)
    if not (2 <= level <= 4):
        raise ValueError("'level' must be in [1;4]")
    return (elem for it in iterable for elem in flatten(it, level=level - 1))  # type: ignore[call-overload]
