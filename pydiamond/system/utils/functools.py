# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Functions/decorators utility module"""

from __future__ import annotations

__all__ = [
    "cache",
    "classmethodonly",
    "dsuppress",
    "forbidden_call",
    "lru_cache",
    "setdefaultattr",
    "tp_cache",
    "wraps",
]

from contextlib import ContextDecorator, suppress
from functools import lru_cache as _lru_cache, wraps
from typing import TYPE_CHECKING, Any, Callable, ParamSpec, TypeGuard, TypeVar, overload

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
        def __call__(*args: _P.args, **kwds: _P.kwargs) -> _R:
            ...

        def cache_info(self) -> _CacheInfo:
            ...

        def cache_clear(self) -> None:
            ...

        def cache_parameters(self) -> _CacheParameters:
            ...

        def __copy__(self) -> _lru_cache_wrapper[_P, _R]:
            ...

        def __deepcopy__(self, __memo: Any, /) -> _lru_cache_wrapper[_P, _R]:
            ...


@overload
def lru_cache(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    ...


@overload
def lru_cache(*, maxsize: int | None = 128, typed: bool = False) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    ...


def lru_cache(func: Callable[..., Any] | None = None, /, *, maxsize: int | None = 128, typed: bool = False) -> Callable[..., Any]:
    decorator = _lru_cache(maxsize=maxsize, typed=bool(typed))
    if func is not None:
        return decorator(func)
    return decorator


def cache(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    return lru_cache(maxsize=None)(func)


@overload
def tp_cache(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    ...


@overload
def tp_cache(*, maxsize: int | None = 128, typed: bool = False) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    ...


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


class dsuppress(suppress, ContextDecorator):
    pass
