# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Mixer module

It is essentially a wrapper to the pygame.mixer module.

See more in pygame documentation: https://www.pygame.org/docs/ref/mixer.html
"""

from __future__ import annotations

__all__ = ["AllowedAudioChanges", "AudioFormat", "Mixer", "MixerParams"]

from contextlib import ExitStack, contextmanager
from enum import IntEnum, IntFlag, auto
from typing import TYPE_CHECKING, Any, Iterator, Literal, NamedTuple, overload

import pygame.constants as _pg_constants
import pygame.mixer as _pg_mixer
from pygame import error as _pg_error
from typing_extensions import final

from ..system.namespace import ClassNamespace
from .sound import Channel

if TYPE_CHECKING:
    from contextlib import _GeneratorContextManager


class AllowedAudioChanges(IntFlag):
    """
    Enumerates the possible flags for the 'allowedchange' parameter of Mixer.init()
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        constant_name = f"AUDIO_ALLOW_{name}_CHANGE"
        return getattr(_pg_constants, constant_name)  # noqa: F821

    FREQUENCY = auto()
    FORMAT = auto()
    CHANNELS = auto()
    ANY = auto()


class AudioFormat(IntEnum):
    """
    Enumerates the possible audio format used by SDL_mixer
    """

    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        return getattr(_pg_constants, name)  # noqa: F821

    AUDIO_U8 = auto()
    AUDIO_S8 = auto()
    AUDIO_U16 = auto()
    AUDIO_S16 = auto()
    AUDIO_U16SYS = auto()
    AUDIO_U16LSB = auto()
    AUDIO_U16MSB = auto()
    AUDIO_S16SYS = auto()
    AUDIO_S16LSB = auto()
    AUDIO_S16MSB = auto()

    # Constants which will exist someday
    # AUDIO_S32SYS = auto()
    # AUDIO_S32LSB = auto()
    # AUDIO_S32MSB = auto()
    # AUDIO_F32LSB = auto()
    # AUDIO_F32MSB = auto()
    # AUDIO_F32SYS = auto()


class MixerParams(NamedTuple):
    """
    A namedtuple containing the actual mixer parameters
    """

    frequency: int
    size: int
    channels: int


@final
class Mixer(ClassNamespace, frozen=True):
    """
    It is essentially a wrapper to the pygame.mixer module functions.

    See more in pygame documentation: https://www.pygame.org/docs/ref/mixer.html
    """

    @overload
    @staticmethod
    def pre_init() -> None:
        ...

    @overload
    @staticmethod
    def pre_init(
        *,
        frequency: int = ...,
        size: int = ...,
        channels: int = ...,
        buffersize: int = ...,
        allowedchanges: AllowedAudioChanges | Literal[-1, 0] = ...,
        **kwargs: Any,
    ) -> None:
        ...

    @staticmethod
    def pre_init(**kwargs: Any) -> None:
        """Preset the mixer init arguments

        Call pre_init to change the defaults used when the real Mixer.init() is called.

        Raise pygame.error if pygame.mixer is already initialized

        See more in pygame documentation: https://www.pygame.org/docs/ref/mixer.html#pygame.mixer.pre_init
        """
        if _pg_mixer.get_init() is not None:
            raise _pg_error("Mixer module already initialized")
        return _pg_mixer.pre_init(**kwargs)

    @overload
    @staticmethod
    def init() -> _GeneratorContextManager[MixerParams]:
        ...

    @overload
    @staticmethod
    def init(
        *,
        frequency: int = ...,
        size: int = ...,
        channels: int = ...,
        buffersize: int = ...,
        allowedchanges: AllowedAudioChanges | Literal[-1, 0] = ...,
        **kwargs: Any,
    ) -> _GeneratorContextManager[MixerParams]:
        ...

    # So add 'devicename' breaks you mypy...?
    @staticmethod
    @contextmanager
    def init(**kwargs: Any) -> Iterator[MixerParams]:
        """Initializes the mixer module

        Initialize the pygame.mixer module for Sound loading and playback.
        The default arguments can be overridden to provide specific audio mixing.

        On context close, this will uninitialize pygame.mixer using pygame.mixer.quit().
        All playback will stop and any loaded Sound objects may not be compatible with the mixer if it is reinitialized later.

        Raise pygame.error if pygame.mixer is already initialized

        See more in pygame documentation: https://www.pygame.org/docs/ref/mixer.html#pygame.mixer.init
        """
        if _pg_mixer.get_init() is not None:
            raise _pg_error("Mixer module already initialized")

        with ExitStack() as stack:
            _pg_mixer.init(**kwargs)
            stack.callback(_pg_mixer.quit)

            from .music import MusicStream

            stack.callback(MusicStream.stop, unload=True)

            init_params: MixerParams | None = Mixer.get_init()
            assert init_params is not None
            yield init_params

    @staticmethod
    def get_init() -> MixerParams | None:
        """Test if the mixer is initialized

        If the mixer is initialized, this returns the playback arguments it is using.
        If the mixer has not been initialized this returns None.
        """
        init_params: tuple[int, int, int] | None = _pg_mixer.get_init()
        if init_params is None:
            return None
        return MixerParams._make(init_params)

    @staticmethod
    def is_busy() -> bool:
        """Test if any sound is being mixed

        Returns True if the mixer is busy mixing any channels. If the mixer is idle then this return False.
        """
        return _pg_mixer.get_busy()

    @staticmethod
    def stop_all_sounds() -> None:
        """Stop playback of all sound channels

        This will stop all playback of all active mixer channels.
        """
        return _pg_mixer.stop()

    @staticmethod
    def pause_all_sounds() -> None:
        """Temporarily stop playback of all sound channels

        This will temporarily stop all playback on the active mixer channels.
        The playback can later be resumed with Mixer.unpause_all_sounds()
        """
        return _pg_mixer.pause()

    @staticmethod
    def unpause_all_sounds() -> None:
        """Resume paused playback of sound channels

        This will resume all active sound channels after they have been paused.
        """
        return _pg_mixer.unpause()

    @staticmethod
    def fadeout_all_sounds(milliseconds: int) -> None:
        """Fade out the volume on all sounds before stopping

        This will fade out the volume on all active channels over the time argument in milliseconds.
        After the sound is muted the playback will stop.
        """
        return _pg_mixer.fadeout(milliseconds)

    @staticmethod
    def set_num_channels(count: int) -> None:
        """Set the total number of playback channels

        Sets the number of available channels for the mixer. The default value is 8.
        The value can be increased or decreased.
        If the value is decreased, sounds playing on the truncated channels are stopped.

        A negative value raises a ValueError.
        """
        if count < 0:
            raise ValueError(f"Negative count: {count}")
        return _pg_mixer.set_num_channels(count)

    @staticmethod
    def get_num_channels() -> int:
        """Get the total number of playback channels

        Returns the number of currently active playback channels.
        """
        return _pg_mixer.get_num_channels()

    @staticmethod
    def get_channels() -> list[Channel]:
        """Get the list of playback channels

        Returns a list of playback channels size get_num_channels().
        """
        return list(map(Channel, range(0, _pg_mixer.get_num_channels())))

    @staticmethod
    def set_reserved(count: int) -> int:
        """Reserve channels from being automatically used

        The mixer can reserve any number of channels that will not be automatically selected for playback by Sounds.
        If sounds are currently playing on the reserved channels they will not be stopped.

        This allows the application to reserve a specific number of channels for important sounds that must not be
        dropped or have a guaranteed channel to play on.

        Will return number of channels actually reserved, this may be less than requested depending on the number of
        channels previously allocated.

        A negative value raises a ValueError.
        """
        if count < 0:
            raise ValueError(f"Negative count: {count}")
        return _pg_mixer.set_reserved(count)

    @overload
    @staticmethod
    def find_channel(force: Literal[True]) -> Channel:
        ...

    @overload
    @staticmethod
    def find_channel(force: bool = ...) -> Channel | None:
        ...

    @staticmethod
    def find_channel(force: bool = False) -> Channel | None:
        """Find an unused channel

        This will find and return an inactive Channel object. If there are no inactive Channels this function will return None.
        If there are no inactive channels and the force argument is True, this will find the Channel with the longest
        running Sound and return it.
        """
        return _pg_mixer.find_channel(force)


del _pg_constants
