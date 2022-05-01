# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


import sys
from functools import cached_property
from typing import TypeVar

_T = TypeVar("_T")


if sys.version_info >= (3, 11):
    from typing import final as _default_final

else:
    from typing_extensions import final as _default_final


def patch_final(f: _T, /) -> _T:
    if isinstance(f, property):
        for func in (f.fget, f.fset, f.fdel):
            if callable(func):
                patch_final(func)
        return f  # type: ignore[return-value]
    if isinstance(f, (classmethod, staticmethod)):
        patch_final(f.__func__)
    if isinstance(f, cached_property):
        patch_final(f.func)
    return _default_final(f)  # type: ignore[no-any-return]


setattr(patch_final, "__fix_typing__", True)


def plugin__override_final_function() -> None:

    import typing

    import typing_extensions

    if not getattr(typing.final, "__fix_typing__", False):
        setattr(typing, "final", patch_final)
    if not getattr(typing_extensions.final, "__fix_typing__", False):
        setattr(typing_extensions, "final", patch_final)
