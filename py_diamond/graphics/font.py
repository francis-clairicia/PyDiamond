# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Font module"""

from __future__ import annotations

__all__ = ["Font", "SysFont", "get_default_font", "match_font"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING, Any, Iterable

import pygame
import pygame.font
import pygame.freetype
import pygame.sysfont

from ..system.object import Object, final

if TYPE_CHECKING:
    from pygame._common import _FileArg  # pyright: reportMissingModuleSource=false


def get_fonts() -> list[str]:
    return pygame.font.get_fonts()


def get_default_font() -> str:
    return pygame.freetype.get_default_font()


def match_font(name: str | bytes | Iterable[str | bytes], bold: bool = False, italic: bool = False) -> str | None:
    return pygame.sysfont.match_font(name, bold=bold, italic=italic)  # type: ignore[no-any-return,no-untyped-call]


def SysFont(name: str | bytes | Iterable[str | bytes], size: int, bold: bool = False, italic: bool = False) -> Font:
    """SysFont(name, size, bold=False, italic=False) -> Font
    Create a pygame Font from system font resources.

    This will search the system fonts for the given font
    name. You can also enable bold or italic styles, and
    the appropriate system font will be selected if available.

    This will always return a valid Font object, and will
    fallback on the builtin pygame font if the given font
    is not found.

    Name can also be an iterable of font names, a string of
    comma-separated font names, or a bytes of comma-separated
    font names, in which case the set of names will be searched
    in order. Pygame uses a small set of common font aliases. If the
    specific font you ask for is not available, a reasonable
    alternative may be used.
    """

    def font_constructor(fontpath: str, size: int, bold: bool, italic: bool) -> Font:
        font: Font = Font(fontpath, size)
        font.wide = bold
        font.oblique = italic
        return font

    font: Font = pygame.sysfont.SysFont(name, size, bold=bold, italic=italic, constructor=font_constructor)  # type: ignore[no-untyped-call]
    return font


@final
class Font(pygame.freetype.Font, Object):
    __encode_file_path = staticmethod(pygame.encode_file_path)
    __get_default_resolution = staticmethod(pygame.freetype.get_default_resolution)
    __default_font = pygame.encode_file_path(get_default_font())

    def __init__(
        self,
        file: _FileArg | None,
        size: float = 0,
        font_index: int = 0,
        resolution: int = 0,
        ucs4: int = True,
    ) -> None:
        size = max(size, 1)
        bfile: Any
        if isinstance(file, str):
            try:
                bfile = self.__encode_file_path(file, ValueError)
            except ValueError:
                bfile = ""
        else:
            bfile = file
        if isinstance(bfile, bytes) and bfile == self.__default_font:
            file = None
        if file is None:
            resolution = int(self.__get_default_resolution() * 0.6875)
            if resolution == 0:
                resolution = 1
        else:
            resolution = 0
        super().__init__(file, size, font_index, resolution, ucs4)
        self.strength = 1.0 / 12.0
        self.kerning = False
        self.pad = True
        self.underline_adjustment = 1.0
        self.antialiased = True

    @property  # type: ignore[override,misc]
    @final
    def rotation(self) -> int:  # type: ignore[override]
        return super().rotation

    @rotation.setter
    def rotation(self, value: Any) -> None:
        raise AttributeError("'rotation' attribute is read-only")
