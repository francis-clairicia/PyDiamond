# -*- coding: Utf-8 -*

import os
import typing
import atexit
import copyreg

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"  # Must be set before importing pygame

import pygame
from pygame.surface import Surface
from pygame.image import fromstring as _surface_deserialization, tostring as _surface_serialization

############ Environment initialization ############
if pygame.version.vernum < (2, 1):
    raise pygame.error(f"Your pygame version is too old: {pygame.version.ver} < '2.1.0'")

os.environ["PYGAME_BLEND_ALPHA_SDL2"] = os.getenv("PYGAME_BLEND_ALPHA_SDL2", "1")
os.environ["SDL_VIDEO_CENTERED"] = os.getenv("SDL_VIDEO_CENTERED", "1")

############ Pygame initialization ############
pygame.quit()

MIXER_FREQUENCY: int = int(os.getenv("AUDIO_FREQUENCY", 44100))
MIXER_SIZE: int = -abs(int(os.getenv("AUDIO_SIZE", 16)))
MIXER_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", 2))
MIXER_BUFFER: int = int(os.getenv("AUDIO_BUFFER", 512))

pygame.mixer.pre_init(MIXER_FREQUENCY, MIXER_SIZE, MIXER_CHANNELS, MIXER_BUFFER)
_status: typing.Tuple[int, int] = pygame.init()
if _status[1] > 0:
    raise RuntimeError(
        f"Error on pygame initialization: {_status[1]} module{'s' if _status[1] > 1 else ''} failed to load: {pygame.get_error()}"
    )

atexit.register(pygame.quit)

############ Surface pickling register ############
def _pickle_surface(s: Surface) -> typing.Any:
    return (_surface_deserialization, (_surface_serialization(s, "ARGB"), s.get_size(), "ARGB"))


copyreg.pickle(Surface, _pickle_surface)  # type: ignore

############ Cleanup ############
del _status, _pickle_surface
del Surface
del os, typing, atexit, pygame, copyreg
