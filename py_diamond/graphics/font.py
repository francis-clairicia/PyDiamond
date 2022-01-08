# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Font module"""

from __future__ import annotations

__all__ = ["Font", "SysFont"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Iterable, Union

import pygame.font
from pygame.font import Font as _Font
from pygame.sysfont import SysFont as _SysFont

pygame.font.init()


def SysFont(name: Union[str, bytes, Iterable[Union[str, bytes]]], size: int, bold: bool = False, italic: bool = False) -> Font:
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

    If optional constructor is provided, it must be a function with
    signature constructor(fontpath, size, bold, italic) which returns
    a Font instance. If None, a pygame.font.Font object is created.
    """

    font: Font = _SysFont(name, size, bold=bold, italic=italic, constructor=_font_constructor)  # type: ignore[no-untyped-call]
    return font


class Font(_Font):
    @staticmethod
    def get_default_font() -> str:
        return pygame.font.get_default_font()


def _font_constructor(fontpath: str, size: int, bold: bool, italic: bool) -> Font:
    font = Font(fontpath, size)
    if bold:
        font.set_bold(True)
    if italic:
        font.set_italic(True)
    return font
