# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""NonCopyable objects module"""

__all__ = ["MetaNonCopyable", "NonCopyable"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Any, TypeVar


def __non_copyable_copy__(self: Any) -> Any:
    raise TypeError("Non copyable class")


def __non_copyable_deepcopy__(self: Any, memo: dict[int, Any]) -> Any:
    raise TypeError("Non copyable class")


class MetaNonCopyable(type):
    __Self = TypeVar("__Self", bound="MetaNonCopyable")

    def __new__(
        metacls: type[__Self],
        /,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> __Self:
        if any(attr in namespace for attr in ["__copy__", "__deepcopy__"]):
            raise TypeError("'__copy__' and '__deepcopy__' cannot be overriden from a non-copyable object")
        namespace["__copy__"] = __non_copyable_copy__
        namespace["__deepcopy__"] = __non_copyable_deepcopy__
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ["__copy__", "__deepcopy__"]:
            raise TypeError(f"Cannot override {name!r} method")
        return super().__setattr__(name, value)

    del __Self


class NonCopyable(metaclass=MetaNonCopyable):
    pass
