# -*- coding: Utf-8 -*

from typing import Tuple, TypedDict
from os.path import splitext
import bz2
import pickle

import pygame
import pygame.image

from pygame.surface import Surface


def create_surface(size: Tuple[float, float], *, convert_alpha: bool = True) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size, pygame.HWSURFACE, depth=32)
    if convert_alpha:
        s = s.convert_alpha()
        s.fill((0, 0, 0, 0))
    else:
        s = s.convert()
    return s


COMPILED_SURFACE_EXTENSION: str = ".surface"


class _BufferDict(TypedDict):
    string: str
    size: Tuple[int, int]


def load_image(file: str) -> Surface:
    image: Surface
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        image = pygame.image.load(file)
    else:
        with bz2.open(file, mode="rb", compresslevel=9) as f:
            buffer_dict: _BufferDict = pickle.loads(f.read())
        image = pygame.image.fromstring(buffer_dict["string"], buffer_dict["size"], "RGBA")
    try:
        image = image.convert_alpha()
    except pygame.error:
        pass
    return image


def save_image(image: Surface, file: str) -> None:
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        return pygame.image.save(image, file)

    surface: Surface = Surface(image.get_size(), flags=pygame.SRCALPHA)
    surface.fill((0, 0, 0, 0))
    surface.blit(image, (0, 0))

    buffer_dict: _BufferDict = {"string": pygame.image.tostring(surface, "RGBA"), "size": surface.get_size()}
    with bz2.open(file, mode="wb", compresslevel=9) as f:
        f.write(pickle.dumps(buffer_dict))
