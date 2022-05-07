# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's audio module"""

__all__ = ["Channel", "Mixer", "MixerParams", "Music", "MusicStream", "Sound"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os

import pygame

############ pygame.mixer initialization ############
if pygame.version.vernum < (2, 1, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.1'", name=__name__, path=__file__)

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'", name=__name__, path=__file__)

SDL_MIXER_VERSION = pygame.mixer.get_sdl_mixer_version()

if SDL_MIXER_VERSION < (2, 0, 0):
    raise ImportError(
        "Your SDL_mixer version is too old: '{0}.{1}.{2}' < '2.0.0'".format(*SDL_MIXER_VERSION),
        name=__name__,
        path=__file__,
    )

############ Cleanup ############
del os, pygame


############ Package initialization ############
from .mixer import Mixer, MixerParams
from .music import Music, MusicStream
from .sound import Channel, Sound
