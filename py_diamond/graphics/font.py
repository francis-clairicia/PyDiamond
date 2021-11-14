# -*- coding: Utf-8 -*

__all__ = ["Font", "SysFont", "get_default_font"]

from pygame import error
from pygame.version import ver, vernum
from pygame.font import Font, SysFont, get_default_font, init as pygame_font_init

############ pygame.mixer initialization ############
if vernum < (2, 0):
    raise error(f"Your pygame version is too old: {ver!r} < '2.0.0'")

pygame_font_init()
del pygame_font_init, error, ver, vernum
