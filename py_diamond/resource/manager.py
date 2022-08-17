# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource manager module"""

from __future__ import annotations

__all__ = ["ResourceManager", "ResourceManagerMeta"]


from contextlib import suppress
from os.path import join
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence, TypeAlias

from ..system.path import set_constant_directory
from .loader import AbstractResourceLoader

_ResourcePath: TypeAlias = str | Sequence["_ResourcePath"] | Mapping[Any, "_ResourcePath"]  # type: ignore[misc]
_ResourceLoader: TypeAlias = AbstractResourceLoader[Any] | tuple["_ResourceLoader", ...] | dict[Any, "_ResourceLoader"]  # type: ignore[misc]


class _ResourceDescriptor:
    def __init__(
        self, path: _ResourcePath, loader: Callable[[str], AbstractResourceLoader[Any]], directory: str | None = None
    ) -> None:
        def get_resources_loader(path: _ResourcePath) -> _ResourceLoader:
            if isinstance(path, str):
                if isinstance(directory, str):
                    path = join(directory, path)
                resource_loader: AbstractResourceLoader[Any] = loader(path)
                self.__nb_resources += 1
                return resource_loader
            if isinstance(path, (list, tuple, set, frozenset, Sequence)):
                return tuple(get_resources_loader(p) for p in path)
            if isinstance(path, (dict, Mapping)):
                return {key: get_resources_loader(value) for key, value in path.items()}
            raise TypeError(f"Unexpected path type: {type(path).__name__!r} ({path!r})")

        self.__nb_resources: int = 0
        self.__loader: _ResourceLoader = get_resources_loader(path)
        self.__resource: Any

    def __get__(self, obj: Any, objtype: type | None = None, /) -> Any:
        return self.load()

    def __set__(self, obj: Any, value: Any, /) -> None:
        raise AttributeError("can't set attribute")

    def __delete__(self, obj: Any, /) -> None:
        self.unload()

    def load(self) -> Any:
        try:
            return self.__resource
        except AttributeError:
            pass
        load_all_resources = _ResourceDescriptor.__load_all_resources
        resource: Any = load_all_resources(self.__loader)
        self.__resource = resource
        return resource

    @staticmethod
    def __load_all_resources(resource_loader: _ResourceLoader) -> Any:
        load_all_resources = _ResourceDescriptor.__load_all_resources
        if isinstance(resource_loader, AbstractResourceLoader):
            return resource_loader.load()
        if isinstance(resource_loader, tuple):
            return tuple(load_all_resources(loader) for loader in resource_loader)
        if isinstance(resource_loader, dict):
            return MappingProxyType({key: load_all_resources(value) for key, value in resource_loader.items()})
        raise TypeError(f"Unexpected resource loader type: {type(resource_loader).__name__!r} ({resource_loader!r})")

    def unload(self) -> None:
        with suppress(AttributeError):
            del self.__resource

    @property
    def nb_resources(self) -> int:
        return self.__nb_resources

    @property
    def nb_loaded_resources(self) -> int:
        try:
            self.__resource
        except AttributeError:
            return 0
        return self.__nb_resources


class ResourceManagerMeta(type):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> ResourceManagerMeta:
        resources: dict[str, Any] = namespace.setdefault("__resources_files__", dict())

        annotations: dict[str, type | str] = namespace.setdefault("__annotations__", dict())
        annotations = annotations.copy()
        for attr_name in ["__resources_files__", "__resources_directory__", "__resource_loader__"]:
            annotations.pop(attr_name, None)
        for attr_name in annotations:
            if attr_name not in resources:
                raise KeyError(f"Missing {attr_name!r} key in '__resources_files__' dict")
        for attr_name in resources:
            if attr_name not in annotations:
                raise KeyError(f"Missing {attr_name!r} annotation")

        directory: str | None = namespace.get("__resources_directory__")
        if directory is not None:
            directory = set_constant_directory(directory, error_msg="Resource directory not found")
        namespace["__resources_directory__"] = directory

        for resource_name, resource_path in resources.items():
            namespace[resource_name] = _ResourceDescriptor(resource_path, namespace["__resource_loader__"], directory)

        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def __init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
        super().__init__(name, bases, namespace, **kwargs)

        cls.__resources_directory__: str | None
        cls.__resources_files__: dict[str, _ResourceDescriptor]
        cls.__resource_loader__: Callable[[str], AbstractResourceLoader[Any]]
        cls.__resources: dict[str, _ResourceDescriptor] = {
            name: value for name, value in vars(cls).items() if isinstance(value, _ResourceDescriptor)
        }

    def __setattr__(cls, name: str, value: Any, /) -> None:
        try:
            resources: dict[str, _ResourceDescriptor] = cls.__resources
        except AttributeError:
            pass
        else:
            if name in resources:
                resources[name].__set__(None, value)
                return
        super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name in cls.__resources:
            cls.__resources[name].__delete__(None)
        else:
            super().__delattr__(name)

    def get_total_nb_resources(cls) -> int:
        return sum(resource.nb_resources for resource in cls.__resources.values())

    def get_nb_loaded_resources(cls) -> int:
        return sum(resource.nb_loaded_resources for resource in cls.__resources.values())

    def load(cls, *resources: str) -> None:
        descriptors: dict[str, _ResourceDescriptor] = cls.__resources
        for name in resources:
            descriptors[name].load()

    def load_all_resources(cls) -> None:
        for resource in cls.__resources.values():
            resource.load()

    def unload(cls, *resources: str) -> None:
        descriptors: dict[str, _ResourceDescriptor] = cls.__resources
        for name in resources:
            descriptors[name].unload()

    def unload_all_resources(cls) -> None:
        for resource in cls.__resources.values():
            resource.unload()


class ResourceManager(metaclass=ResourceManagerMeta):
    __resources_directory__: str | None = None
    __resources_files__: dict[str, _ResourcePath]
    __resource_loader__: Callable[[str], AbstractResourceLoader[Any]]
