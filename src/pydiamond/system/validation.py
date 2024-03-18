# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Generic validator functions module"""

from __future__ import annotations

__all__ = [
    "valid_float",
    "valid_integer",
    "valid_optional_float",
    "valid_optional_integer",
    "valid_sequence",
]

from typing import Any, Callable, Sequence, TypeAlias, TypeVar, overload

from .utils.functools import cache

_T = TypeVar("_T")

_MISSING: Any = object()


@overload
def valid_integer(*, min_value: int) -> Callable[[Any], int]: ...


@overload
def valid_integer(*, max_value: int) -> Callable[[Any], int]: ...


@overload
def valid_integer(*, min_value: int, max_value: int) -> Callable[[Any], int]: ...


@overload
def valid_integer(*, value: Any, min_value: int) -> int: ...


@overload
def valid_integer(*, value: Any, max_value: int) -> int: ...


@overload
def valid_integer(*, value: Any, min_value: int, max_value: int) -> int: ...


def valid_integer(**kwargs: Any) -> int | Callable[[Any], int]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], int] = __valid_number(int, False, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_optional_integer(*, min_value: int) -> Callable[[Any], int | None]: ...


@overload
def valid_optional_integer(*, max_value: int) -> Callable[[Any], int | None]: ...


@overload
def valid_optional_integer(*, min_value: int, max_value: int) -> Callable[[Any], int | None]: ...


@overload
def valid_optional_integer(*, value: Any, min_value: int) -> int | None: ...


@overload
def valid_optional_integer(*, value: Any, max_value: int) -> int | None: ...


@overload
def valid_optional_integer(*, value: Any, min_value: int, max_value: int) -> int | None: ...


def valid_optional_integer(**kwargs: Any) -> int | None | Callable[[Any], int | None]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], int | None] = __valid_number(int, True, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_float(*, min_value: float) -> Callable[[Any], float]: ...


@overload
def valid_float(*, max_value: float) -> Callable[[Any], float]: ...


@overload
def valid_float(*, min_value: float, max_value: float) -> Callable[[Any], float]: ...


@overload
def valid_float(*, value: Any, min_value: float) -> float: ...


@overload
def valid_float(*, value: Any, max_value: float) -> float: ...


@overload
def valid_float(*, value: Any, min_value: float, max_value: float) -> float: ...


def valid_float(**kwargs: Any) -> float | Callable[[Any], float]:
    value: Any = kwargs.pop("value", _MISSING)
    decorator: Callable[[Any], float] = __valid_number(float, False, **kwargs)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@overload
def valid_optional_float(*, min_value: float) -> Callable[[Any], float | None]: ...


@overload
def valid_optional_float(*, max_value: float) -> Callable[[Any], float | None]: ...


@overload
def valid_optional_float(*, min_value: float, max_value: float) -> Callable[[Any], float | None]: ...


@overload
def valid_optional_float(*, value: Any, min_value: float) -> float | None: ...


@overload
def valid_optional_float(*, value: Any, max_value: float) -> float | None: ...


@overload
def valid_optional_float(*, value: Any, min_value: float, max_value: float) -> float | None: ...


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

        if optional:

            def valid_number(val: Any) -> _Number | None:
                if val is None:
                    return None
                return min(max(value_type(val), _min), _max)

        else:

            def valid_number(val: Any) -> _Number | None:
                return min(max(value_type(val), _min), _max)

    elif min_value is not _MISSING:
        _min = value_type(min_value)

        if optional:

            def valid_number(val: Any) -> _Number | None:
                if val is None:
                    return None
                return max(value_type(val), _min)

        else:

            def valid_number(val: Any) -> _Number | None:
                return max(value_type(val), _min)

    elif max_value is not _MISSING:
        _max = value_type(max_value)

        if optional:

            def valid_number(val: Any) -> _Number | None:
                if val is None:
                    return None
                return min(value_type(val), _max)

        else:

            def valid_number(val: Any) -> _Number | None:
                return min(value_type(val), _max)

    else:
        raise TypeError("Invalid arguments")
    return valid_number


@overload
def valid_sequence(*, length: int = ...) -> Callable[[Any], Sequence[Any]]: ...


@overload
def valid_sequence(*, validator: Callable[[Any], _T], length: int = ...) -> Callable[[Any], Sequence[_T]]: ...


@overload
def valid_sequence(*, value: Any, length: int = ...) -> Sequence[Any]: ...


@overload
def valid_sequence(*, value: Any, validator: Callable[[Any], _T], length: int = ...) -> Sequence[_T]: ...


def valid_sequence(*, value: Any = _MISSING, validator: Callable[[Any], Any] | None = None, length: int = -1) -> Any:
    decorator: Callable[[Any], Sequence[Any]] = __valid_sequence(length=length, validator=validator)
    if value is not _MISSING:
        return decorator(value)
    return decorator


@cache
def __valid_sequence(*, length: int, validator: Callable[[Any], Any] | None) -> Callable[[Any], Sequence[Any]]:
    def valid_sequence(val: Any) -> Sequence[Any]:
        if validator is None:
            val = tuple(val)
        else:
            val = tuple(map(validator, val))
        if length >= 0:
            if (val_length := len(val)) != length:
                raise ValueError(f"Invalid sequence length: expected {length}, got {val_length}")
        return val

    return valid_sequence
