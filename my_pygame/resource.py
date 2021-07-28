# -*- coding: Utf-8 -*

from __future__ import annotations
from re import split as re_split
from typing import Any, Dict, Generic, Iterator, List, Mapping, Tuple, Type, TypeVar, TypedDict, Union
from abc import ABCMeta, abstractmethod

from pygame.surface import Surface
from pygame.mixer import Sound
from pygame.font import Font

from .path import set_constant_file
from .surface import load_image

T = TypeVar("T")


class ResourceLoader(Generic[T], metaclass=ABCMeta):
    def __init__(self, filepath: str) -> None:
        super().__init__()
        self.__filepath: str = set_constant_file(*re_split(r"/|\\", filepath))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.filepath})"

    @abstractmethod
    def load(self) -> T:
        raise NotImplementedError

    @property
    def filepath(self) -> str:
        return self.__filepath


class ImageLoader(ResourceLoader[Surface]):
    def load(self) -> Surface:
        return load_image(self.filepath)


class SoundLoader(ResourceLoader[Sound]):
    def load(self) -> Sound:
        return Sound(file=self.filepath)


class FontLoader(ResourceLoader[str]):
    def load(self) -> str:
        assert Font(self.filepath, 10)
        return self.filepath


class MusicLoader(ResourceLoader[str]):
    def load(self) -> str:
        assert Sound(file=self.filepath)
        return self.filepath


_ResourcePath = Union[str, List[Any], Tuple[Any, ...], Dict[Any, Any]]
_ResourceLoader = Union[ResourceLoader[Any], List[Any], Tuple[Any, ...], Dict[Any, Any]]


class ResourcesFile(TypedDict):
    path: _ResourcePath
    loader: Type[ResourceLoader[Any]]


class ResourceManagerFiles(Mapping[str, ResourcesFile]):
    def __init__(self, default: Dict[str, ResourcesFile]) -> None:
        super().__init__()
        self.__default: Dict[str, ResourcesFile] = default

    def __getitem__(self, key: str) -> ResourcesFile:
        return self.__default[key]

    def __len__(self) -> int:
        return len(self.__default)

    def __iter__(self) -> Iterator[str]:
        return iter(self.__default)


class MetaResourceManager(type):
    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> MetaResourceManager:
        namespace["__resources_files__"] = resources = ResourceManagerFiles(namespace.get("__resources_files__", dict()))

        annotations: Dict[str, Union[type, str]] = namespace.get("__annotations__", dict())
        for attr_name in annotations:
            if attr_name == "__resources_files__":
                continue
            if attr_name not in resources:
                raise KeyError(f"Missing {repr(attr_name)} key in '__resources_files__' dict")

        return super().__new__(metacls, name, bases, namespace, **extra)

    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> None:
        super().__init__(name, bases, namespace, **extra)

        def get_resources_loader(name: str, path: _ResourcePath, loader: Type[ResourceLoader[Any]]) -> _ResourceLoader:
            if isinstance(path, str):
                resource_loader: ResourceLoader[Any] = loader(path)
                cls.__nb_resources[name] += 1
                cls.__total_nb_resources += 1
                return resource_loader
            if isinstance(path, list):
                return [get_resources_loader(name, p, loader) for p in path]
            if isinstance(path, tuple):
                return tuple(get_resources_loader(name, p, loader) for p in path)
            if isinstance(path, dict):
                return {key: get_resources_loader(name, value, loader) for key, value in path.items()}
            raise TypeError(f"Unexpected path type: {repr(type(path).__name__)} ({repr(path)})")

        cls.__resources_files__: ResourceManagerFiles
        cls.__total_nb_resources: int = 0
        cls.__nb_resources: Dict[str, int] = dict.fromkeys(cls.__resources_files__, 0)
        cls.__nb_loaded_resources: int = 0
        cls.__resources_loader: Dict[str, _ResourceLoader] = {
            name: get_resources_loader(name, file["path"], file["loader"]) for name, file in cls.__resources_files__.items()
        }

    def __setattr__(cls, name: str, value: Any) -> None:
        if name == "__resources_files__" or name in cls.__resources_files__:
            raise AttributeError("Resource attributes can't be set")
        return super().__setattr__(name, value)

    def __getattr__(cls, name: str) -> Any:
        if name in cls.__resources_files__:
            return cls.__get_resource(name)
        raise AttributeError(f"type object {repr(cls.__name__)} has no attribute {repr(name)}")

    def __delattr__(cls, name: str) -> None:
        if name in cls.__resources_files__:
            return cls.__erase_resource(name)
        return super().__delattr__(name)

    def get_total_nb_resources(cls) -> int:
        return cls.__total_nb_resources

    def get_nb_loaded_resources(cls) -> int:
        return cls.__nb_loaded_resources

    def load(cls, *resources: str) -> None:
        for resource in resources:
            if resource not in cls.__resources_files__:
                raise ValueError(f"{repr(resource)} is not a known resource")
            cls.__get_resource(resource)

    def load_all_resources(cls) -> None:
        for resource in cls.__resources_files__:
            cls.__get_resource(resource)

    def unload(cls, *resources: str) -> None:
        for resource in resources:
            if resource not in cls.__resources_files__:
                raise ValueError(f"{repr(resource)} is not a known resource")
            cls.__erase_resource(resource)

    def unload_all_resources(cls) -> None:
        for resource in cls.__resources_files__:
            cls.__erase_resource(resource)

    def __get_resource(cls, resource_name: str) -> Any:
        def load_all_resources(resource_loader: _ResourceLoader) -> Any:
            if isinstance(resource_loader, ResourceLoader):
                return resource_loader.load()
            if isinstance(resource_loader, list):
                return [load_all_resources(loader) for loader in resource_loader]
            if isinstance(resource_loader, tuple):
                return tuple(load_all_resources(loader) for loader in resource_loader)
            if isinstance(resource_loader, dict):
                return {key: load_all_resources(value) for key, value in resource_loader.items()}
            raise TypeError(f"Unexpected resource loader type: {repr(type(resource_loader).__name__)} ({repr(resource_loader)})")

        resource_attribute: str = cls.__get_resource_attribute(resource_name)
        resource: Any
        try:
            resource = getattr(cls, resource_attribute)
        except AttributeError:
            resource = load_all_resources(cls.__resources_loader[resource_name])
            setattr(cls, resource_attribute, resource)
            cls.__nb_loaded_resources += cls.__nb_resources[resource_name]
        return resource

    def __erase_resource(cls, resource: str) -> None:
        try:
            super().__delattr__(cls.__get_resource_attribute(resource))
        except AttributeError:
            pass
        else:
            cls.__nb_loaded_resources -= cls.__nb_resources[resource]

    @staticmethod
    def __get_resource_attribute(resource_name: str) -> str:
        return f"__resource_{resource_name}"


class ResourceManager(metaclass=MetaResourceManager):
    __resources_files__: Dict[str, ResourcesFile]

    @property
    def total_nb_resources(self) -> int:
        return type(self).get_total_nb_resources()

    @property
    def nb_loaded_resources(self) -> int:
        return type(self).get_nb_loaded_resources()
