# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Threading utilty module"""

from __future__ import annotations

__all__ = ["Thread", "thread_factory", "thread_factory_method"]


import ctypes
import threading
from typing import TYPE_CHECKING, Any, Callable, Concatenate, Final, Generic, ParamSpec, Sequence, TypeVar, overload
from weakref import WeakKeyDictionary

from .object import Object
from .utils.functools import wraps

if TYPE_CHECKING:
    from typing import type_check_only

_P = ParamSpec("_P")
_ThreadT = TypeVar("_ThreadT", bound="Thread")
_T = TypeVar("_T")
_R = TypeVar("_R")


class Thread(threading.Thread, Object, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[Sequence[str]] = ("__dict__", "__weakref__")

    def terminate(self) -> None:
        if self is threading.main_thread():  # Can occur in case of fork/spawn
            raise RuntimeError("Cannot terminate myself")
        if self is threading.current_thread():
            raise SystemExit(0)

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
def thread_factory(func: Callable[_P, Any], /) -> Callable[_P, Thread]:
    ...


@overload
def thread_factory(
    *,
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
) -> Callable[[Callable[_P, Any]], Callable[_P, Thread]]:
    ...


@overload
def thread_factory(
    *,
    thread_cls: type[_ThreadT],
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
    **thread_cls_kwargs: Any,
) -> Callable[[Callable[_P, Any]], Callable[_P, _ThreadT]]:
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


@overload
def thread_factory_method(func: Callable[Concatenate[_T, _P], _R], /) -> _ThreadFactoryMethod[_T, _P, _R, Thread]:
    ...


@overload
def thread_factory_method(
    *,
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
    global_lock: bool = True,
    shared_lock: bool = False,
) -> Callable[[Callable[Concatenate[_T, _P], _R]], _ThreadFactoryMethod[_T, _P, _R, Thread]]:
    ...


@overload
def thread_factory_method(
    *,
    thread_cls: type[_ThreadT],
    daemon: bool | None = None,
    auto_start: bool = True,
    name: str | None = None,
    global_lock: bool = True,
    shared_lock: bool = False,
    **thread_cls_kwargs: Any,
) -> Callable[[Callable[Concatenate[_T, _P], _R]], _ThreadFactoryMethod[_T, _P, _R, Thread]]:
    ...


def thread_factory_method(
    func: Callable[..., Any] | None = None,
    /,
    *,
    thread_cls: type[Thread] = Thread,
    **kwargs: Any,
) -> Callable[[Callable[..., Any]], _ThreadFactoryMethod[Any, Any, Any, Any]] | _ThreadFactoryMethod[Any, Any, Any, Any]:
    def decorator(func: Callable[..., Any]) -> _ThreadFactoryMethod[Any, ..., Any, Thread]:
        return _ThreadFactoryMethod(func, thread_cls=thread_cls, **kwargs)

    if func is not None:
        return decorator(func)
    return decorator


if TYPE_CHECKING:

    @type_check_only
    class _ThreadMethodType(Generic[_P, _ThreadT]):
        @staticmethod
        def __call__(*args: _P.args, **kwds: _P.kwargs) -> _ThreadT:
            ...

        def get_lock(self) -> threading.RLock:
            ...


class _ThreadFactoryMethod(Generic[_T, _P, _R, _ThreadT]):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="_ThreadFactoryMethod[Any, Any, Any, Any]")

    def __init__(
        self,
        func: Callable[Concatenate[_T, _P], _R],
        /,
        thread_cls: type[_ThreadT],
        *,
        global_lock: bool = True,
        shared_lock: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__()
        self.__func__: Callable[Concatenate[_T, _P], _R] = func
        self.__global_lock: bool = bool(global_lock)
        self.__thread_factory = thread_factory(thread_cls=thread_cls, **kwargs)
        self.__default_lock: threading.RLock | None = threading.RLock() if shared_lock else None
        self.__private_lock = threading.RLock()
        self.__lock: WeakKeyDictionary[_T, threading.RLock] = WeakKeyDictionary()

    def __set_name__(self, owner: type, name: str, /) -> None:
        if not hasattr(owner, "__weakref__"):
            raise TypeError(f"{owner.__qualname__!r} must be weak-referencable")

    def __call__(__self, self: _T, *args: _P.args, **kwargs: _P.kwargs) -> _ThreadT:
        func = __self.__get__(self)
        return func(*args, **kwargs)

    @overload
    def __get__(self: __Self, obj: None, objtype: type | None = None, /) -> __Self:
        ...

    @overload
    def __get__(self, obj: _T, objtype: type | None = None, /) -> _ThreadMethodType[_P, _ThreadT]:
        ...

    def __get__(self: __Self, obj: _T | None, objtype: type | None = None, /) -> __Self | _ThreadMethodType[_P, _ThreadT]:
        if obj is None:
            if objtype is None:
                raise TypeError("__get__(None, None) is forbidden")
            return self

        func: Callable[_P, _R] = self.__func__.__get__(obj, objtype)
        lock: threading.RLock = self.get_lock(obj)

        if self.__global_lock:

            @self.__thread_factory
            def thread_method(*args: _P.args, **kwargs: _P.kwargs) -> _R:
                with lock:
                    return func(*args, **kwargs)

        else:

            thread_method = self.__thread_factory(func)

        setattr(thread_method, "get_lock", lambda: lock)

        return thread_method  # type: ignore[return-value]

    def get_lock(self, obj: _T) -> threading.RLock:
        if default_lock := self.__default_lock:
            return default_lock
        lock_cache = self.__lock
        lock: threading.RLock | None = lock_cache.get(obj)
        if lock is None:
            with self.__private_lock:
                lock = lock_cache.get(obj)
                if lock is None:
                    lock_cache[obj] = lock = threading.RLock()
        return lock

    @property
    def __wrapped__(self) -> Callable[Concatenate[_T, _P], _R]:
        return self.__func__
