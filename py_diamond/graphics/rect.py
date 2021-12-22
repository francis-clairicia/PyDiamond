# -*- coding: Utf-8 -*

__all__ = ["Rect", "pg_rect_convert"]

from pygame.rect import Rect as _Rect


class Rect(_Rect):
    pass


def pg_rect_convert(rect: _Rect) -> Rect:
    return Rect(rect.topleft, rect.size)
