# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Functions/decorators utility module"""

from __future__ import annotations

__all__ = [
    "cache",
    "classmethodonly",
    "forbidden_call",
    "lru_cache",
    "setdefaultattr",
    "tp_cache",
    "wraps",
]

from collections.abc import Callable
from functools import lru_cache as _lru_cache, wraps
from typing import TYPE_CHECKING, Any, Concatenate, ParamSpec, TypeGuard, TypeVar, overload
from weakref import WeakMethod, ref as weakref

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")


if TYPE_CHECKING:
    from functools import _CacheInfo
    from typing import Generic, TypedDict, final, type_check_only

    @type_check_only
    class _CacheParameters(TypedDict):
        maxsize: int | None
        typed: bool

    @final
    @type_check_only
    class _lru_cache_wrapper(Generic[_P, _R]):
        __wrapped__: Callable[_P, _R]

        @staticmethod
        def __call__(*args: _P.args, **kwds: _P.kwargs) -> _R: ...

        def cache_info(self) -> _CacheInfo: ...

        def cache_clear(self) -> None: ...

        def cache_parameters(self) -> _CacheParameters: ...

        def __copy__(self) -> _lru_cache_wrapper[_P, _R]: ...

        def __deepcopy__(self, __memo: Any, /) -> _lru_cache_wrapper[_P, _R]: ...


@overload
def lru_cache(func: Callable[_P, _R], /) -> Callable[_P, _R]: ...


@overload
def lru_cache(*, maxsize: int | None = 128, typed: bool = False) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...


def lru_cache(func: Callable[..., Any] | None = None, /, *, maxsize: int | None = 128, typed: bool = False) -> Callable[..., Any]:
    decorator = _lru_cache(maxsize=maxsize, typed=bool(typed))
    if func is not None:
        return decorator(func)
    return decorator


def cache(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    return lru_cache(maxsize=None)(func)


@overload
def tp_cache(func: Callable[_P, _R], /) -> Callable[_P, _R]: ...


@overload
def tp_cache(*, maxsize: int | None = 128, typed: bool = False) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]: ...


def tp_cache(func: Callable[..., Any] | None = None, /, *, maxsize: int | None = 128, typed: bool = False) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cached: Callable[..., Any] = lru_cache(maxsize=maxsize, typed=typed)(func)

        assert is_lru_cache(cached)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return cached(*args, **kwargs)
            except TypeError:
                pass
            return func(*args, **kwargs)

        setattr(wrapper, "cache_clear", cached.cache_clear)
        setattr(wrapper, "cache_info", cached.cache_info)
        setattr(wrapper, "cache_parameters", cached.cache_parameters)

        assert is_lru_cache(wrapper)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def is_lru_cache(f: Callable[_P, _R]) -> TypeGuard[_lru_cache_wrapper[_P, _R]]:
    return (
        callable(f)
        and all(callable(getattr(f, method, None)) for method in ("cache_info", "cache_clear", "cache_parameters"))
        and hasattr(f, "__wrapped__")
    )


def setdefaultattr(obj: object, name: str, value: _T) -> Any | _T:
    try:
        return getattr(obj, name)
    except AttributeError:
        setattr(obj, name, value)
    return value


if TYPE_CHECKING:
    classmethodonly = classmethod

else:
    _R_co = TypeVar("_R_co", covariant=True)

    class classmethodonly(classmethod):
        def __get__(self, __obj: _T, __type: type[_T] | None = ...) -> Callable[..., _R_co]:
            if __obj is not None:
                raise TypeError("This method should not be called from instance")
            return super().__get__(__obj, __type)


def forbidden_call(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def not_callable(*args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"Call to function {func.__qualname__} is forbidden")

    setattr(not_callable, "__forbidden_call__", True)
    return not_callable


@overload
def make_callback(
    __func: Callable[_P, _R] | WeakMethod[Callable[_P, _R]],
    __obj: None = ...,
    /,
    weakref_callback: Callable[[weakref[Any]], Any] | None = ...,
    deadref_value_return: Any = ...,
) -> Callable[_P, _R]: ...


@overload
def make_callback(
    __func: Callable[Concatenate[_T, _P], _R] | WeakMethod[Callable[Concatenate[_T, _P], _R]],
    __obj: _T,
    /,
    weakref_callback: Callable[[weakref[_T]], Any] | None = ...,
    deadref_value_return: _R = ...,
) -> Callable[_P, _R]: ...


@overload
def make_callback(
    __func: Callable[Concatenate[_T, _P], _R] | WeakMethod[Callable[Concatenate[_T, _P], _R]],
    __obj: _T,
    /,
    weakref_callback: Callable[[weakref[_T]], Any] | None = ...,
    deadref_value_return: type[BaseException] = ...,
) -> Callable[_P, _R]: ...


def make_callback(
    func_or_weakmethod: Callable[..., Any] | WeakMethod[Callable[..., Any]],
    obj: Any = None,
    /,
    weakref_callback: Callable[[weakref[Any]], Any] | None = None,
    deadref_value_return: Any = ReferenceError,
) -> Callable[..., Any]:
    func: Callable[..., Any]
    weak_method: WeakMethod[Callable[..., Any]]
    objref: weakref[Any]

    if isinstance(deadref_value_return, type) and issubclass(deadref_value_return, BaseException):
        deadref_exception: type[BaseException] = deadref_value_return

        def deadref_fallback() -> Any:
            raise deadref_exception("weakly-referenced object no longer exists")

    else:

        def deadref_fallback() -> Any:
            return deadref_value_return

    if not isinstance(func_or_weakmethod, WeakMethod):
        func = func_or_weakmethod

        if obj is None:
            callback = func

        else:
            objref = weakref(obj, weakref_callback)

            def callback(*args: Any, **kwargs: Any) -> Any:
                obj = objref()
                if obj is None:
                    return deadref_fallback()
                return func(obj, *args, **kwargs)

    else:
        weak_method = func_or_weakmethod

        if obj is None:

            def callback(*args: Any, **kwargs: Any) -> Any:
                method = weak_method()
                if method is None:
                    return deadref_fallback()
                return method(*args, **kwargs)

        else:
            objref = weakref(obj, weakref_callback)

            def callback(*args: Any, **kwargs: Any) -> Any:
                method = weak_method()
                obj = objref()
                if method is None or obj is None:
                    return deadref_fallback()
                return method(obj, *args, **kwargs)

    return callback
