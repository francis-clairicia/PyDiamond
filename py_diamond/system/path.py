# -*- coding: Utf-8 -*

__all__ = ["set_constant_directory", "set_constant_file"]

import os.path
from sys import argv
from typing import Callable, Optional, overload


def __set_path(path_exists: Callable[[str], bool], *paths: str, raise_error: bool, error_msg: Optional[str]) -> str:
    all_path = os.path.join(*paths)
    if not os.path.isabs(all_path):
        all_path = os.path.join(os.path.abspath(os.path.dirname(argv[0])), all_path)
    all_path = os.path.realpath(all_path)
    if not path_exists(all_path) and raise_error:
        if error_msg:
            raise FileNotFoundError(f"{all_path!r}: {error_msg}")
        raise FileNotFoundError(f"{all_path!r} not found")
    return all_path


@overload
def set_constant_directory(path: str, *paths: str) -> str:
    ...


@overload
def set_constant_directory(path: str, *paths: str, raise_error: bool) -> str:
    ...


@overload
def set_constant_directory(path: str, *paths: str, error_msg: str) -> str:
    ...


def set_constant_directory(path: str, *paths: str, raise_error: bool = True, error_msg: Optional[str] = None) -> str:
    return __set_path(os.path.isdir, path, *paths, raise_error=raise_error, error_msg=error_msg)


@overload
def set_constant_file(path: str, *paths: str) -> str:
    ...


@overload
def set_constant_file(path: str, *paths: str, raise_error: bool) -> str:
    ...


@overload
def set_constant_file(path: str, *paths: str, error_msg: str) -> str:
    ...


def set_constant_file(path: str, *paths: str, raise_error: bool = True, error_msg: Optional[str] = None) -> str:
    return __set_path(os.path.isfile, path, *paths, raise_error=raise_error, error_msg=error_msg)
