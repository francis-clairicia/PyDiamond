# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

from __future__ import annotations

__all__ = []  # type: list[str]

import os
import sys
from functools import cached_property, partialmethod, update_wrapper
from typing import TYPE_CHECKING, Any, Callable

from .._base import BasePatch

if TYPE_CHECKING:
    from types import ModuleType


class OverrideFinalFunctionsPatch(BasePatch):
    def setup(self) -> None:
        super().setup()

        if sys.version_info < (3, 11):
            from typing_extensions import final as _default_final

        else:
            from typing import final as _default_final

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
        def patch_final(f: Any, /) -> Any:
            if os.environ.get("PYDIAMOND_TEST_STRICT_FINAL", "0") != "0":
                if type(f) in (property, classmethod, staticmethod, cached_property, partialmethod):
                    # yes this specially for these classes, do not include subclasses !
                    raise TypeError(f"final() call forbidden for {type(f).__name__!r} objects")
            match f:
                case property(fget=fget, fset=fset, fdel=fdel):
                    for method in filter(callable, (fget, fset, fdel)):
                        patch_final(method)
                case (
                    classmethod(__func__=func)
                    | staticmethod(__func__=func)
                    | cached_property(func=func)
                    | partialmethod(func=func)
                ):
                    patch_final(func)
            return default_final(f)

        setattr(patch_final, "__fix_typing__", True)
        setattr(patch_final, "__default_final__", default_final)
        return patch_final
