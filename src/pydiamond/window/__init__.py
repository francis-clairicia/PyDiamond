# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

from __future__ import annotations

__all__ = [
    "Window",
    "WindowCallback",
    "WindowError",
    "WindowExit",
    "WindowRenderer",
]

import pygame

############ pygame.display initialization ############
if pygame.version.vernum < (2, 1, 3):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.3'", name=__name__, path=__file__)

if pygame.version.SDL < (2, 0, 20):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.20'", name=__name__, path=__file__)

############ Cleanup ############
del pygame

############ Package initialization ############
from .display import *
