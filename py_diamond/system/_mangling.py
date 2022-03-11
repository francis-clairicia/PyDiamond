# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Python mangling module"""

__all__ = ["delattr_pv", "getattr_pv", "hasattr_pv", "mangle_private_attribute", "setattr_pv", "setdefaultattr_pv"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from typing import Any, TypeVar, overload

_T = TypeVar("_T")

_NO_DEFAULT: Any = object()


def mangle_private_attribute(cls: type, attribute: str) -> str:
    if not isinstance(cls, type):
        raise TypeError("'cls' must be a type")
    if not attribute:
        raise ValueError(f"Empty attribute string")
    if all(c == "_" for c in attribute):
        raise ValueError(f"attribute filled with underscores")
    if attribute.endswith("__"):
        raise ValueError(f"{attribute!r}: Two or more trailing underscores")
    return f"_{cls.__name__.strip('_')}__{attribute}"


def hasattr_pv(obj: object, attribute: str, *, owner: type | None = None) -> bool:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    attribute = mangle_private_attribute(owner, attribute)
    try:
        return hasattr(obj, attribute)
    except AttributeError as exc:
        raise AttributeError(f"Error when checking private attribute {attribute!r}: {exc}") from None


@overload
def getattr_pv(obj: object, attribute: str, *, owner: type | None = None) -> Any:
    ...


@overload
def getattr_pv(obj: object, attribute: str, default: _T, *, owner: type | None = None) -> Any | _T:
    ...


def getattr_pv(obj: object, attribute: str, default: Any = _NO_DEFAULT, *, owner: type | None = None) -> Any:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    attribute = mangle_private_attribute(owner, attribute)
    try:
        if default is not _NO_DEFAULT:
            return getattr(obj, attribute, default)
        return getattr(obj, attribute)
    except AttributeError:
        raise AttributeError(f"Missing private attribute {attribute!r}") from None


def setattr_pv(obj: object, attribute: str, value: Any, *, owner: type | None = None) -> None:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    attribute = mangle_private_attribute(owner, attribute)
    try:
        return setattr(obj, attribute, value)
    except AttributeError as exc:
        raise AttributeError(f"Error when setting private attribute {attribute!r}: {exc}") from None


def delattr_pv(obj: object, attribute: str, *, owner: type | None = None) -> None:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    attribute = mangle_private_attribute(owner, attribute)
    try:
        return delattr(obj, attribute)
    except AttributeError:
        raise AttributeError(f"Missing private attribute {attribute!r}") from None


def setdefaultattr_pv(obj: object, name: str, value: _T, *, owner: type | None = None) -> _T:
    try:
        return getattr_pv(obj, name, owner=owner)  # type: ignore[no-any-return]
    except AttributeError:
        setattr_pv(obj, name, value, owner=owner)
    return value


del _T
