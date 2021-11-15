# -*- coding: Utf-8 -*

import os
import pygame

############ pygame.display initialization ############
os.environ["PYGAME_BLEND_ALPHA_SDL2"] = os.getenv("PYGAME_BLEND_ALPHA_SDL2", "1")
os.environ["SDL_VIDEO_CENTERED"] = os.getenv("SDL_VIDEO_CENTERED", "1")

if pygame.version.vernum < (2, 1):
    raise pygame.error(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'")

############ Cleanup ############
del os, pygame
