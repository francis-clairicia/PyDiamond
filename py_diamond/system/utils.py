# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Utility module"""

__all__ = [
    "cache",
    "concreteclassmethod",
    "lru_cache",
    "setdefaultattr",
    "tp_cache",
    "valid_float",
    "valid_integer",
    "valid_optional_float",
    "valid_optional_integer",
    "wraps",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from functools import lru_cache as _lru_cache, wraps as _wraps
from typing import Any, Callable, Optional, Type, TypeVar, Union, cast, overload

_T = TypeVar("_T")
_Func = TypeVar("_Func", bound=Callable[..., Any])


@overload
def lru_cache(func: _Func, /) -> _Func:
    ...


@overload
def lru_cache(*, maxsize: Optional[int] = 128, typed: bool = False) -> Callable[[_Func], _Func]:
    ...


def lru_cache(func: Optional[_Func] = None, /, *, maxsize: Optional[int] = 128, typed: bool = False) -> Callable[..., Any]:
    decorator = cast(Callable[[_Func], _Func], _lru_cache(maxsize=maxsize, typed=typed))
    if func is not None:
        return decorator(func)
    return decorator


def cache(func: _Func, /) -> _Func:
    return lru_cache(maxsize=None)(func)


@overload
def tp_cache(func: _Func, /) -> _Func:
    ...


@overload
def tp_cache(*, maxsize: Optional[int] = 128, typed: bool = False) -> Callable[[_Func], _Func]:
    ...


def tp_cache(func: Optional[_Func] = None, /, *, maxsize: Optional[int] = 128, typed: bool = False) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        cached: Callable[..., Any] = lru_cache(maxsize=maxsize, typed=typed)(func)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return cached(*args, **kwargs)
            except TypeError:
                pass
            return func(*args, **kwargs)

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def wraps(wrapped_func: _Func) -> Callable[[Callable[..., Any]], _Func]:
    def decorator(wrapper: Callable[..., Any]) -> _Func:
        wrapper = _wraps(wrapped_func)(wrapper)
        return cast(_Func, _FunctionWrapperProxy(wrapper))

    return decorator


def setdefaultattr(obj: object, name: str, value: _T) -> _T:
    try:
        return getattr(obj, name)  # type: ignore[no-any-return]
    except AttributeError:
        setattr(obj, name, value)
    return value


def concreteclassmethod(func: _Func) -> _Func:
    @wraps(func)
    def wrapper(cls: Any, /, *args: Any, **kwargs: Any) -> Any:
        if isinstance(cls, type) and getattr(cls, "__abstractmethods__", None):
            raise TypeError(f"{cls.__name__} is an abstract class")
        return func(cls, *args, **kwargs)

    return wrapper


_MISSING: Any = object()


@overload
def valid_integer(*, min_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, max_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, min_value: int, max_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, value: Any, min_value: int) -> int:
    ...


@overload
def valid_integer(*, value: Any, max_value: int) -> int:
    ...


@overload
def valid_integer(*, value: Any, min_value: int, max_value: int) -> int:
    ...


def valid_integer(**kwargs: Any) -> Union[int, Callable[[Any], int]]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], int] = __valid_number(int, False, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_optional_integer(*, min_value: int) -> Callable[[Any], Optional[int]]:
    ...


@overload
def valid_optional_integer(*, max_value: int) -> Callable[[Any], Optional[int]]:
    ...


@overload
def valid_optional_integer(*, min_value: int, max_value: int) -> Callable[[Any], Optional[int]]:
    ...


@overload
def valid_optional_integer(*, value: Any, min_value: int) -> Optional[int]:
    ...


@overload
def valid_optional_integer(*, value: Any, max_value: int) -> Optional[int]:
    ...


@overload
def valid_optional_integer(*, value: Any, min_value: int, max_value: int) -> Optional[int]:
    ...


def valid_optional_integer(**kwargs: Any) -> Union[Optional[int], Callable[[Any], Optional[int]]]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], Optional[int]] = __valid_number(int, True, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_float(*, min_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, max_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, min_value: float, max_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, value: Any, min_value: float) -> float:
    ...


@overload
def valid_float(*, value: Any, max_value: float) -> float:
    ...


@overload
def valid_float(*, value: Any, min_value: float, max_value: float) -> float:
    ...


def valid_float(**kwargs: Any) -> Union[float, Callable[[Any], float]]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], float] = __valid_number(float, False, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_optional_float(*, min_value: float) -> Callable[[Any], Optional[float]]:
    ...


@overload
def valid_optional_float(*, max_value: float) -> Callable[[Any], Optional[float]]:
    ...


@overload
def valid_optional_float(*, min_value: float, max_value: float) -> Callable[[Any], Optional[float]]:
    ...


@overload
def valid_optional_float(*, value: Any, min_value: float) -> Optional[float]:
    ...


@overload
def valid_optional_float(*, value: Any, max_value: float) -> Optional[float]:
    ...


@overload
def valid_optional_float(*, value: Any, min_value: float, max_value: float) -> Optional[float]:
    ...


def valid_optional_float(**kwargs: Any) -> Union[Optional[float], Callable[[Any], Optional[float]]]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], Optional[float]] = __valid_number(float, True, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@cache
def __valid_number(value_type: Union[Type[int], Type[float]], optional: bool, /, **kwargs: Any) -> Callable[[Any], Any]:
    _min: Union[int, float]
    _max: Union[int, float]

    if any(param not in ("min_value", "max_value") for param in kwargs):
        raise TypeError("Invalid arguments")

    null = object()
    min_value: Any = kwargs.get("min_value", null)
    max_value: Any = kwargs.get("max_value", null)

    if min_value is not null and max_value is not null:
        _min = value_type(min_value)
        _max = value_type(max_value)

        if _min > _max:
            raise ValueError(f"min_value ({_min}) > max_value ({_max})")

        def valid_number(val: Any) -> Optional[Union[int, float]]:
            if optional and val is None:
                return None
            return min(max(value_type(val), _min), _max)

    elif min_value is not null:
        _min = value_type(min_value)

        def valid_number(val: Any) -> Optional[Union[int, float]]:
            if optional and val is None:
                return None
            return max(value_type(val), _min)

    elif max_value is not null:
        _max = value_type(max_value)

        def valid_number(val: Any) -> Optional[Union[int, float]]:
            if optional and val is None:
                return None
            return min(value_type(val), _max)

    else:
        raise TypeError("Invalid arguments")
    return valid_number


class _FunctionWrapperProxy:
    def __init__(self, /, wrapper: Callable[..., Any]) -> None:
        if not callable(getattr(wrapper, "__wrapped__")):
            raise AttributeError("Not a valid wrapper object: __wrapped__ attribute must be callable")
        self.__func__: Callable[..., Any] = wrapper

    def __repr__(self, /) -> str:
        func: Callable[..., Any] = self.__wrapped__
        return f"<function wrapper proxy {func.__name__} at {id(self):#x}>"

    def __getattr__(self, /, name: str) -> Any:
        func: Any = self.__wrapped__
        return getattr(func, name)

    def __setattr__(self, /, name: str, value: Any) -> None:
        if name == "__func__":
            if "__func__" in self.__dict__:
                raise AttributeError("__func__ is a read-only attribute")
            return super().__setattr__(name, value)
        func: Any = self.__wrapped__
        return setattr(func, name, value)

    def __delattr__(self, /, name: str) -> None:
        if name == "__func__":
            raise AttributeError("__func__ is a read-only attribute")
        return super().__delattr__(name)

    def __call__(self, /, *args: Any, **kwargs: Any) -> Any:
        func: Callable[..., Any] = self.__func__
        return func(*args, **kwargs)

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Callable[..., Any]:
        func: Callable[..., Any] = self.__func__
        func = getattr(func, "__get__")(obj, objtype)
        return func

    @property
    def __wrapped__(self, /) -> Callable[..., Any]:
        func: Callable[..., Any] = self.__func__
        func = getattr(func, "__wrapped__")
        return func
