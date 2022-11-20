# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""collections utility module"""

from __future__ import annotations

__all__ = [
    "is_namedtuple_class",
]

from typing import Any


def is_namedtuple_class(o: type[Any]) -> bool:
    return (
        issubclass(o, tuple)
        and o is not tuple
        and all(
            callable(getattr(o, callable_attr, None))
            for callable_attr in (
                "_make",
                "_asdict",
                "_replace",
            )
        )
        and isinstance(getattr(o, "_fields", None), tuple)
    )
