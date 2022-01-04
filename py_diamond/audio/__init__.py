# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's audio module"""

__all__ = ["AUDIO_BUFFER", "AUDIO_CHANNELS", "AUDIO_FREQUENCY", "AUDIO_SIZE", "Music", "Sound"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os

import pygame

############ pygame.mixer initialization ############
if pygame.version.vernum < (2, 0):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.0.0'")

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'")

AUDIO_FREQUENCY = int(os.environ.setdefault("AUDIO_FREQUENCY", "44100"))
AUDIO_SIZE = -abs(int(os.environ.setdefault("AUDIO_SIZE", "16")))
AUDIO_CHANNELS = int(os.environ.setdefault("AUDIO_CHANNELS", "2"))
AUDIO_BUFFER = int(os.environ.setdefault("AUDIO_BUFFER", "512"))

if pygame.mixer.get_init() is not None:
    pygame.mixer.quit()

pygame.mixer.init(AUDIO_FREQUENCY, AUDIO_SIZE, AUDIO_CHANNELS, AUDIO_BUFFER)

############ Cleanup ############
del os, pygame


############ Package initialization ############
from .sound import Music, Sound
