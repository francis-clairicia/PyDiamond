# -*- coding: Utf-8 -*

from typing import Any, Callable, Optional, Type, TypeVar, Union, cast, overload
from functools import cache as _cache

__all__ = ["cache", "MethodWrapper", "valid_integer", "valid_float"]


_Func = TypeVar("_Func", bound=Callable[..., Any])


def cache(func: _Func) -> _Func:
    return cast(_Func, _cache(func))


class MethodWrapper:
    def __init__(self, wrapper: Callable[..., Any], call_wrapped: bool = False) -> None:
        self.__func__: Callable[..., Any] = wrapper
        self.__wrapped__: Callable[..., Any] = getattr(wrapper, "__wrapped__")
        self.__call_wrapped: bool = bool(call_wrapped)

    def __getattr__(self, name: str) -> Any:
        func: Any = self.__wrapped__
        return getattr(func, name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in ("__func__", "__wrapped__"):
            return super().__setattr__(name, value)
        func: Any = self.__wrapped__
        setattr(func, name, value)

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        func: Callable[..., Any] = self.__wrapped__ if self.__call_wrapped else self.__func__
        return func(*args, **kwargs)

    def __get__(self, obj: object, objtype: Optional[type] = None) -> Callable[..., Any]:
        func: Callable[..., Any] = self.__wrapped__ if obj is None else self.__func__
        func = getattr(func, "__get__")(obj, objtype)
        return func


@overload
def valid_integer(*, min_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, max_value: int) -> Callable[[Any], int]:
    ...


@overload
def valid_integer(*, min_value: int, max_value: int) -> Callable[[Any], int]:
    ...


def valid_integer(**kwargs: Any) -> Callable[[Any], int]:
    return __valid_number(int, **kwargs)


@overload
def valid_float(*, min_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, max_value: float) -> Callable[[Any], float]:
    ...


@overload
def valid_float(*, min_value: float, max_value: float) -> Callable[[Any], float]:
    ...


def valid_float(**kwargs: Any) -> Callable[[Any], float]:
    return __valid_number(float, **kwargs)


@cache
def __valid_number(value_type: Union[Type[int], Type[float]], **kwargs: Any) -> Callable[[Any], Any]:
    _min: Union[int, float]
    _max: Union[int, float]

    if any(param not in ["min_value", "max_value"] for param in kwargs):
        raise TypeError("Invalid arguments")

    null = object()
    min_value: Any = kwargs.get("min_value", null)
    max_value: Any = kwargs.get("max_value", null)

    if min_value is not null and max_value is not null:
        _min = value_type(min_value)
        _max = value_type(max_value)

        if _min > _max:
            raise ValueError(f"min_value ({_min}) > max_value ({_max})")

        def valid_number(val: Any) -> Union[int, float]:
            return min(max(value_type(val), _min), _max)

    elif min_value is not null:
        _min = value_type(min_value)

        def valid_number(val: Any) -> Union[int, float]:
            return max(value_type(val), _min)

    elif max_value is not null:
        _max = value_type(max_value)

        def valid_number(val: Any) -> Union[int, float]:
            return min(value_type(val), _max)

    else:
        raise TypeError("Invalid arguments")

    return valid_number
