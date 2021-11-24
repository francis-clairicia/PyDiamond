# -*- coding: Utf-8 -*

__all__ = [
    "COMPILED_SURFACE_EXTENSION",
    "Surface",
    "create_surface",
    "load_image",
    "save_image",
]

import bz2
import pickle
from os.path import splitext
from typing import Tuple

import pygame
import pygame.image

from pygame.surface import Surface


def create_surface(size: Tuple[float, float], *, convert_alpha: bool = True) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface
    if not pygame.display.get_init():
        if convert_alpha:
            s = Surface(size, flags=pygame.SRCALPHA)
            s.fill((0, 0, 0, 0))
        else:
            s = Surface(size)
    else:
        s = Surface(size)
        if convert_alpha:
            s = s.convert_alpha()
            s.fill((0, 0, 0, 0))
        else:
            s = s.convert()
    return s


COMPILED_SURFACE_EXTENSION: str = ".surface"


def load_image(file: str) -> Surface:
    image: Surface
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        image = pygame.image.load(file)
    else:
        with bz2.open(file, mode="rb", compresslevel=9) as f:
            image = pickle.loads(f.read())
    return image


def save_image(image: Surface, file: str) -> None:
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        return pygame.image.save(image, file)

    with bz2.open(file, mode="wb", compresslevel=9) as f:
        f.write(pickle.dumps(image, protocol=pickle.HIGHEST_PROTOCOL))
