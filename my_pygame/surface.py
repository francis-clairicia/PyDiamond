# -*- coding: Utf-8 -*

from typing import Literal, Tuple, TypedDict
from os.path import splitext
import bz2
import pickle

import pygame
import pygame.image

from pygame.surface import Surface

__ignore_imports__: Tuple[str, ...] = tuple(globals())


def create_surface(size: Tuple[float, float], *, convert_alpha: bool = True) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size)
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
    format: Literal["p", "RGB", "RGBX", "RGBA", "ARGB"]


def load_image(file: str) -> Surface:
    image: Surface
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        image = pygame.image.load(file)
    else:
        with bz2.open(file, mode="rb", compresslevel=9) as f:
            buffer_dict: _BufferDict = pickle.loads(f.read())
        image = pygame.image.fromstring(buffer_dict["string"], buffer_dict["size"], buffer_dict["format"])
    return image.convert_alpha()


def save_image(image: Surface, file: str, *, format: Literal["p", "RGB", "RGBX", "RGBA", "ARGB"] = "ARGB") -> None:
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        return pygame.image.save(image, file)

    buffer_dict: _BufferDict = {"string": pygame.image.tostring(image, format), "size": image.get_size(), "format": format}
    with bz2.open(file, mode="wb", compresslevel=9) as f:
        f.write(pickle.dumps(buffer_dict))


__all__ = [n for n in globals() if not n.startswith("_") and n not in __ignore_imports__]
