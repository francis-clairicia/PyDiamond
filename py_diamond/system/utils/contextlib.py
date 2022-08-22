# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["ExitStackView"]

import contextlib
from types import TracebackType
from typing import Any, Callable, ParamSpec, TypeAlias, TypeVar

_P = ParamSpec("_P")
_T = TypeVar("_T")

_ExitFunc: TypeAlias = Callable[[type[BaseException] | None, BaseException | None, TracebackType | None], bool | None]
_CM_EF = TypeVar("_CM_EF", bound=contextlib.AbstractAsyncContextManager[Any] | _ExitFunc)


class ExitStackView:
    __slots__ = ("__s",)

    def __init__(self, stack: contextlib.ExitStack) -> None:
        self.__s = stack

    def enter_context(self, cm: contextlib.AbstractContextManager[_T]) -> _T:
        return self.__s.enter_context(cm)

    def push(self, exit: _CM_EF) -> _CM_EF:
        return self.__s.push(exit)  # type: ignore[type-var]

    def callback(self, __callback: Callable[_P, _T], *args: _P.args, **kwds: _P.kwargs) -> Callable[_P, _T]:
        return self.__s.callback(__callback, *args, **kwds)
