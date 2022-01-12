# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Mixer module"""

__all__ = ["Mixer", "MixerParams"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import ExitStack, contextmanager
from typing import Iterator, NamedTuple, Optional, Tuple

import pygame.mixer as _pg_mixer
from pygame import error as _pg_error


class MixerParams(NamedTuple):
    frequency: int
    size: int
    channels: int


class Mixer:

    __slots__ = ()

    @staticmethod
    @contextmanager
    def init(frequency: int = 44100, size: int = -16, channels: int = 2, buffersize: int = 512) -> Iterator[None]:
        if _pg_mixer.get_init() is not None:
            raise _pg_error("Mixer module already initialized")

        with ExitStack() as stack:
            _pg_mixer.init(frequency=frequency, size=size, channels=channels, buffer=buffersize)
            stack.callback(_pg_mixer.quit)
            yield

    @staticmethod
    def get_init() -> MixerParams:
        init_params: Optional[Tuple[int, int, int]] = _pg_mixer.get_init()
        if init_params is None:
            raise _pg_error("Mixer module not initialized")
        return MixerParams(*init_params)
