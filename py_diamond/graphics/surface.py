# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Surface module"""

__all__ = [
    "Surface",
    "create_surface",
    "load_image",
    "save_image",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import pygame.image
from pygame import encode_file_path

if pygame.image.get_extended():  # Should be true as we explicitly query for SDL_image at package initialization
    from pygame.image import load_extended as _pg_image_load, save_extended as _pg_image_save
else:
    from pygame.image import load as _pg_image_load, save as _pg_image_save

from pygame.surface import Surface

from .color import TRANSPARENT, Color

del pygame


def create_surface(size: tuple[float, float], *, convert_alpha: bool = True, default_color: Color = TRANSPARENT) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size)
    if convert_alpha:
        s = s.convert_alpha()
    else:
        s = s.convert()
    s.fill(default_color)
    return s


def load_image(file: str, convert: bool = True) -> Surface:
    image: Surface = _pg_image_load(encode_file_path(file))
    if convert:
        return image.convert_alpha()
    return image


def save_image(image: Surface, file: str) -> None:
    return _pg_image_save(image, encode_file_path(file))
