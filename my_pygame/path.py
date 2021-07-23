# -*- coding: Utf-8 -*

import os.path
from sys import argv
from typing import Callable, Optional


def __set_constant_path(
    path_exists: Callable[[str], bool], path: str, *paths: str, raise_error: bool = True, special_msg: Optional[str] = None
) -> str:
    all_path = os.path.join(path, *paths)
    if not os.path.isabs(all_path):
        all_path = os.path.join(os.path.abspath(os.path.dirname(argv[0])), all_path)
    all_path = os.path.realpath(all_path)
    if not path_exists(all_path) and raise_error:
        if special_msg:
            raise FileNotFoundError(f"{repr(all_path)}: {special_msg}")
        raise FileNotFoundError(f"{repr(all_path)} not found")
    return all_path


def set_constant_directory(path: str, *paths: str, raise_error: bool = True, special_msg: Optional[str] = None) -> str:
    return __set_constant_path(os.path.isdir, path, *paths, raise_error=raise_error, special_msg=special_msg)


def set_constant_file(path: str, *paths: str, raise_error: bool = True, special_msg: Optional[str] = None) -> str:
    return __set_constant_path(os.path.isfile, path, *paths, raise_error=raise_error, special_msg=special_msg)
