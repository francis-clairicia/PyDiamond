# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Threading utilty module"""

from __future__ import annotations

__all__ = ["Thread", "thread_factory"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import ctypes
import threading
from typing import TYPE_CHECKING, Any, Callable, Final, ParamSpec, Sequence, TypeVar, overload

from .object import Object
from .utils.functools import wraps

_P = ParamSpec("_P")
_T = TypeVar("_T", bound="Thread")


class Thread(threading.Thread, Object, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[Sequence[str]] = ("__dict__",)

    def terminate(self) -> None:
        if self is threading.main_thread():  # Can occur in case of fork/spawn
            raise RuntimeError("Cannot terminate myself")
        if self is threading.current_thread():
            raise SystemExit

        thread_id: int | None = self.ident
        if thread_id is None:
            raise RuntimeError("Thread not started")
        if not self.is_alive():
            raise RuntimeError("Thread already stopped")

        # Asynchronously raise an exception in a thread
        # Ref: https://docs.python.org/3/c-api/init.html?highlight=pythreadstate_setasyncexc#c.PyThreadState_SetAsyncExc
        PyThreadState_SetAsyncExc = ctypes.pythonapi.PyThreadState_SetAsyncExc
        match PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), ctypes.py_object(SystemExit)):
            case 0:  # Invalid ID
                raise RuntimeError("Invalid thread ID")
            case 1:  # In case of success, join the thread
                self.join(timeout=None)
            case ret_val:  # Something went wrong
                PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), ctypes.c_void_p(0))
                raise SystemError("PyThreadState_SetAsyncExc failed", ret_val)

    def join(self, timeout: float | None = None, terminate_on_timeout: bool = False) -> None:
        super().join(timeout)
        if terminate_on_timeout and timeout is not None and self.is_alive():
            self.terminate()


@overload
def thread_factory(func: Callable[_P, None], /) -> Callable[_P, Thread]:
    ...


@overload
def thread_factory(
    *, daemon: bool | None = None, auto_start: bool = True, name: str | None = None
) -> Callable[[Callable[_P, None]], Callable[_P, Thread]]:
    ...


@overload
def thread_factory(
    *,
    thread_cls: type[_T],
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
    **thread_cls_kwargs: Any,
) -> Callable[[Callable[_P, Any]], Callable[_P, _T]]:
    ...


def thread_factory(
    func: Callable[..., Any] | None = None,
    /,
    *,
    thread_cls: type[Thread] = Thread,
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
    **thread_cls_kwargs: Any,
) -> Callable[..., Any]:
    if daemon is not None:
        daemon = bool(daemon)
    auto_start = bool(auto_start)

    def decorator(func: Callable[..., Any], /) -> Callable[..., Thread]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Thread:
            thread = thread_cls(group=None, target=func, args=args, kwargs=kwargs, name=name, daemon=daemon, **thread_cls_kwargs)
            if auto_start:
                thread.start()
            return thread

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
