# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Iteration utility module"""

from __future__ import annotations

__all__ = ["consume", "consumer_start", "flatten"]

import inspect
from collections import deque
from itertools import chain
from typing import Any, Generator, Iterable, Iterator, Literal as L, TypeVar, overload

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)


def consumer_start(gen: Generator[_T_co, Any, Any]) -> _T_co:
    if inspect.getgeneratorstate(gen) != "GEN_CREATED":
        raise RuntimeError("generator already started")
    try:
        return next(gen)
    except StopIteration as exc:
        raise RuntimeError("generator didn't yield") from exc


def consume(it: Iterator[Any]) -> None:
    deque(it, maxlen=0)  # Consume iterator at C level


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
