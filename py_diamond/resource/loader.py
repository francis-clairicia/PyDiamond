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
from typing import Generic, Type, TypeVar, cast, get_args

from ..audio.sound import Sound
from ..graphics.font import Font
from ..graphics.surface import Surface, load_image
from ..system.path import set_constant_file

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
        assert Font(self.filepath, 10) is not None
        return self.filepath


class MusicLoader(ResourceLoader[str]):
    def load(self, /) -> str:
        assert Sound(file=self.filepath) is not None
        return self.filepath
