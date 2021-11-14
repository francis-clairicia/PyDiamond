# -*- coding: Utf-8 -*

import os
import typing
import copyreg

import pygame
from pygame.image import fromstring as _surface_deserialization, tostring as _surface_serialization

if pygame.version.vernum < (2, 1):
    raise pygame.error(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'")

############ Surface pickling register ############
def _pickle_surface(s: pygame.surface.Surface) -> typing.Any:
    return (_surface_deserialization, (_surface_serialization(s, "ARGB"), s.get_size(), "ARGB"))


copyreg.pickle(pygame.surface.Surface, _pickle_surface)  # type: ignore

############ Cleanup ############
del _pickle_surface
del os, typing, pygame, copyreg
