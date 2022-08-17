# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

from __future__ import annotations

__all__ = [
    "Window",
    "WindowCallback",
    "WindowError",
    "WindowExit",
]

import os

import pygame

############ pygame.display initialization ############
if pygame.version.vernum < (2, 1, 2):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.2'", name=__name__, path=__file__)

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'", name=__name__, path=__file__)

os.environ.setdefault("PYGAME_BLEND_ALPHA_SDL2", "1")
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

############ Cleanup ############
del os, pygame

############ Package initialization ############
from .display import *
