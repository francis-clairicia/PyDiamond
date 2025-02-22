# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource manager module"""

from __future__ import annotations

__all__ = ["ResourceManager", "ResourceManagerMeta"]

from collections import ChainMap
from collections.abc import Callable, Mapping, Sequence
from contextlib import suppress
from os import PathLike, fspath
from types import MappingProxyType
from typing import AbstractSet, Any, NoReturn, final

from ..system.namespace import ClassNamespace, ClassNamespaceMeta
from ..system.object import mro
from .abc import Resource, ResourcesLocation
from .file import ResourcesDirectory
from .loader import AbstractResourceLoader

type _ResourcePath = str | PathLike[str] | Sequence["_ResourcePath"] | Mapping[Any, "_ResourcePath"]
type _ResourceLoader = AbstractResourceLoader[Any] | tuple["_ResourceLoader", ...] | dict[Any, "_ResourceLoader"]


class _ResourceDescriptor:
    def __init__(
        self,
        path: _ResourcePath,
        loader: Callable[[Resource], AbstractResourceLoader[Any]],
        location: ResourcesLocation,
    ) -> None:
        def get_resources_loader(path: _ResourcePath) -> _ResourceLoader:
            if isinstance(path, (str, PathLike)):
                path = fspath(path)
                resource_loader: AbstractResourceLoader[Any] = loader(location.get_resource(path))
                self.__nb_resources += 1
                return resource_loader
            if isinstance(path, (list, tuple, set, frozenset, Sequence, AbstractSet)):
                return tuple(get_resources_loader(p) for p in path)
            if isinstance(path, (dict, Mapping)):
                return {key: get_resources_loader(value) for key, value in path.items()}
            raise TypeError(f"Unexpected path type: {type(path).__name__!r} ({path!r})")

        self.__nb_resources: int = 0
        self.__loader: _ResourceLoader = get_resources_loader(path)
        self.__resource: Any

    def __get__(self, obj: Any, objtype: type | None = None, /) -> Any:
        try:
            return self.__resource
        except AttributeError:
            raise AttributeError("Resource not loaded") from None

    def __set__(self, obj: Any, value: Any, /) -> NoReturn:
        raise AttributeError("can't set attribute")

    def __delete__(self, obj: Any, /) -> None:
        self.unload()

    def load(self) -> None:
        try:
            self.__resource
        except AttributeError:
            pass
        else:
            return
        load_all_resources = _ResourceDescriptor.__load_all_resources
        resource: Any = load_all_resources(self.__loader)
        self.__resource = resource

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


class _LazyAutoLoadResourceDescriptor(_ResourceDescriptor):
    def __get__(self, obj: Any, objtype: type | None = None, /) -> Any:
        get_resource = super().__get__
        try:
            return get_resource(obj, objtype)
        except AttributeError:
            self.load()
            return get_resource(obj, objtype)


class ResourceManagerMeta(ClassNamespaceMeta):
    def __new__[Self: ResourceManagerMeta](
        mcs: type[Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        autoload: bool = False,
        **kwargs: Any,
    ) -> Self:
        namespace_including_bases: ChainMap[str, Any] = ChainMap(namespace, *map(vars, mro(*bases)))  # type: ignore[arg-type]

        resources: dict[str, Any] = namespace_including_bases.setdefault("__resources_files__", dict())

        annotations: dict[str, type | str] = dict(namespace_including_bases.get("__annotations__", dict()))
        for attr_name in ["__resources_files__", "__resources_location__", "__resource_loader__"]:
            annotations.pop(attr_name, None)
        for attr_name in annotations:
            if attr_name not in resources:
                raise KeyError(f"Missing {attr_name!r} key in '__resources_files__' dict")
        for attr_name in resources:
            if attr_name not in annotations:
                raise KeyError(f"Missing {attr_name!r} annotation")

        try:
            cls_defined_location: str | PathLike[str] | ResourcesLocation | None = namespace["__resources_location__"]
        except KeyError:
            pass
        else:
            if cls_defined_location is None:
                namespace.pop("__resources_location__")
            elif not isinstance(cls_defined_location, ResourcesLocation):
                cls_defined_location = ResourcesDirectory(cls_defined_location, relative_to_cwd=False)
                namespace["__resources_location__"] = cls_defined_location

        if resources:
            location: ResourcesLocation | None = namespace_including_bases.get("__resources_location__")
            if location is None:
                location = ResourcesDirectory(".", relative_to_cwd=False)

            resource_loader: Callable[[Resource], AbstractResourceLoader[Any]]
            for resource_name, resource_path in resources.items():
                resource_loader = namespace_including_bases["__resource_loader__"]
                if autoload:
                    namespace[resource_name] = _LazyAutoLoadResourceDescriptor(resource_path, resource_loader, location)
                else:
                    namespace[resource_name] = _ResourceDescriptor(resource_path, resource_loader, location)

        cls = super().__new__(mcs, name, bases, namespace, frozen=True, **kwargs)
        if resources:
            cls = final(cls)
        return cls

    def __init__(cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
        cls.__resources_location__: ResourcesLocation | None
        cls.__resources_files__: dict[str, _ResourceDescriptor]
        cls.__resource_loader__: Callable[[str], AbstractResourceLoader[Any]]
        cls.__resources: dict[str, _ResourceDescriptor] = {
            name: value for name, value in vars(cls).items() if isinstance(value, _ResourceDescriptor)
        }
        super().__init__(name, bases, namespace, frozen=True, **kwargs)

    def __getattribute__(self, __name: str) -> Any:
        if __name == "__resource_location__":
            try:
                return super().__getattribute__(__name)
            except AttributeError:
                return None
        return super().__getattribute__(__name)

    def __delattr__(cls, name: str, /) -> None:
        if name in cls.__resources:
            cls.__resources[name].unload()
        else:
            super().__delattr__(name)

    def get_resource_names(self) -> list[str]:
        return list(self.__resources)

    def get_total_nb_resources(cls) -> int:
        return sum(resource.nb_resources for resource in cls.__resources.values())

    def get_nb_loaded_resources(cls) -> int:
        return sum(resource.nb_loaded_resources for resource in cls.__resources.values())

    def load(cls, *resources: str) -> None:
        resources_dict: dict[str, _ResourceDescriptor] = cls.__resources
        if len(resources) != len(set(resources)):
            raise ValueError("Resource name duplicate")
        for name in resources:
            resources_dict[name].load()

    def load_and_get(cls, resource: str) -> Any:
        resources_dict: dict[str, _ResourceDescriptor] = cls.__resources
        resource_obj = resources_dict[resource]
        try:
            return resource_obj.__get__(None)
        except AttributeError:
            resource_obj.load()
            return resource_obj.__get__(None)

    def load_all_resources(cls) -> None:
        for resource in cls.__resources.values():
            resource.load()

    def unload(cls, *resources: str) -> None:
        resources_dict: dict[str, _ResourceDescriptor] = cls.__resources
        if len(resources) != len(set(resources)):
            raise ValueError("Resource name duplicate")
        for name in resources:
            resources_dict[name].unload()

    def unload_all_resources(cls) -> None:
        for resource in cls.__resources.values():
            resource.unload()


class ResourceManager(ClassNamespace, metaclass=ResourceManagerMeta):
    __resources_location__: str | PathLike[str] | ResourcesLocation | None
    __resources_files__: dict[str, _ResourcePath]
    __resource_loader__: Callable[[Resource], AbstractResourceLoader[Any]]
