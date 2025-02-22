# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource abstract base classes module"""

from __future__ import annotations

__all__ = [
    "PackageResource",
    "PackageType",
    "ResourcesPackage",
]

import importlib.resources as _importlib_resources
from importlib import import_module
from importlib.resources import Package as PackageType
from pathlib import Path
from types import ModuleType
from typing import IO, ContextManager

from ..system.object import Object
from .abc import Resource, ResourcesLocation


@Resource.register
class PackageResource(Object):
    __slots__ = ("__f", "__h", "__weakref__")

    def __init__(self, package: PackageType, resource: str) -> None:
        traversable = _importlib_resources.files(package).joinpath(resource)
        if not traversable.is_file():
            if traversable.is_dir():
                raise IsADirectoryError(traversable.name)
            raise FileNotFoundError(traversable.name)
        self.__f = traversable

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self.__f!r})>"

    def __eq__(self, __o: object, /) -> bool:
        if not isinstance(__o, PackageResource):
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
        return _importlib_resources.as_file(self.__f)

    def open(self) -> IO[bytes]:
        return self.__f.open("rb")

    @property
    def name(self) -> str:
        return self.__f.name


@ResourcesLocation.register
class ResourcesPackage(Object):
    __slots__ = ("__p", "__h", "__weakref__")

    def __init__(self, package: PackageType) -> None:
        if not isinstance(package, ModuleType):
            package = import_module(package)
        if package.__spec__ is None or package.__spec__.submodule_search_locations is None:
            raise ValueError("Invalid package")
        self.__p: ModuleType = package

    def __repr__(self) -> str:
        return f"<{type(self).__name__}({self.__p!r})>"

    def __eq__(self, __o: object, /) -> bool:
        if not isinstance(__o, ResourcesPackage):
            return NotImplemented
        return __o.__p == self.__p

    def __ne__(self, __o: object) -> bool:
        return not (self == __o)

    def __hash__(self) -> int:
        self.__h: int
        try:
            return self.__h
        except AttributeError:
            self.__h = h = hash((type(self), self.__p))
            return h

    def get_resource(self, resource: str) -> PackageResource:
        package = self.__p
        return PackageResource(package, resource)
