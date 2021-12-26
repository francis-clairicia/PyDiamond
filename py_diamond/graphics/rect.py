# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

__all__ = ["Rect", "pg_rect_convert"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from pygame.rect import Rect as _Rect


class Rect(_Rect):
    pass


def pg_rect_convert(rect: _Rect) -> Rect:
    return Rect(rect.topleft, rect.size)
