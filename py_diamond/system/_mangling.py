# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Python mangling module"""

__all__ = ["mangle_private_attribute", "delattr_pv", "getattr_pv", "setattr_pv"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from typing import Any, TypeVar, overload

_T = TypeVar("_T")

_NO_DEFAULT: Any = object()


def mangle_private_attribute(cls: type, attribute: str) -> str:
    return f"_{cls.__name__.strip('_')}__{attribute}"


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
    if default is _NO_DEFAULT:
        return getattr(obj, attribute)
    return getattr(obj, attribute, default)


def setattr_pv(obj: object, attribute: str, value: Any, *, owner: type | None = None) -> None:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    attribute = mangle_private_attribute(owner, attribute)
    return setattr(obj, attribute, value)


def delattr_pv(obj: object, attribute: str, *, owner: type | None = None) -> None:
    if owner is None:
        if isinstance(obj, type):
            owner = obj
        else:
            owner = type(obj)
    attribute = mangle_private_attribute(owner, attribute)
    return delattr(obj, attribute)
