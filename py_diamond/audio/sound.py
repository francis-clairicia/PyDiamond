# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Sound module"""

__all__ = ["Channel", "Sound"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from pygame.mixer import Channel, Sound as _PygameSound

from ..system.duplicate import MetaNoDuplicate


class Sound(_PygameSound, metaclass=MetaNoDuplicate):
    def __init__(self, file: str) -> None:
        return super().__init__(file=file)

    def set_volume(self, value: float) -> None:
        value = max(value, 0)
        return super().set_volume(value)


del _PygameSound
