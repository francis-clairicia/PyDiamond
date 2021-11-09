# -*- coding: Utf-8 -*

import os
import typing
import atexit
import pygame

if pygame.get_init():
    pygame.quit()

MIXER_FREQUENCY: int = int(os.getenv("AUDIO_FREQUENCY", 44100))
MIXER_SIZE: int = -abs(int(os.getenv("AUDIO_SIZE", 16)))
MIXER_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", 2))
MIXER_BUFFER: int = int(os.getenv("AUDIO_BUFFER", 512))

pygame.mixer.pre_init(MIXER_FREQUENCY, MIXER_SIZE, MIXER_CHANNELS, MIXER_BUFFER)
_status: typing.Tuple[int, int] = pygame.init()
if _status[1] > 0:
    raise RuntimeError(f"Error on pygame initialization: {_status[1]} module{'s' if _status[1] > 1 else ''} failed to load")

atexit.register(pygame.quit)

del _status
del os, typing, atexit, pygame
