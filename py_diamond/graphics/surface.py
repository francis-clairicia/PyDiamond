# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Surface module"""

__all__ = [
    "COMPILED_SURFACE_EXTENSION",
    "Surface",
    "create_surface",
    "load_image",
    "save_image",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import bz2
import pickle
from os.path import splitext
from typing import Any, Final, Tuple

from pygame import error as _pg_error
from pygame.image import load as _pg_image_load, save as _pg_image_save
from pygame.surface import Surface

from .color import TRANSPARENT, Color


def create_surface(size: Tuple[float, float], *, convert_alpha: bool = True, default_color: Color = TRANSPARENT) -> Surface:
    size = (max(size[0], 0), max(size[1], 0))
    s: Surface = Surface(size)
    if convert_alpha:
        s = s.convert_alpha()
    else:
        s = s.convert()
    s.fill(default_color)
    return s


COMPILED_SURFACE_EXTENSION: Final[str] = ".surface"


class SurfaceUnpickler(pickle.Unpickler):
    def find_class(self, __module_name: str, __global_name: str) -> Any:
        if __module_name != "pygame.image" or __global_name != "fromstring":
            raise pickle.UnpicklingError(f"Trying to unpickle {__module_name}.{__global_name}")
        return super().find_class(__module_name, __global_name)


def load_image(file: str, convert: bool = True) -> Surface:
    image: Surface
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        image = _pg_image_load(file)
    else:
        try:
            with bz2.open(file, mode="rb", compresslevel=9) as f:
                image = SurfaceUnpickler(f).load()
        except (IOError, pickle.UnpicklingError) as exc:
            raise _pg_error(str(exc)) from exc
    if convert:
        return image.convert_alpha()
    return image


def save_image(image: Surface, file: str) -> None:
    if splitext(file)[1] != COMPILED_SURFACE_EXTENSION:
        return _pg_image_save(image, file)

    with bz2.open(file, mode="wb", compresslevel=9) as f:
        f.write(pickle.dumps(image, protocol=pickle.HIGHEST_PROTOCOL))
