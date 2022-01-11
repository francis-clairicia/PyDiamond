# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Threading utilty module"""

__all__ = ["JThread", "RThread", "Thread", "jthread", "rthread", "thread"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from threading import Thread, current_thread
from typing import Any, Callable, Generic, Iterable, Mapping, Optional, ParamSpec, Type, TypeVar, overload

from .utils import wraps

_P = ParamSpec("_P")
_T = TypeVar("_T", bound=Thread)
_R = TypeVar("_R")


@overload
def thread(func: Callable[_P, None], /) -> Callable[_P, Thread]:
    ...


@overload
def thread(
    *, daemon: Optional[bool] = None, auto_start: bool = True, name: Optional[str] = None
) -> Callable[[Callable[_P, None]], Callable[_P, Thread]]:
    ...


@overload
def thread(
    *,
    thread_cls: Type[_T],
    daemon: Optional[bool] = None,
    auto_start: bool = True,
    name: Optional[str] = None,
    **thread_cls_kwargs: Any,
) -> Callable[[Callable[_P, Any]], Callable[_P, _T]]:
    ...


def thread(
    func: Optional[Callable[..., Any]] = None,
    /,
    *,
    thread_cls: Type[Thread] = Thread,
    daemon: Optional[bool] = None,
    auto_start: bool = True,
    name: Optional[str] = None,
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
        target: Optional[Callable[..., _R]] = None,
        name: Optional[str] = None,
        args: Iterable[Any] = (),
        kwargs: Optional[Mapping[str, Any]] = None,
        *,
        daemon: Optional[bool] = None,
    ) -> None:
        self._return: _R
        used_target: Optional[Callable[..., None]] = None
        if target is not None:
            _target: Callable[..., _R] = target

            def used_target(*args: Any, **kwargs: Any) -> None:
                self._return = _target(*args, **kwargs)

        super().__init__(group=group, target=used_target, name=name, args=args, kwargs=kwargs, daemon=daemon)

    def join(self, timeout: Optional[float] = None) -> _R:  # type: ignore[override]
        super().join(timeout=timeout)
        ret: _R = self._return
        del self._return
        return ret


@overload
def rthread(func: Callable[_P, _R], /) -> Callable[_P, RThread[_R]]:
    ...


@overload
def rthread(
    *, daemon: Optional[bool] = None, auto_start: bool = True, name: Optional[str] = None
) -> Callable[[Callable[_P, _R]], Callable[_P, RThread[_R]]]:
    ...


def rthread(
    func: Optional[Callable[..., Any]] = None,
    /,
    *,
    daemon: Optional[bool] = None,
    auto_start: bool = True,
    name: Optional[str] = None,
) -> Callable[..., Any]:
    decorator = thread(thread_cls=RThread, daemon=daemon, auto_start=auto_start, name=name)
    if func is not None:
        return decorator(func)
    return decorator


class JThread(Thread):
    def __init__(
        self,
        group: None = None,
        target: Optional[Callable[..., None]] = None,
        name: Optional[str] = None,
        args: Iterable[Any] = (),
        kwargs: Optional[Mapping[str, Any]] = None,
        *,
        daemon: None = None,
    ) -> None:
        used_target: Optional[Callable[..., None]] = target
        super().__init__(group=group, target=used_target, name=name, args=args, kwargs=kwargs)

    def __del__(self) -> None:
        if current_thread() is self or not self.is_alive():
            return
        self.join()

    @property
    def daemon(self) -> bool:  # type: ignore[override]
        return super().daemon


@overload
def jthread(func: Callable[_P, None], /) -> Callable[_P, JThread]:
    ...


@overload
def jthread(*, auto_start: bool = True, name: Optional[str] = None) -> Callable[[Callable[_P, None]], Callable[_P, JThread]]:
    ...


def jthread(
    func: Optional[Callable[..., Any]] = None,
    /,
    *,
    auto_start: bool = True,
    name: Optional[str] = None,
) -> Callable[..., Any]:
    decorator = thread(thread_cls=JThread, daemon=None, auto_start=auto_start, name=name)
    if func is not None:
        return decorator(func)
    return decorator
