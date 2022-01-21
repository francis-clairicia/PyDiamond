# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Path utils module"""

__all__ = ["set_constant_directory", "set_constant_file"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os.path as os_path
from sys import argv
from typing import Any, Callable, overload


def __set_path(
    path_exists: Callable[[str], bool],
    *paths: str,
    raise_error: bool = True,
    error_msg: str | None = None,
    relative_to_cwd: bool = False,
) -> str:
    all_path = os_path.join(*paths)
    if not relative_to_cwd and not os_path.isabs(all_path):
        all_path = os_path.join(os_path.abspath(os_path.dirname(argv[0])), all_path)
    all_path = os_path.realpath(all_path)
    if not path_exists(all_path) and raise_error:
        if error_msg:
            raise FileNotFoundError(f"{all_path!r}: {error_msg}")
        raise FileNotFoundError(f"{all_path!r} not found")
    return all_path


@overload
def set_constant_directory(path: str, *paths: str, relative_to_cwd: bool = False) -> str:
    ...


@overload
def set_constant_directory(path: str, *paths: str, raise_error: bool, relative_to_cwd: bool = False) -> str:
    ...


@overload
def set_constant_directory(path: str, *paths: str, error_msg: str, relative_to_cwd: bool = False) -> str:
    ...


def set_constant_directory(path: str, *paths: str, error_msg: str | None = None, **kwargs: Any) -> str:
    return __set_path(os_path.isdir, path, *paths, error_msg=error_msg or "Not a directory", **kwargs)


@overload
def set_constant_file(path: str, *paths: str, relative_to_cwd: bool = False) -> str:
    ...


@overload
def set_constant_file(path: str, *paths: str, raise_error: bool, relative_to_cwd: bool = False) -> str:
    ...


@overload
def set_constant_file(path: str, *paths: str, error_msg: str, relative_to_cwd: bool = False) -> str:
    ...


def set_constant_file(path: str, *paths: str, **kwargs: Any) -> str:
    return __set_path(os_path.isfile, path, *paths, **kwargs)
