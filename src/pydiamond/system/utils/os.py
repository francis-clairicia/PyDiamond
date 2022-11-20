# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""os utility module"""

from __future__ import annotations

__all__ = ["fork", "has_fork", "register_at_fork_if_supported"]

import os
from typing import Any, Callable, overload

_NO_DEFAULT: Any = object()


def fork() -> int:
    try:
        fork: Callable[[], int] = getattr(os, "fork")
    except AttributeError:
        pass
    else:
        return fork()
    raise NotImplementedError("Not supported on this platform")


def has_fork() -> bool:
    return hasattr(os, "fork")


@overload
def register_at_fork_if_supported(
    *,
    before: Callable[[], Any],
    after_in_parent: Callable[[], Any] = ...,
    after_in_child: Callable[[], Any] = ...,
) -> None:
    ...


@overload
def register_at_fork_if_supported(
    *,
    after_in_parent: Callable[[], Any],
    before: Callable[[], Any] = ...,
    after_in_child: Callable[[], Any] = ...,
) -> None:
    ...


@overload
def register_at_fork_if_supported(
    *,
    after_in_child: Callable[[], Any],
    before: Callable[[], Any] = ...,
    after_in_parent: Callable[[], Any] = ...,
) -> None:
    ...


def register_at_fork_if_supported(
    *,
    before: Callable[[], Any] = _NO_DEFAULT,
    after_in_parent: Callable[[], Any] = _NO_DEFAULT,
    after_in_child: Callable[[], Any] = _NO_DEFAULT,
) -> None:
    kwargs: dict[str, Any] = {}
    if before is not _NO_DEFAULT:
        kwargs["before"] = before
    if after_in_parent is not _NO_DEFAULT:
        kwargs["after_in_parent"] = after_in_parent
    if after_in_child is not _NO_DEFAULT:
        kwargs["after_in_child"] = after_in_child
    if not kwargs:
        raise TypeError("At least one argument is required")
    for param, argument in kwargs.items():
        if not callable(argument):
            msg = f"{param}: Expected callable, not {object.__repr__(argument)}"
            raise TypeError(msg)
    try:
        register_at_fork: Callable[..., None] = getattr(os, "register_at_fork")
    except AttributeError:
        return
    return register_at_fork(**kwargs)
