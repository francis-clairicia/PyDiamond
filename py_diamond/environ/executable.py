# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment executable utils module"""

from __future__ import annotations

__all__ = [
    "get_executable_path",
    "get_main_script_path",
    "is_frozen_executable",
]

import os.path
import sys


def get_main_script_path() -> str:
    try:
        main_module = sys.modules["__main__"]
    except KeyError as exc:
        raise RuntimeError("Wait... How the '__main__' module cannot exist ?") from exc

    spec = main_module.__spec__
    if spec and spec.origin:
        path = os.path.realpath(spec.origin)
    else:
        path = getattr(main_module, "__file__", None) or os.path.realpath(sys.argv[0])
    return os.path.abspath(path)


def get_executable_path() -> str:
    if is_frozen_executable():
        return sys.executable
    return get_main_script_path()


def is_frozen_executable() -> bool:
    return True if getattr(sys, "frozen", False) else False
