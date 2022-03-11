# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Threading utilty module"""

__all__ = ["RThread", "Thread", "rthread", "thread"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from threading import Thread as _Thread
from typing import Any, Callable, Generic, Iterable, Mapping, ParamSpec, TypeVar, overload

from .utils import wraps

_P = ParamSpec("_P")
_T = TypeVar("_T", bound="Thread")
_R = TypeVar("_R")


class Thread(_Thread):
    pass


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
            thread = thread_cls(target=func, args=args, kwargs=kwargs, name=name, daemon=daemon, **thread_cls_kwargs)
            if auto_start:
                thread.start()
            return thread

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


class RThread(Thread, Generic[_R]):
    def __init__(
        self,
        group: None = None,
        target: Callable[..., _R] | None = None,
        name: str | None = None,
        args: Iterable[Any] = (),
        kwargs: Mapping[str, Any] | None = None,
        *,
        daemon: bool | None = None,
    ) -> None:
        self._return: _R
        used_target: Callable[..., None] | None = None
        if target is not None:
            _target: Callable[..., _R] = target

            def used_target(*args: Any, **kwargs: Any) -> None:
                self._return = _target(*args, **kwargs)

        super().__init__(group=group, target=used_target, name=name, args=args, kwargs=kwargs, daemon=daemon)

    def join(self, timeout: float | None = None) -> _R:  # type: ignore[override]
        super().join(timeout)
        ret: _R = self._return
        del self._return
        return ret


@overload
def rthread(func: Callable[_P, _R], /) -> Callable[_P, RThread[_R]]:
    ...


@overload
def rthread(
    *, daemon: bool | None = None, auto_start: bool = True, name: str | None = None
) -> Callable[[Callable[_P, _R]], Callable[_P, RThread[_R]]]:
    ...


def rthread(
    func: Callable[..., Any] | None = None,
    /,
    *,
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
) -> Callable[..., Any]:
    decorator = thread(thread_cls=RThread, daemon=daemon, auto_start=auto_start, name=name)
    if func is not None:
        return decorator(func)
    return decorator


del _Thread
