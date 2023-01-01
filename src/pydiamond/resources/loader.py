# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource loader module"""

from __future__ import annotations

__all__ = ["AbstractResourceLoader", "FontLoader", "ImageLoader", "MusicLoader", "SoundLoader"]

from abc import abstractmethod
from typing import Generic, TypeVar

from ..audio.music import Music
from ..audio.sound import Sound
from ..graphics.font import FontFactory
from ..graphics.surface import Surface, load_image_resource
from ..system.object import Object
from .abc import Resource

_T = TypeVar("_T")


class AbstractResourceLoader(Generic[_T], Object):
    __slots__ = ("__resource",)

    def __init__(self, resource: Resource) -> None:
        super().__init__()
        self.__resource: Resource = resource

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.__resource!r})"

    @abstractmethod
    def load(self) -> _T:
        raise NotImplementedError

    @property
    def resource(self) -> Resource:
        return self.__resource


class ImageLoader(AbstractResourceLoader[Surface]):
    __slots__ = ()

    def load(self) -> Surface:
        return load_image_resource(self.resource, convert=True)


class SoundLoader(AbstractResourceLoader[Sound]):
    __slots__ = ()

    def load(self) -> Sound:
        with self.resource.open() as fp:
            return Sound(file=fp)


class FontLoader(AbstractResourceLoader[FontFactory]):
    __slots__ = ()

    def load(self) -> FontFactory:
        return FontFactory(self.resource)


class MusicLoader(AbstractResourceLoader[Music]):
    __slots__ = ()

    def load(self) -> Music:
        return Music(self.resource)
