# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Utility module"""

from __future__ import annotations

__all__ = [
    "cache",
    "classmethodonly",
    "concreteclass",
    "concreteclasscheck",
    "concreteclassmethod",
    "dsuppress",
    "flatten",
    "forbidden_call",
    "isabstract",
    "isabstractmethod",
    "isconcreteclass",
    "lru_cache",
    "setdefaultattr",
    "tp_cache",
    "valid_float",
    "valid_integer",
    "valid_optional_float",
    "valid_optional_integer",
    "weakref_unwrap",
    "wraps",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import ContextDecorator, suppress
from functools import lru_cache as _lru_cache, wraps
from inspect import isabstract
from itertools import chain
from operator import truth
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Concatenate,
    Iterable,
    Iterator,
    Literal,
    ParamSpec,
    TypeAlias,
    TypeGuard,
    TypeVar,
    overload,
)
from weakref import ReferenceType as WeakReferenceType

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
        __call__: Callable[_P, _R]

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
                raise TypeError(f"This method should not be called from instance")
            return super().__get__(__obj, __type)


_TT = TypeVar("_TT", bound=type)


def concreteclassmethod(func: Callable[Concatenate[_TT, _P], _R]) -> Callable[Concatenate[_TT, _P], _R]:
    @wraps(func)
    def wrapper(cls: _TT, /, *args: _P.args, **kwargs: _P.kwargs) -> _R:
        concreteclasscheck(cls)
        return func(cls, *args, **kwargs)

    return wrapper


def concreteclass(cls: _TT) -> _TT:
    concreteclasscheck(cls)
    return cls


def concreteclasscheck(cls: Any) -> None:
    if not isconcreteclass(cls):
        raise TypeError(f"{cls.__name__} is an abstract class (abstract methods: {', '.join(cls.__abstractmethods__)})")


def isconcreteclass(cls: type) -> bool:
    if not isinstance(cls, type):
        raise TypeError("'cls' must be a type")
    return not isabstract(cls)


def isabstractmethod(func: Any) -> bool:
    return truth(getattr(func, "__isabstractmethod__", False))


def forbidden_call(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def not_callable(*args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"Call to function {func.__qualname__} is forbidden")

    return not_callable


class dsuppress(suppress, ContextDecorator):
    pass


def weakref_unwrap(ref: WeakReferenceType[_T]) -> _T:
    obj = ref()
    if obj is None:
        raise ReferenceError("weakly-referenced object no longer exists")
    return obj


@overload
def flatten(iterable: Iterable[Iterable[_T]]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[_T]], *, level: Literal[1]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[_T]]], *, level: Literal[2]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[Iterable[_T]]]], *, level: Literal[3]) -> Iterator[_T]:
    ...


@overload
def flatten(iterable: Iterable[Iterable[Iterable[Iterable[Iterable[_T]]]]], *, level: Literal[4]) -> Iterator[_T]:
    ...


def flatten(iterable: Any, *, level: int = 1) -> Iterator[Any]:
    level = int(level)
    if level == 1:
        return (yield from chain.from_iterable(iterable))
    if not (2 <= level <= 4):
        raise ValueError("'level' must be in ]0;4]")
    for it in iterable:
        yield from flatten(it, level=level - 1)  # type: ignore[call-overload]


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
