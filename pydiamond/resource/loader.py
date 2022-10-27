# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource loader module"""

from __future__ import annotations

__all__ = ["AbstractResourceLoader", "FontLoader", "ImageLoader", "MusicLoader", "SoundLoader"]

from abc import abstractmethod
from os import PathLike, fspath
from typing import Generic, TypeVar

from ..audio.music import Music
from ..audio.sound import Sound
from ..graphics.font import FontFactory
from ..graphics.surface import Surface, load_image
from ..system.object import Object
from ..system.path import set_constant_file

_T = TypeVar("_T")


class AbstractResourceLoader(Generic[_T], Object):

    __slots__ = ("__filepath",)

    def __init__(self, filepath: str | PathLike[str]) -> None:
        super().__init__()
        filepath = set_constant_file(fspath(filepath))
        self.__filepath: str = filepath

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.filepath})"

    @abstractmethod
    def load(self) -> _T:
        raise NotImplementedError

    @property
    def filepath(self) -> str:
        return self.__filepath


class ImageLoader(AbstractResourceLoader[Surface]):

    __slots__ = ()

    def load(self) -> Surface:
        return load_image(self.filepath)


class SoundLoader(AbstractResourceLoader[Sound]):

    __slots__ = ()

    def load(self) -> Sound:
        return Sound(file=self.filepath)


class FontLoader(AbstractResourceLoader[FontFactory]):

    __slots__ = ()

    def load(self) -> FontFactory:
        return FontFactory(self.filepath)


class MusicLoader(AbstractResourceLoader[Music]):

    __slots__ = ()

    def load(self) -> Music:
        return Music(self.filepath)
