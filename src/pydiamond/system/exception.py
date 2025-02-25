# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Exception utility module"""

from __future__ import annotations

__all__ = ["noexcept"]

import inspect
import os
import sys
from collections.abc import AsyncGenerator, Callable
from typing import Any, NoReturn

from .utils.functools import wraps


def noexcept[**_P, _R](func: Callable[_P, _R], /) -> Callable[_P, _R]:
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
        exit_exceptions += (GeneratorExit,)

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return (yield from func(*args, **kwargs))
            except exit_exceptions:
                raise
            except BaseException:
                abort()

    elif inspect.isasyncgenfunction(func):
        exit_exceptions += (GeneratorExit,)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                async_gen: AsyncGenerator[Any, Any] = func(*args, **kwargs)
                # Reproduced the pure python implementation of the 'yield from' statement
                # See https://peps.python.org/pep-0380/#formal-semantics
                _y = await anext(async_gen)
                while True:
                    try:
                        _s = yield _y
                    except GeneratorExit:
                        await async_gen.aclose()
                        raise
                    except BaseException:
                        _y = await async_gen.athrow(*sys.exc_info())
                    else:
                        _y = await async_gen.asend(_s)
            except StopAsyncIteration:
                return
            except exit_exceptions:
                raise
            except BaseException:
                abort()

    elif inspect.iscoroutinefunction(func):

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await func(*args, **kwargs)
            except exit_exceptions:
                raise
            except BaseException:
                abort()

    else:

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return func(*args, **kwargs)
            except exit_exceptions:
                raise
            except BaseException:
                abort()

    return wrapper
