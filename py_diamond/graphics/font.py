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


def SysFont(
    name: Union[str, bytes, Iterable[Union[str, bytes]]],
    size: int,
    bold: bool = False,
    italic: bool = False,
) -> Font:
    font: Font = _SysFont(name, size, bold=bold, italic=italic, constructor=_font_constructor)  # type: ignore[no-untyped-call]
    return font


SysFont.__doc__ = _SysFont.__doc__


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
