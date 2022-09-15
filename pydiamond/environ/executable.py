# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment executable utils module

Get information about the execution environment using the declared functions.
"""

from __future__ import annotations

__all__ = [
    "get_executable_path",
    "get_main_script_path",
    "is_frozen_executable",
]

import os.path
import sys


def get_main_script_path() -> str:
    """Retrieve the path to the main script

    Returns the absolute path to the .py (or any else extension) file ran by the interpreter.
    """
    try:
        main_module = sys.modules["__main__"]
    except KeyError as exc:
        raise RuntimeError("Wait... How the '__main__' module cannot exist ?") from exc

    spec = main_module.__spec__
    path: str
    if spec and spec.origin:
        path = os.path.realpath(spec.origin)
    else:
        path = getattr(main_module, "__file__", None) or (os.path.realpath(sys.argv[0]) if sys.argv and sys.argv[0] else "")
        if not path:
            return ""
    return os.path.abspath(path)


def get_executable_path() -> str:
    """Retrieve the executable path

    Returns the absolute path to the executable file running the application.
    For 'frozen' scripts (by cx_Freeze or pyinstaller), returns the frozen executable filepath,
    otherwise, returns the main script path.
    """

    if is_frozen_executable():
        return sys.executable
    return get_main_script_path()


def is_frozen_executable() -> bool:
    """Test whether the script is 'frozen' or not

    Returns True if the running script was frozen to an embedded executable by external tools
    such as cx_Freeze or pyinstaller.
    """
    return True if getattr(sys, "frozen", False) else False
