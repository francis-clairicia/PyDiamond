from __future__ import annotations

__all__ = ["reflect_signature"]

from collections.abc import Callable
from typing import Any, Concatenate


def reflect_signature[**_P, _R](src: Callable[_P, _R], /) -> Callable[[Callable[..., _R]], Callable[_P, _R]]:
    def decorator(f: Any) -> Any:
        setattr(f, "__wrapped__", src)
        return f

    return decorator


def reflect_method_signature[**_P, _R, _S](
    src: Callable[Concatenate[Any, _P], _R], /
) -> Callable[[Callable[Concatenate[_S, ...], _R]], Callable[Concatenate[_S, _P], _R]]:
    def decorator(f: Any) -> Any:
        setattr(f, "__wrapped__", src)
        return f

    return decorator
