# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Utility module"""

__all__ = [
    "cache",
    "concreteclasscheck",
    "concreteclassmethod",
    "forbidden_call",
    "isconcreteclass",
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

from functools import WRAPPER_ASSIGNMENTS, WRAPPER_UPDATES, lru_cache as _lru_cache, update_wrapper as _update_wrapper
from operator import truth
from typing import Any, Callable, ParamSpec, Sequence, TypeAlias, TypeVar, overload

_P = ParamSpec("_P")
_T = TypeVar("_T")
_R = TypeVar("_R")


@overload
def lru_cache(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    ...


@overload
def lru_cache(*, maxsize: int | None = 128, typed: bool = False) -> Callable[[Callable[_P, _R]], Callable[_P, _R]]:
    ...


def lru_cache(func: Callable[..., Any] | None = None, /, *, maxsize: int | None = 128, typed: bool = False) -> Callable[..., Any]:
    decorator = _lru_cache(maxsize=maxsize, typed=typed)
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


def wraps(
    wrapped_func: Callable[_P, _R], *, assigned: Sequence[str] = WRAPPER_ASSIGNMENTS, updated: Sequence[str] = WRAPPER_UPDATES
) -> Callable[[Callable[..., _R]], Callable[_P, _R]]:
    def decorator(wrapper: Callable[..., Any]) -> Callable[..., Any]:
        return _update_wrapper(wrapper, wrapped_func, assigned=assigned, updated=updated)

    return decorator


def setdefaultattr(obj: object, name: str, value: _T) -> _T:
    try:
        return getattr(obj, name)  # type: ignore[no-any-return]
    except AttributeError:
        setattr(obj, name, value)
    return value


# def concreteclassmethod(func: Callable[Concatenate[type[_T], _P], _R]) -> Callable[Concatenate[type[_T], _P], _R]:
def concreteclassmethod(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def wrapper(cls: Any, /, *args: Any, **kwargs: Any) -> Any:
        concreteclasscheck(cls)
        return func(cls, *args, **kwargs)

    return wrapper


def concreteclasscheck(cls: Any) -> None:
    if not isconcreteclass(cls):
        raise TypeError(f"{cls.__name__} is an abstract class")


def isconcreteclass(cls: type) -> bool:
    if not isinstance(cls, type):
        raise TypeError("'cls' must be a type")
    return not truth(getattr(cls, "__abstractmethods__", None))


def forbidden_call(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def not_callable(*args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"Call to function {func.__module__}.{func.__name__} is forbidden")

    return not_callable


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


def valid_integer(**kwargs: Any) -> int | Callable[[Any], int]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], int] = __valid_number(int, False, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_optional_integer(*, min_value: int) -> Callable[[Any], int | None]:
    ...


@overload
def valid_optional_integer(*, max_value: int) -> Callable[[Any], int | None]:
    ...


@overload
def valid_optional_integer(*, min_value: int, max_value: int) -> Callable[[Any], int | None]:
    ...


@overload
def valid_optional_integer(*, value: Any, min_value: int) -> int | None:
    ...


@overload
def valid_optional_integer(*, value: Any, max_value: int) -> int | None:
    ...


@overload
def valid_optional_integer(*, value: Any, min_value: int, max_value: int) -> int | None:
    ...


def valid_optional_integer(**kwargs: Any) -> int | None | Callable[[Any], int | None]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], int | None] = __valid_number(int, True, **kwargs)
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


def valid_float(**kwargs: Any) -> float | Callable[[Any], float]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], float] = __valid_number(float, False, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_optional_float(*, min_value: float) -> Callable[[Any], float | None]:
    ...


@overload
def valid_optional_float(*, max_value: float) -> Callable[[Any], float | None]:
    ...


@overload
def valid_optional_float(*, min_value: float, max_value: float) -> Callable[[Any], float | None]:
    ...


@overload
def valid_optional_float(*, value: Any, min_value: float) -> float | None:
    ...


@overload
def valid_optional_float(*, value: Any, max_value: float) -> float | None:
    ...


@overload
def valid_optional_float(*, value: Any, min_value: float, max_value: float) -> float | None:
    ...


def valid_optional_float(**kwargs: Any) -> float | None | Callable[[Any], float | None]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], float | None] = __valid_number(float, True, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


_Number: TypeAlias = int | float


@cache
def __valid_number(value_type: type[_Number], optional: bool, /, **kwargs: Any) -> Callable[[Any], Any]:
    _min: _Number
    _max: _Number

    if any(param not in ("min_value", "max_value") for param in kwargs):
        raise TypeError("Invalid arguments")

    min_value: Any = kwargs.get("min_value", _MISSING)
    max_value: Any = kwargs.get("max_value", _MISSING)

    if min_value is not _MISSING and max_value is not _MISSING:
        _min = value_type(min_value)
        _max = value_type(max_value)

        if _min > _max:
            raise ValueError(f"min_value ({_min}) > max_value ({_max})")

        def valid_number(val: Any) -> _Number | None:
            if optional and val is None:
                return None
            return min(max(value_type(val), _min), _max)

    elif min_value is not _MISSING:
        _min = value_type(min_value)

        def valid_number(val: Any) -> _Number | None:
            if optional and val is None:
                return None
            return max(value_type(val), _min)

    elif max_value is not _MISSING:
        _max = value_type(max_value)

        def valid_number(val: Any) -> _Number | None:
            if optional and val is None:
                return None
            return min(value_type(val), _max)

    else:
        raise TypeError("Invalid arguments")
    return valid_number


del _P, _T, _R
