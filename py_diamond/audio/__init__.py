# -*- coding: Utf-8 -*

__all__ = ["MIXER_BUFFER", "MIXER_CHANNELS", "MIXER_FREQUENCY", "MIXER_SIZE"]

import os

import pygame

############ pygame.mixer initialization ############
if pygame.version.vernum < (2, 0):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.0.0'")

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL2 version is too old: {str(pygame.version.SDL)!r} < '2.0.16'")

MIXER_FREQUENCY: int = int(os.getenv("AUDIO_FREQUENCY", 44100))
MIXER_SIZE: int = -abs(int(os.getenv("AUDIO_SIZE", 16)))
MIXER_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", 2))
MIXER_BUFFER: int = int(os.getenv("AUDIO_BUFFER", 512))

if pygame.mixer.get_init() is not None:
    pygame.mixer.quit()

pygame.mixer.init(MIXER_FREQUENCY, MIXER_SIZE, MIXER_CHANNELS, MIXER_BUFFER)

############ Cleanup ############
del os, pygame
