# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Module for auto docstring assignment from overloads"""

from __future__ import annotations

__all__ = [
    "AutoOverloadDocStringDict",
    "AutoOverloadDocStringMeta",
    "overload",
]

from contextlib import suppress
from typing import TYPE_CHECKING, Any

from .object import ObjectMeta

if TYPE_CHECKING:
    from typing import overload
else:
    from typing import overload as _default_overload

    def overload(f: Any) -> Any:
        overload_f = _default_overload(f)
        if overload_f is not f:
            overload_f.__doc__ = f.__doc__
        return overload_f


def _apply_doc(f: Any, doc: str) -> None:
    with suppress(AttributeError, TypeError):
        f.__doc__ = doc
    if hasattr(f, "__wrapped__"):
        _apply_doc(getattr(f, "__wrapped__"), doc)


def _reset_overload_doc() -> None:
    overload(lambda: None).__doc__ = None


class AutoOverloadDocStringDict(dict[str, Any]):
    def __init__(self) -> None:
        super().__init__()
        self._overloaded_function_docstrings: dict[str, str | None] = {}

    def __setitem__(self, __k: str, __v: Any) -> None:
        super().__setitem__(__k, __v)
        overload_dict = self._overloaded_function_docstrings
        if __v is overload(__v):  # overload() always returns a singleton
            if __k not in overload_dict:  # First overload
                overload_dict[__k] = __v.__doc__
            elif __v.__doc__ is not None:  # Each overload has a docstring, couldn't determine which to choose
                overload_dict[__k] = None
        elif overload_dict.get(__k, None) is not None and __v.__doc__ is None:
            _apply_doc(__v, str(overload_dict[__k]))
        _reset_overload_doc()


class AutoOverloadDocStringMeta(ObjectMeta):
    @classmethod
    def __prepare__(cls, __name: str, __bases: tuple[type, ...], **kwds: Any) -> AutoOverloadDocStringDict:
        return AutoOverloadDocStringDict()
