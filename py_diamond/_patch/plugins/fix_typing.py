# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

from __future__ import annotations

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


import sys
from functools import cached_property, update_wrapper
from typing import TYPE_CHECKING, Any, Callable, TypeVar

from .._base import BasePatch

if TYPE_CHECKING:
    from types import ModuleType

_T = TypeVar("_T")


class OverrideFinalFunctionsPatch(BasePatch):
    def setup(self) -> None:
        super().setup()

        if sys.version_info >= (3, 11):
            from typing import final as _default_final

        else:
            from typing_extensions import final as _default_final

        self.__default_final = _default_final

    def teardown(self) -> None:
        del self.__default_final
        return super().teardown()

    def run(self) -> None:
        import typing

        import typing_extensions

        self._apply_patch_on_module(typing)
        self._apply_patch_on_module(typing_extensions)

    def _apply_patch_on_module(self, module: ModuleType) -> None:
        _final = getattr(module, "final")
        if not self._already_patched(_final):
            patch_final = self._compute_patch_function(self.__default_final)
            setattr(module, "final", update_wrapper(patch_final, wrapped=_final))

    @staticmethod
    def _already_patched(func: Any) -> bool:
        return True if getattr(func, "__fix_typing__", False) else False

    @staticmethod
    def _compute_patch_function(default_final: Callable[[Any], Any]) -> Callable[[Any], Any]:
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
            return default_final(f)  # type: ignore[no-any-return]

        setattr(patch_final, "__fix_typing__", True)
        return patch_final
