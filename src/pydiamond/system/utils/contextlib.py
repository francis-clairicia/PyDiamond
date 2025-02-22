from __future__ import annotations

__all__ = ["ExitStackView", "dsuppress"]

import contextlib
from collections.abc import Callable
from types import TracebackType
from typing import Any

type _ExitFunc = Callable[[type[BaseException] | None, BaseException | None, TracebackType | None], bool | None]


class ExitStackView:
    __slots__ = ("__s", "__weakref__")

    def __init__(self, stack: contextlib.ExitStack) -> None:
        self.__s = stack

    def enter_context[_T](self, cm: contextlib.AbstractContextManager[_T]) -> _T:
        return self.__s.enter_context(cm)

    def push[_CM_EF: contextlib.AbstractAsyncContextManager[Any] | _ExitFunc](self, exit: _CM_EF) -> _CM_EF:
        return self.__s.push(exit)  # type: ignore[type-var]

    def callback[**_P, _T](self, __callback: Callable[_P, _T], /, *args: _P.args, **kwds: _P.kwargs) -> Callable[_P, _T]:
        return self.__s.callback(__callback, *args, **kwds)


class dsuppress(contextlib.suppress, contextlib.ContextDecorator):
    pass
