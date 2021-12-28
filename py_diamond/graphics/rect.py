# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

from __future__ import annotations

__all__ = ["Rect"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from pygame.rect import Rect as _Rect


class Rect(_Rect):
    @staticmethod
    def convert(pygame_rect: _Rect) -> Rect:
        return Rect(pygame_rect.topleft, pygame_rect.size)
