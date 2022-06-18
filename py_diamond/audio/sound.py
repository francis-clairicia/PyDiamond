# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Sound module"""

from __future__ import annotations

__all__ = ["Channel", "Sound"]

import pygame.mixer
from pygame import encode_file_path
from pygame.mixer import Channel

from ..system.duplicate import NoDuplicate


class Sound(pygame.mixer.Sound, NoDuplicate):
    __slots__ = ()

    def __init__(self, file: str | bytes) -> None:
        if not isinstance(file, bytes):
            file = encode_file_path(file)
        return super().__init__(file=file)

    def set_volume(self, value: float) -> None:
        value = max(value, 0)
        return super().set_volume(value)
