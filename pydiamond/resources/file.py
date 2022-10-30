# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Filesystem resource module"""

from __future__ import annotations

__all__ = [
    "FileResource",
    "ResourcesDirectory",
]

from os import PathLike, fsdecode
from os.path import basename
from pathlib import Path
from typing import BinaryIO, ContextManager

from ..system.object import Object
from ..system.path import set_constant_directory, set_constant_file
from .abc import Resource, ResourcesLocation


@Resource.register
class FileResource(Object):
    __slots__ = ("__f", "__h", "__weakref__")

    def __init__(self, filepath: str | bytes | PathLike[str] | PathLike[bytes]) -> None:
        filepath = set_constant_file(fsdecode(filepath), relative_to_cwd=True)
        self.__f: str = filepath

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self.__f!r})>"

    def __eq__(self, __o: object, /) -> bool:
        if not isinstance(__o, FileResource):
            return NotImplemented
        return __o.__f == self.__f

    def __ne__(self, __o: object) -> bool:
        return not (self == __o)

    def __hash__(self) -> int:
        self.__h: int
        try:
            return self.__h
        except AttributeError:
            self.__h = h = hash((type(self), self.__f))
            return h

    def as_file(self) -> ContextManager[Path]:
        from contextlib import nullcontext

        return nullcontext(Path(self.__f))

    def open(self) -> BinaryIO:
        return open(self.__f, "rb")

    @property
    def path(self) -> str:
        return self.__f

    @property
    def name(self) -> str:
        return basename(self.__f)


@ResourcesLocation.register
class ResourcesDirectory(Object):
    __slots__ = ("__d", "__h", "__weakref__")

    def __init__(self, directory: str | bytes | PathLike[str] | PathLike[bytes], *, relative_to_cwd: bool = False) -> None:
        directory = fsdecode(directory)
        directory = set_constant_directory(directory, relative_to_cwd=relative_to_cwd, error_msg="Resource directory not found")
        self.__d: Path = Path(directory)

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self.__d!r})>"

    def __eq__(self, __o: object, /) -> bool:
        if not isinstance(__o, ResourcesDirectory):
            return NotImplemented
        return __o.__d == self.__d

    def __ne__(self, __o: object) -> bool:
        return not (self == __o)

    def __hash__(self) -> int:
        self.__h: int
        try:
            return self.__h
        except AttributeError:
            self.__h = h = hash((type(self), self.__d))
            return h

    def get_resource(self, resource: str) -> FileResource:
        path = self.__d
        return FileResource(path / resource)

    @property
    def path(self) -> Path:
        return self.__d
