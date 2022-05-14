# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Threading utilty module"""

from __future__ import annotations

__all__ = ["Thread", "thread"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import ctypes
import threading
from contextlib import ExitStack
from typing import TYPE_CHECKING, Any, Callable, Final, ParamSpec, Sequence, TypeVar, overload

from .object import Object
from .utils import wraps

_P = ParamSpec("_P")
_T = TypeVar("_T", bound="Thread")


class Thread(threading.Thread, Object, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[Sequence[str]] = ("__dict__",)

    class Exit(BaseException):
        """
        Specific exception raised by terminate() to stop a thread
        """

    def start(self) -> None:
        default_thread_run: Callable[[], None] = self.run

        def thread_run() -> None:
            try:
                return default_thread_run()
            except Thread.Exit:  # Exception raised within run() or sent by other thread using terminate()
                return

        with ExitStack() as stack:
            if "run" in self.__dict__:  # setattr() was previously called to override default run

                def __clear_run() -> None:
                    self.__dict__["run"] = default_thread_run

            else:

                def __clear_run() -> None:
                    attr_dict = self.__dict__
                    if attr_dict.get("run") is thread_run:
                        attr_dict.pop("run")

            self.__dict__["run"] = thread_run

            stack.callback(__clear_run)

            return super().start()

    def terminate(self) -> None:
        if self is threading.current_thread():
            raise RuntimeError("Cannot terminate myself")
        thread_id: int | None = self.ident
        if thread_id is None:
            raise RuntimeError("Thread not started")
        if not self.is_alive():
            raise RuntimeError("Thread already stopped")

        # Asynchronously raise an exception in a thread
        # Ref: https://docs.python.org/3/c-api/init.html?highlight=pythreadstate_setasyncexc#c.PyThreadState_SetAsyncExc
        PyThreadState_SetAsyncExc = ctypes.pythonapi.PyThreadState_SetAsyncExc
        match PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), ctypes.py_object(Thread.Exit)):
            case 0:  # Invalid ID
                raise RuntimeError("Invalid thread ID")
            case 1:  # In case of success, join the thread
                self.join(timeout=None)
            case _:  # Something went wrong
                PyThreadState_SetAsyncExc(ctypes.c_ulong(thread_id), ctypes.c_void_p(0))
                raise SystemError("PyThreadState_SetAsyncExc failed")

    def join(self, timeout: float | None = None, terminate_on_timeout: bool = False) -> None:
        super().join(timeout)
        if timeout is not None and self.is_alive() and terminate_on_timeout:
            self.terminate()
        


@overload
def thread(func: Callable[_P, None], /) -> Callable[_P, Thread]:
    ...


@overload
def thread(
    *, daemon: bool | None = None, auto_start: bool = True, name: str | None = None
) -> Callable[[Callable[_P, None]], Callable[_P, Thread]]:
    ...


@overload
def thread(
    *,
    thread_cls: type[_T],
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
    **thread_cls_kwargs: Any,
) -> Callable[[Callable[_P, Any]], Callable[_P, _T]]:
    ...


def thread(
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
