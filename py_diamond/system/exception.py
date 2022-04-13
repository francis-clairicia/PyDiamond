# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Exception utility module"""

__all__ = ["noexcept"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Any, Callable, ParamSpec, TypeVar

from .utils import wraps

_P = ParamSpec("_P")
_R = TypeVar("_R")


def noexcept(func: Callable[_P, _R], /) -> Callable[_P, _R]:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except (SystemExit, KeyboardInterrupt):
            raise
        except:
            import os
            import sys
            import traceback

            traceback.print_exc()
            sys.stdout.flush()
            sys.stderr.flush()
            os.abort()

    return wrapper
