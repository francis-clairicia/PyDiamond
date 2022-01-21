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

from ..system.namespace import MetaClassNamespace
from .music import MusicStream
from .sound import Channel


class MixerParams(NamedTuple):
    frequency: int
    size: int
    channels: int


class Mixer(metaclass=MetaClassNamespace, frozen=True):
    @staticmethod
    @contextmanager
    def init(frequency: int = 44100, size: int = -16, channels: int = 2, buffersize: int = 512) -> Iterator[MixerParams]:
        if _pg_mixer.get_init() is not None:
            raise _pg_error("Mixer module already initialized")

        with ExitStack() as stack:
            _pg_mixer.init(frequency=frequency, size=size, channels=channels, buffer=buffersize)
            stack.callback(_pg_mixer.quit)
            stack.callback(MusicStream.stop)
            yield Mixer.get_init()

    @staticmethod
    def get_init() -> MixerParams:
        init_params: Tuple[int, int, int] | None = _pg_mixer.get_init()
        if init_params is None:
            raise _pg_error("Mixer module not initialized")
        return MixerParams(*init_params)

    @staticmethod
    def stop_all_sounds() -> None:
        return _pg_mixer.stop()

    @staticmethod
    def pause_all_sounds() -> None:
        return _pg_mixer.pause()

    @staticmethod
    def unpause_all_sounds() -> None:
        return _pg_mixer.unpause()

    @staticmethod
    def fadeout_all_sounds(milliseconds: int) -> None:
        return _pg_mixer.fadeout(milliseconds)

    @staticmethod
    def set_num_channels(count: int) -> None:
        if count < 0:
            raise ValueError(f"Negative count: {count}")
        return _pg_mixer.set_num_channels(count)

    @staticmethod
    def get_num_channels() -> int:
        return _pg_mixer.get_num_channels()

    @staticmethod
    def set_reserved(count: int) -> int:
        if count < 0:
            raise ValueError(f"Negative count: {count}")
        return _pg_mixer.set_reserved(count)

    @staticmethod
    def find_channel() -> Optional[Channel]:  # Channel | None cannot be used -> Channel is a function
        return _pg_mixer.find_channel()

    @staticmethod
    def find_channel_force() -> Channel:
        return _pg_mixer.find_channel(force=True)
