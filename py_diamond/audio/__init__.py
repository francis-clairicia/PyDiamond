# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's audio module

This module allows you to load and play sounds.

It is essentially a wrapper to the pygame.mixer module, which depends on SDL_mixer, but have
a more convenient way to handle long music playback with the MusicStream class.

See more in pygame documentation: https://www.pygame.org/docs/ref/mixer.html
"""

from __future__ import annotations

__all__ = []  # type: list[str]

import os

import pygame

############ pygame.mixer initialization ############
if pygame.version.vernum < (2, 1, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.1'", name=__name__, path=__file__)

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'", name=__name__, path=__file__)

SDL_MIXER_VERSION = pygame.mixer.get_sdl_mixer_version(linked=True)

if SDL_MIXER_VERSION < (2, 0, 0):
    raise ImportError(
        "Your SDL_mixer version is too old: '{0}.{1}.{2}' < '2.0.0'".format(*SDL_MIXER_VERSION),
        name=__name__,
        path=__file__,
    )

############ Cleanup ############
del os, pygame
