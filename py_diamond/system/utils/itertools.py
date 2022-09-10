# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Iteration utility module"""

from __future__ import annotations

__all__ = ["consume", "consumer_start", "flatten", "next_return", "prepend", "send_return"]

import inspect
from collections import deque
from itertools import chain
from typing import Any, Generator, Iterable, Iterator, Literal, TypeVar, overload

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)
_T_contra = TypeVar("_T_contra", contravariant=True)
_V_co = TypeVar("_V_co", covariant=True)
_NO_DEFAULT: Any = object()


def consumer_start(gen: Generator[_T_co, Any, Any], /) -> _T_co:
    if inspect.getgeneratorstate(gen) != "GEN_CREATED":
        raise RuntimeError("generator already started")
    try:
        return next(gen)
    except StopIteration as exc:
        raise RuntimeError("generator didn't yield") from exc


def consume(it: Iterator[Any], /) -> None:
    deque(it, maxlen=0)  # Consume iterator at C level


@overload
def next_return(gen: Generator[Any, None, _V_co], /) -> _V_co:
    ...


@overload
def next_return(gen: Generator[Any, None, _V_co], default: _T, /) -> _V_co | _T:
    ...


def next_return(gen: Generator[Any, None, Any], default: Any = _NO_DEFAULT) -> Any:
    if inspect.getgeneratorstate(gen) == "GEN_CLOSED":
        raise RuntimeError("generator closed")
    try:
        value = next(gen)
    except StopIteration as exc:
        return exc.value
    if default is not _NO_DEFAULT:
        return default
    raise StopIteration(value)


def send_return(gen: Generator[Any, _T_contra, _V_co], value: _T_contra, /) -> _V_co:
    if inspect.getgeneratorstate(gen) == "GEN_CLOSED":
        raise RuntimeError("generator closed")
    try:
        send_value = gen.send(value)
    except StopIteration as exc:
        return exc.value
    raise StopIteration(send_value)


@overload
def flatten(iterable: Iterable[Iterable[_T]]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[_T]], *, level: Literal[1]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[_T]]], *, level: Literal[2]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[Iterable[_T]]]], *, level: Literal[3]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[Iterable[Iterable[_T]]]]], *, level: Literal[4]) -> Iterator[_T]:
    ...


def flatten(iterable: Any, *, level: int = 1) -> Iterator[Any]:
    if level == 1:
        return chain.from_iterable(iterable)
    if not (2 <= level <= 4):
        raise ValueError("'level' must be in [1;4]")
    return (elem for it in iterable for elem in flatten(it, level=level - 1))  # type: ignore[call-overload]


def prepend(obj: _T, iterable: Iterable[_T]) -> Iterator[_T]:
    return chain((obj,), iterable)
