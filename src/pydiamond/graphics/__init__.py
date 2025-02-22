# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's graphics module"""

from __future__ import annotations

__all__ = []  # type: list[str]

import pygame

############ pygame graphics initialization ############
if pygame.version.vernum < (2, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'", name=__name__, path=__file__)

SDL_IMAGE_VERSION = SDL_IMAGE_VERSION if (SDL_IMAGE_VERSION := pygame.image.get_sdl_image_version()) else (-1, -1, -1)

if SDL_IMAGE_VERSION[0] < 0:
    raise ImportError("SDL_image library is not loaded", name=__name__, path=__file__)

if SDL_IMAGE_VERSION < (2, 0, 0):
    raise ImportError(
        "Your SDL_image version is too old: '{}.{}.{}' < '2.0.0'".format(*SDL_IMAGE_VERSION),
        name=__name__,
        path=__file__,
    )


############ Cleanup ############
del pygame
