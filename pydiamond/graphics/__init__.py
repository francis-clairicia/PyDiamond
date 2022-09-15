# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's graphics module"""

from __future__ import annotations

__all__ = []  # type: list[str]

import os
import typing

import pygame

############ pygame graphics initialization ############
if pygame.version.vernum < (2, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'", name=__name__, path=__file__)

SDL_IMAGE_VERSION = typing.cast(tuple[int, int, int], pygame.image.get_sdl_image_version())

if SDL_IMAGE_VERSION is None:
    raise ImportError("SDL_image library is not loaded", name=__name__, path=__file__)

if SDL_IMAGE_VERSION < (2, 0, 0):
    raise ImportError(
        "Your SDL_image version is too old: '{0}.{1}.{2}' < '2.0.0'".format(*SDL_IMAGE_VERSION),
        name=__name__,
        path=__file__,
    )


############ Cleanup ############
del os, typing, pygame
