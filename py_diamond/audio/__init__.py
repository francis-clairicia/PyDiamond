# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's audio module"""

__all__ = ["Mixer", "MixerParams", "Music", "Sound"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os

import pygame

############ pygame.mixer initialization ############
if pygame.version.vernum < (2, 1, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.1'")

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'")

if pygame.mixer.get_sdl_mixer_version() < (2, 0, 0):
    raise ImportError("Your SDL_mixer version is too old: '{0}.{1}.{2}' < '2.0.0'".format(*pygame.mixer.get_sdl_mixer_version()))

############ Cleanup ############
del os, pygame


############ Package initialization ############
from .mixer import Mixer, MixerParams
from .sound import Music, Sound
