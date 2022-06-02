# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Exception utility module"""

__all__ = ["noexcept"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import inspect
import os
import sys
from typing import Any, Callable, NoReturn, ParamSpec, TypeVar

from .utils.functools import wraps

_P = ParamSpec("_P")
_R = TypeVar("_R")


def noexcept(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    def abort() -> NoReturn:
        try:
            import traceback

            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
        finally:
            os.abort()

    exit_exceptions: tuple[type[BaseException], ...] = (SystemExit, KeyboardInterrupt)

    if inspect.isgeneratorfunction(func):
        exit_exceptions += (StopIteration, GeneratorExit)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return (yield from func(*args, **kwargs))  # type: ignore[misc]
            except exit_exceptions:
                raise
            except:
                abort()

    else:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exit_exceptions:
                raise
            except:
                abort()

    return wrapper
