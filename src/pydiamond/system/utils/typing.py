# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["reflect_signature"]

from typing import Any, Callable, Concatenate, ParamSpec, TypeVar

_P = ParamSpec("_P")
_AnyP = ParamSpec("_AnyP")
_T = TypeVar("_T")
_S = TypeVar("_S")


def reflect_signature(src: Callable[_P, _T], /) -> Callable[[Callable[..., _T]], Callable[_P, _T]]:
    def decorator(f: Any) -> Any:
        setattr(f, "__wrapped__", src)
        return f

    return decorator


def reflect_method_signature(
    src: Callable[Concatenate[Any, _P], _T], /
) -> Callable[[Callable[Concatenate[_S, _AnyP], _T]], Callable[Concatenate[_S, _P], _T]]:
    def decorator(f: Any) -> Any:
        setattr(f, "__wrapped__", src)
        return f

    return decorator
