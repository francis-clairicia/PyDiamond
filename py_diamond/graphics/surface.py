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
from typing import Any, Final, Tuple

import pygame
import pygame.image
from pygame.surface import Surface


def create_surface(size: Tuple[float, float], *, convert_alpha: bool = True) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size)
    if convert_alpha:
        s = s.convert_alpha()
        s.fill((0, 0, 0, 0))
    else:
        s = s.convert()
    return s


COMPILED_SURFACE_EXTENSION: Final[str] = ".surface"


class SurfaceUnpickler(pickle.Unpickler):
    def find_class(self, /, __module_name: str, __global_name: str) -> Any:
        if __module_name != "pygame.image" or __global_name != "fromstring":
            raise pickle.UnpicklingError(f"Trying to unpickle {__module_name}.{__global_name}")
        return super().find_class(__module_name, __global_name)


def load_image(file: str) -> Surface:
    image: Surface
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        image = pygame.image.load(file)
    else:
        try:
            with bz2.open(file, mode="rb", compresslevel=9) as f:
                image = SurfaceUnpickler(f).load()
        except (IOError, pickle.UnpicklingError) as exc:
            raise pygame.error(str(exc)) from exc
    return image


def save_image(image: Surface, file: str) -> None:
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        return pygame.image.save(image, file)

    with bz2.open(file, mode="wb", compresslevel=9) as f:
        f.write(pickle.dumps(image, protocol=pickle.HIGHEST_PROTOCOL))