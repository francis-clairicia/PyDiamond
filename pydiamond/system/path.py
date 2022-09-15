# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Path utils module"""

from __future__ import annotations

__all__ = ["ConstantFileNotFoundError", "set_constant_directory", "set_constant_file"]


import os.path as os_path
from typing import Any, overload

from ..environ.executable import get_executable_path


class ConstantFileNotFoundError(FileNotFoundError):
    def __init__(self, filename: str, message: str | None = None) -> None:
        if message:
            message = f"{filename!r}: {message}"
        else:
            message = f"{filename!r} not found"
        super().__init__(message)
        self.filename = filename
        self.filename2 = None


def __set_path(
    *paths: str,
    raise_error: bool = True,
    error_msg: str | None = None,
    relative_to_cwd: bool = False,
) -> str:
    all_path = os_path.join(*paths)
    if not relative_to_cwd and not os_path.isabs(all_path):
        all_path = os_path.join(os_path.abspath(os_path.dirname(get_executable_path())), all_path)
    all_path = os_path.realpath(all_path)
    if raise_error and not os_path.exists(all_path):
        raise ConstantFileNotFoundError(all_path, message=error_msg)
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


def set_constant_directory(path: str, *paths: str, raise_error: bool = True, **kwargs: Any) -> str:
    path = __set_path(path, *paths, raise_error=raise_error, **kwargs)
    if raise_error and not os_path.isdir(path):
        raise NotADirectoryError(path)
    return path


@overload
def set_constant_file(path: str, *paths: str, relative_to_cwd: bool = False) -> str:
    ...


@overload
def set_constant_file(path: str, *paths: str, raise_error: bool, relative_to_cwd: bool = False) -> str:
    ...


@overload
def set_constant_file(path: str, *paths: str, error_msg: str, relative_to_cwd: bool = False) -> str:
    ...


def set_constant_file(path: str, *paths: str, raise_error: bool = True, **kwargs: Any) -> str:
    path = __set_path(path, *paths, raise_error=raise_error, **kwargs)
    if raise_error and not os_path.isfile(path):
        if os_path.isdir(path):
            raise IsADirectoryError(path)
        raise PermissionError(path)
    return path
