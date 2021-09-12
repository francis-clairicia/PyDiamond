# -*- coding: Utf-8 -*

from typing import Any, Callable, Optional, Type, TypeVar, Union, cast, overload
from functools import cache as _cache

__all__ = ["cache", "valid_integer", "valid_float"]


_Func = TypeVar("_Func", bound=Callable[..., Any])


def cache(func: _Func) -> _Func:
    return cast(_Func, _cache(func))


@overload
def valid_integer(*, min_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, max_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, min_value: int, max_value: int) -> Callable[[Any], int]:
    ...


def valid_integer(*, min_value: Optional[int] = None, max_value: Optional[int] = None) -> Callable[[Any], int]:
    return __valid_number(int, min_value=min_value, max_value=max_value)


@overload
def valid_float(*, min_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, max_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, min_value: float, max_value: float) -> Callable[[Any], float]:
    ...


def valid_float(*, min_value: Optional[float] = None, max_value: Optional[float] = None) -> Callable[[Any], float]:
    return __valid_number(float, min_value=min_value, max_value=max_value)


@cache
def __valid_number(
    value_type: Union[Type[int], Type[float]], *, min_value: Optional[float], max_value: Optional[float]
) -> Callable[[Any], Any]:
    _min: float
    _max: float

    if min_value is not None and max_value is not None:
        _min = value_type(min_value)
        _max = value_type(max_value)

        if _min >= _max:
            raise ValueError(f"min_value ({_min}) >= max_value ({_max})")

        def valid_impl(val: Any) -> float:
            return min(max(value_type(val), _min), _max)

    elif min_value is not None:
        _min = value_type(min_value)

        def valid_impl(val: Any) -> float:
            return max(value_type(val), _min)

    elif max_value is not None:
        _max = value_type(max_value)

        def valid_impl(val: Any) -> float:
            return min(value_type(val), _max)

    else:
        raise TypeError("Invalid arguments")

    return valid_impl
