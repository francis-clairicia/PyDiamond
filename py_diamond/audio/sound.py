# -*- coding: Utf-8 -*

__all__ = ["Music", "Sound"]

from pygame.mixer import Sound as _Sound


class Sound(_Sound):
    pass


class Music:
    pass
