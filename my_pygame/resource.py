# -*- coding: Utf-8 -*

from __future__ import annotations
from os.path import join
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, Type, TypeVar, Union, cast, get_args
from abc import ABCMeta, abstractmethod

from pygame.surface import Surface
from pygame.mixer import Sound
from pygame.font import Font

from .path import set_constant_directory, set_constant_file
from .surface import load_image

__all__ = ["ResourceLoader", "ImageLoader", "SoundLoader", "FontLoader", "MusicLoader", "MetaResourceManager", "ResourceManager"]

_T = TypeVar("_T")


class ResourceLoader(Generic[_T], metaclass=ABCMeta):
    def __init__(self, /, filepath: str) -> None:
        super().__init__()
        self.__filepath: str = set_constant_file(filepath)

    def __repr__(self, /) -> str:
        return f"{type(self).__name__}({self.filepath})"

    @abstractmethod
    def load(self, /) -> _T:
        raise NotImplementedError

    @property
    def filepath(self, /) -> str:
        return self.__filepath

    @property
    def type(self, /) -> Type[_T]:
        return cast(Type[_T], get_args(getattr(type(self), "__orig_bases__")[0])[0])


class ImageLoader(ResourceLoader[Surface]):
    def load(self, /) -> Surface:
        return load_image(self.filepath)


class SoundLoader(ResourceLoader[Sound]):
    def load(self, /) -> Sound:
        return Sound(file=self.filepath)


class FontLoader(ResourceLoader[str]):
    def load(self, /) -> str:
        assert Font(self.filepath, 10)
        return self.filepath


class MusicLoader(ResourceLoader[str]):
    def load(self, /) -> str:
        assert Sound(file=self.filepath)
        return self.filepath


_ResourcePath = Union[str, List[Any], Tuple[Any, ...], Dict[Any, Any]]
_ResourceLoader = Union[ResourceLoader[Any], List[Any], Tuple[Any, ...], Dict[Any, Any]]


class _ResourceDescriptor:
    def __init__(
        self, /, path: _ResourcePath, loader: Callable[[str], ResourceLoader[Any]], directory: Optional[str] = None
    ) -> None:
        def get_resources_loader(path: _ResourcePath) -> _ResourceLoader:
            if isinstance(path, str):
                if isinstance(directory, str):
                    path = join(directory, path)
                resource_loader: ResourceLoader[Any] = loader(path)
                self.__nb_resources += 1
                return resource_loader
            if isinstance(path, list):
                return [get_resources_loader(p) for p in path]
            if isinstance(path, tuple):
                return tuple(get_resources_loader(p) for p in path)
            if isinstance(path, dict):
                return {key: get_resources_loader(value) for key, value in path.items()}
            raise TypeError(f"Unexpected path type: {type(path).__name__!r} ({path!r})")

        self.__nb_resources: int = 0
        self.__loader: _ResourceLoader = get_resources_loader(path)
        self.__resource: Any

    def __get__(self, obj: Any, objtype: Optional[type] = None, /) -> Any:
        return self.load()

    def __set__(self, obj: Any, value: Any, /) -> None:
        raise AttributeError("can't set attribute")

    def __delete__(self, obj: Any, /) -> None:
        self.unload()

    def load(self, /) -> Any:
        def load_all_resources(resource_loader: _ResourceLoader) -> Any:
            if isinstance(resource_loader, ResourceLoader):
                return resource_loader.load()
            if isinstance(resource_loader, list):
                return [load_all_resources(loader) for loader in resource_loader]
            if isinstance(resource_loader, tuple):
                return tuple(load_all_resources(loader) for loader in resource_loader)
            if isinstance(resource_loader, dict):
                return {key: load_all_resources(value) for key, value in resource_loader.items()}
            raise TypeError(f"Unexpected resource loader type: {type(resource_loader).__name__!r} ({resource_loader!r})")

        resource: Any
        try:
            resource = self.__resource
        except AttributeError:
            self.__resource = resource = load_all_resources(self.__loader)
        return resource

    def unload(self, /) -> None:
        try:
            del self.__resource
        except AttributeError:
            pass

    @property
    def nb_resources(self, /) -> int:
        return self.__nb_resources

    @property
    def nb_loaded_resources(self, /) -> int:
        try:
            self.__resource
        except AttributeError:
            return 0
        return self.__nb_resources


class MetaResourceManager(type):
    def __new__(metacls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> MetaResourceManager:
        namespace["__resources_files__"] = resources = namespace.get("__resources_files__", dict())

        annotations: Dict[str, Union[type, str]] = namespace.get("__annotations__", dict())
        for attr_name in ["__resources_files__", "__resources_directory__", "__resource_loader__"]:
            annotations.pop(attr_name, None)
        for attr_name in annotations:
            if attr_name not in resources:
                raise KeyError(f"Missing {attr_name!r} key in '__resources_files__' dict")

        directory: Optional[str] = namespace.get("__resources_directory__")
        if directory is not None:
            directory = set_constant_directory(directory)
        namespace["__resources_directory__"] = directory

        for resource_name, resource_path in resources.items():
            namespace[resource_name] = _ResourceDescriptor(resource_path, namespace["__resource_loader__"], directory)

        return super().__new__(metacls, name, bases, namespace, **extra)

    def __init__(cls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> None:
        super().__init__(name, bases, namespace, **extra)

        cls.__resources_directory__: Optional[str]
        cls.__resources_files__: Dict[str, _ResourceDescriptor]
        cls.__resource_loader__: Callable[[str], ResourceLoader[Any]]
        cls.__resources: Dict[str, _ResourceDescriptor] = {
            name: value for name, value in vars(cls).items() if isinstance(value, _ResourceDescriptor)
        }

    def __setattr__(cls, /, name: str, value: Any) -> None:
        try:
            resources: Dict[str, _ResourceDescriptor] = cls.__resources
        except AttributeError:
            pass
        else:
            if name in resources:
                resources[name].__set__(None, value)
                return
        super().__setattr__(name, value)

    def __delattr__(cls, /, name: str) -> None:
        if name in cls.__resources:
            cls.__resources[name].__delete__(None)
        else:
            super().__delattr__(name)

    def get_total_nb_resources(cls, /) -> int:
        return sum(resource.nb_resources for resource in cls.__resources.values())

    def get_nb_loaded_resources(cls, /) -> int:
        return sum(resource.nb_loaded_resources for resource in cls.__resources.values())

    def load(cls, /, *resources: str) -> None:
        descriptors: Dict[str, _ResourceDescriptor] = cls.__resources
        for name in resources:
            descriptors[name].load()

    def load_all_resources(cls, /) -> None:
        for resource in cls.__resources.values():
            resource.load()

    def unload(cls, /, *resources: str) -> None:
        descriptors: Dict[str, _ResourceDescriptor] = cls.__resources
        for name in resources:
            descriptors[name].unload()

    def unload_all_resources(cls, /) -> None:
        for resource in cls.__resources.values():
            resource.unload()


class ResourceManager(metaclass=MetaResourceManager):
    __resources_directory__: Optional[str] = None
    __resources_files__: Dict[str, _ResourcePath]
    __resource_loader__: Callable[[str], ResourceLoader[Any]]
