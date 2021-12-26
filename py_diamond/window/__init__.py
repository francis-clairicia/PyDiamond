# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os

import pygame

############ pygame.display initialization ############
if pygame.version.vernum < (2, 1, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.1'")

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL2 version is too old: {str(pygame.version.SDL)!r} < '2.0.16'")

os.environ.setdefault("PYGAME_BLEND_ALPHA_SDL2", "1")
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

############ Cleanup ############
del os, pygame
