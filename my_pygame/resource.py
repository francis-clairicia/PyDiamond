# -*- coding: Utf-8 -*

from __future__ import annotations
from re import split as re_split
from typing import Any, Dict, Generic, Tuple, Type, TypeVar, TypedDict
from abc import ABCMeta, abstractmethod

import pygame.image

from pygame.surface import Surface
from pygame.mixer import Sound
from pygame.font import Font

from .path import set_constant_file

T = TypeVar("T")


class ResourceLoader(Generic[T], metaclass=ABCMeta):
    def __init__(self, filepath: str) -> None:
        super().__init__()
        self.__filepath: str = set_constant_file(*re_split(r"/|\\", filepath))

    @abstractmethod
    def load(self) -> T:
        raise NotImplementedError

    @property
    def filepath(self) -> str:
        return self.__filepath


class ImageLoader(ResourceLoader[Surface]):
    def load(self) -> Surface:
        return pygame.image.load(self.filepath).convert_alpha()


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


class ResourcesFile(TypedDict):
    path: str
    loader: Type[ResourceLoader[Any]]


class MetaResourceManager(type):
    __resources_files__: Dict[str, ResourcesFile]

    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> MetaResourceManager:
        namespace["__resources_files__"] = namespace.get("__resources_files__", dict())
        namespace["__resources_loader__"] = dict()
        return super().__new__(metacls, name, bases, namespace, **extra)

    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> None:
        super().__init__(name, bases, namespace, **extra)
        cls.__resources_loader__: Dict[str, ResourceLoader[Any]] = {
            name: file["loader"](file["path"]) for name, file in cls.__resources_files__.items()
        }

    def __setattr__(cls, name: str, value: Any) -> None:
        if name in cls.__resources_files__:
            raise AttributeError("Resource attributes can't be set")
        return super().__setattr__(name, value)

    def __getattribute__(cls, name: str) -> Any:
        if name != "__resources_loader__" and name in cls.__resources_loader__:
            resource_attribute: str = f"_{cls.__name__}__{name}"
            resource: Any
            if not hasattr(cls, resource_attribute):
                resource = cls.__resources_loader__[name].load()
                setattr(cls, resource_attribute, resource)
            else:
                resource = getattr(cls, resource_attribute)
            return resource

        return super().__getattribute__(name)


class ResourceManager(metaclass=MetaResourceManager):
    __resources_files__: Dict[str, ResourcesFile]
