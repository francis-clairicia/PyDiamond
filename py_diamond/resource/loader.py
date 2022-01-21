# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource loader module"""

__all__ = ["FontLoader", "ImageLoader", "MusicLoader", "ResourceLoader", "SoundLoader"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from typing import Generic, Type, TypeVar

from pygame.mixer import Sound as _PygameSound

from ..audio.music import Music
from ..audio.sound import Sound
from ..graphics.font import Font
from ..graphics.surface import Surface, load_image
from ..system.path import set_constant_file

_T = TypeVar("_T")


class ResourceLoader(Generic[_T], metaclass=ABCMeta):

    __slots__ = ("__filepath",)

    def __init__(self, filepath: str) -> None:
        super().__init__()
        filepath = set_constant_file(filepath)
        self.__filepath: str = filepath

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.filepath})"

    @abstractmethod
    def load(self) -> _T:
        raise NotImplementedError

    @property
    def filepath(self) -> str:
        return self.__filepath

    @property
    @abstractmethod
    def type(self) -> Type[_T]:
        raise NotImplementedError


class ImageLoader(ResourceLoader[Surface]):

    __slots__ = ()

    def load(self) -> Surface:
        return load_image(self.filepath)

    @property
    def type(self) -> Type[Surface]:
        return Surface


class SoundLoader(ResourceLoader[Sound]):

    __slots__ = ()

    def load(self) -> Sound:
        return Sound(file=self.filepath)

    @property
    def type(self) -> Type[Sound]:
        return Sound


class FontLoader(ResourceLoader[str]):

    __slots__ = ()

    def load(self) -> str:
        Font(self.filepath, 10)
        return self.filepath

    @property
    def type(self) -> Type[str]:
        return str


class MusicLoader(ResourceLoader[Music]):

    __slots__ = ()

    def load(self) -> Music:
        _PygameSound(self.filepath)
        return Music(self.filepath)

    @property
    def type(self) -> Type[Music]:
        return Music


del _T
