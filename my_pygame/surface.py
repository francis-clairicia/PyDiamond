# -*- coding: Utf-8 -*

from typing import Tuple
import pygame
from pygame.surface import Surface


def create_surface(size: Tuple[float, float], *, convert_alpha: bool = True) -> Surface:
    s: Surface = Surface(size, flags=pygame.SRCALPHA)
    if convert_alpha:
        s = s.convert_alpha()
    return s
