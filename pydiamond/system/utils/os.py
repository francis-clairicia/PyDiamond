# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
# mypy: no-warn-unused-ignores
"""os utility module"""

from __future__ import annotations

__all__ = ["HAS_FORK", "fork", "register_at_fork_if_applicable"]

from typing import Any, Callable, overload

try:
    from os import fork  # type: ignore[attr-defined]
except ImportError:

    def fork() -> int:
        raise NotImplementedError("Not supported on this platform")

    HAS_FORK = False
else:
    HAS_FORK = True


_NO_DEFAULT: Any = object()


@overload
def register_at_fork_if_applicable(
    *,
    before: Callable[[], Any],
    after_in_parent: Callable[[], Any] = ...,
    after_in_child: Callable[[], Any] = ...,
) -> None:
    ...


@overload
def register_at_fork_if_applicable(
    *,
    after_in_parent: Callable[[], Any],
    before: Callable[[], Any] = ...,
    after_in_child: Callable[[], Any] = ...,
) -> None:
    ...


@overload
def register_at_fork_if_applicable(
    *,
    after_in_child: Callable[[], Any],
    before: Callable[[], Any] = ...,
    after_in_parent: Callable[[], Any] = ...,
) -> None:
    ...


def register_at_fork_if_applicable(
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
    try:
        from os import register_at_fork  # type: ignore[attr-defined]
    except ImportError:
        return
    return register_at_fork(**kwargs)
