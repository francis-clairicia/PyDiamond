# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Python mangling module"""

from __future__ import annotations

__all__ = [
    "delattr_pv",
    "getattr_pv",
    "hasattr_pv",
    "mangle_private_attribute",
    "setattr_pv",
    "setdefaultattr_pv",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from typing import Any, TypeVar, overload

from .functools import cache

_T = TypeVar("_T")

_NO_DEFAULT: Any = object()


@cache
def mangle_private_attribute(cls: type, name: str) -> str:
    if not name:
        raise ValueError(f"Empty attribute string")
    if all(c == "_" for c in name):
        raise ValueError(f"attribute filled with underscores")
    if name.endswith("__"):
        raise ValueError(f"{name!r}: Two or more trailing underscores")
    return f"_{cls.__name__.strip('_')}__{name}"


def hasattr_pv(obj: object, name: str, *, owner: type | None = None) -> bool:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    name = mangle_private_attribute(owner, name)
    try:
        return hasattr(obj, name)
    except AttributeError as exc:
        raise AttributeError(f"Error when checking private attribute {name!r}: {exc}") from None


@overload
def getattr_pv(obj: object, name: str, *, owner: type | None = None) -> Any:
    ...


@overload
def getattr_pv(obj: object, name: str, default: _T, *, owner: type | None = None) -> Any | _T:
    ...


def getattr_pv(obj: object, name: str, default: Any = _NO_DEFAULT, *, owner: type | None = None) -> Any:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    name = mangle_private_attribute(owner, name)
    try:
        if default is not _NO_DEFAULT:
            return getattr(obj, name, default)
        return getattr(obj, name)
    except AttributeError:
        raise AttributeError(f"Missing private attribute {name!r}") from None


def setattr_pv(obj: object, name: str, value: Any, *, owner: type | None = None) -> None:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    name = mangle_private_attribute(owner, name)
    try:
        return setattr(obj, name, value)
    except AttributeError as exc:
        raise AttributeError(f"Error when setting private attribute {name!r}: {exc}") from None


def delattr_pv(obj: object, name: str, *, owner: type | None = None) -> None:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    name = mangle_private_attribute(owner, name)
    try:
        return delattr(obj, name)
    except AttributeError:
        raise AttributeError(f"Missing private attribute {name!r}") from None


def setdefaultattr_pv(obj: object, name: str, value: _T, *, owner: type | None = None) -> Any | _T:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    name = mangle_private_attribute(owner, name)
    try:
        return getattr(obj, name)
    except AttributeError:
        try:
            setattr(obj, name, value)
        except AttributeError as exc:
            raise AttributeError(f"Error when setting private attribute {name!r}: {exc}") from None
    return value
