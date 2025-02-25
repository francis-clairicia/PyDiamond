# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Music module

This module leans on pygame.mixer.music module to control the playback of music.

The difference between the music playback and regular Sound playback is that the music is streamed,
and never actually loaded all at once. The mixer system only supports a single music stream at once.

(See more in pygame documentation: https://www.pygame.org/docs/ref/music.html)

This module provides a high-level interface, which handles several queued musics (playlists) and
keeps tracking running and queued sounds.
"""

from __future__ import annotations

__all__ = ["Music", "MusicStream"]

from collections import deque
from contextlib import AbstractContextManager as ContextManager, ExitStack
from dataclasses import dataclass, field
from os import PathLike
from typing import IO, Final, final
from weakref import WeakValueDictionary

import pygame.mixer as _pg_mixer
from pygame.constants import NOEVENT
from pygame.event import Event as _PygameEvent
from pygame.mixer import music as _pg_music

from ..resources.abc import Resource
from ..resources.file import FileResource
from ..system.namespace import ClassNamespace
from ..system.non_copyable import NonCopyable
from ..system.utils.itertools import prepend


@final
class Music(NonCopyable):
    """
    Simple object which can be used to play or queue a music into the MusicStream.
    """

    __slots__ = ("__resource", "__weakref__")
    __cache: Final[WeakValueDictionary[Resource, Music]] = WeakValueDictionary()

    def __new__(cls, resource: str | bytes | PathLike[str] | PathLike[bytes] | Resource) -> Music:
        if not isinstance(resource, Resource):
            resource = FileResource(resource)
        try:
            self = cls.__cache[resource]
        except KeyError:
            cls.__cache[resource] = self = super().__new__(cls)
            self.__resource = resource
        return self

    def __repr__(self) -> str:
        self.__resource: Resource
        return f"<{type(self).__name__} {self.__resource!r}>"

    def play(self, *, repeat: int = 0, fade_ms: int = 0) -> None:
        """Start the playback of the music stream

        See MusicStream.play() docstring for more information
        """
        MusicStream.play(self, repeat=repeat, fade_ms=fade_ms)

    def queue(self, *, repeat: int = 0) -> None:
        """Queue a music file to follow the current

        See MusicStream.queue() docstring for more information
        """
        MusicStream.queue(self, repeat=repeat)

    def open(self) -> ContextManager[IO[bytes]]:
        return self.__resource.open()

    @property
    def resource(self, /) -> Resource:
        """Resource object representing music file"""
        return self.__resource

    @property
    def name(self) -> str:
        """Music name"""
        return self.__resource.name


@final
class MusicStream(ClassNamespace, frozen=True):
    """
    API for the pygame.mixer.music controller

    This class provides a high-level interface, which handles several queued musics (playlists) and
    keeps tracking running and queued sounds.
    """

    @dataclass
    class _PlayingMusic:
        payload: _MusicPayload | None = None
        fadeout: bool = False
        stopped: Music | None = None

    __queue: deque[_MusicPayload] = deque()
    __playing: _PlayingMusic = _PlayingMusic()
    __fp: dict[Music, ExitStack] = {}

    @staticmethod
    def play(music: Music, *, repeat: int = 0, fade_ms: int = 0) -> None:
        """Start the playback of the music stream

        This will load and play the music file. If the music is already playing it will be restarted.

        repeat is an optional integer argument, which is 0 by default, which indicates how many times to repeat the music.
        The music repeats indefinitely if this argument is set to -1.

        fade_ms is an optional integer argument, which is 0 by default, which denotes the period of time (in milliseconds)
        over which the music will fade up from volume level 0.0 to full volume (or the volume level previously set by
        MusicStream.set_volume()).
        The sample may end before the fade-in is complete. If the music is already streaming fade_ms is ignored.
        """
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        repeat = max(int(repeat), -1)
        stopped_music = MusicStream.__playing.stopped
        MusicStream.__playing.stopped = None
        if (played_music is not None and played_music.music is music) or stopped_music is music:
            _pg_music.play(loops=repeat, fade_ms=fade_ms)
            if played_music is None:
                MusicStream.__playing.payload = _MusicPayload(music, repeat=repeat)
            else:
                played_music.repeat = repeat
            return
        MusicStream.__playing.payload = None
        MusicStream.stop(unload=True)
        with ExitStack() as exit_stack:
            _pg_music.load(exit_stack.enter_context(music.open()), music.name)
            MusicStream.__fp[music] = exit_stack.pop_all()
        _pg_music.play(loops=repeat, fade_ms=fade_ms)
        MusicStream.__playing.payload = _MusicPayload(music, repeat=repeat)

    @staticmethod
    def stop(*, unload: bool = False) -> None:
        """Stop the music playback

        Stops the music playback if it is currently playing. MUSICEND event will NOT be triggered.
        It will not unload the music unless 'unload' argument is True.
        """
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is not None:
            played_music.repeat = 0
            MusicStream.__playing.stopped = played_music.music
            MusicStream.__playing.payload = None
        if unload:
            MusicStream.__playing.stopped = None
        MusicStream.__playing.fadeout = False
        try:
            if _pg_mixer.get_init():
                _pg_music.stop()
                if unload:
                    _pg_music.unload()
        finally:
            if unload:
                MusicStream.__clear_all_resources()
            else:
                MusicStream.__clear_queue()

    @staticmethod
    def get_music() -> Music | None:
        """Get the actual music playback

        Returns the Music object of the playing music, or None if there is not.
        """
        return payload.music if (payload := MusicStream.__playing.payload) is not None else None

    @staticmethod
    def get_queue() -> list[Music]:
        """Get pending musics

        Returns a list of all the queued musics.
        """
        return [payload.music for payload in MusicStream.__queue]

    @staticmethod
    def get_playlist() -> list[Music]:
        """Get the music playlist

        Returns a list including the playing music and the queued music, in order.
        """
        running_music = MusicStream.get_music()
        if running_music:
            return list(prepend(running_music, MusicStream.get_queue()))
        return MusicStream.get_queue()

    @staticmethod
    def is_busy() -> bool:
        """Check if the music stream is playing

        Returns True when the music stream is actively playing. When the music is idle this returns False.
        """
        return _pg_music.get_busy()

    @staticmethod
    def pause() -> None:
        """Temporarily stop music playback

        Temporarily stop playback of the music stream. It can be resumed with the unpause() function.
        """
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is not None:
            MusicStream.__playing.stopped = played_music.music
        return _pg_music.pause()

    @staticmethod
    def unpause() -> None:
        """Resume paused music

        This will resume the playback of a music stream after it has been paused.
        """
        MusicStream.__playing.stopped = None
        return _pg_music.unpause()

    @staticmethod
    def fadeout(milliseconds: int) -> None:
        """Stop music playback after fading out

        Fade out and stop the currently playing music.

        The time argument denotes the integer milliseconds for which the fading effect is generated.

        Note, that this function blocks until the music has faded out. Calls to fadeout() and set_volume() will have
        no effect during this time.
        MUSICEND event will be triggered after the music has faded.
        """
        MusicStream.__playing.fadeout = True
        try:
            return _pg_music.fadeout(milliseconds)
        finally:
            MusicStream.__clear_queue()

    @staticmethod
    def get_volume() -> float:
        """Get the music volume

        Returns the current volume for the mixer. The value will be between 0.0 and 1.0.
        """
        return _pg_music.get_volume()

    @staticmethod
    def set_volume(volume: float) -> None:
        """Set the music volume

        Set the volume of the music playback.

        The volume argument is a float between 0.0 and 1.0 that sets the volume level.
        When new music is loaded the volume is reset to full volume.
        If volume is a negative value the volume will be set to 0.0.
        If the volume argument is greater than 1.0, the volume will be set to 1.0.
        """

        volume = min(max(float(volume), 0), 1)
        return _pg_music.set_volume(volume)

    @staticmethod
    def queue(music: Music, *, repeat: int = 0) -> None:
        """Queue a music file to follow the current

        This will load a music file and queue it. A queued music file will begin as soon as the current music naturally ends.
        Several music can be queued at a time. Also, if the current music is ever stopped or changed,
        all the queued music will be lost.
        """
        repeat = int(repeat)
        if repeat < 0:
            raise ValueError("Cannot set infinite loop for queued musics")
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is None or MusicStream.__playing.fadeout:
            MusicStream.play(music, repeat=repeat)
            return
        if played_music.repeat < 0:
            raise ValueError("The playing music loops infinitely, queued musics will not be set")
        queue: deque[_MusicPayload] = MusicStream.__queue
        if not queue:
            MusicStream.__set_pygame_music_queue(music, repeat)
        queue.append(_MusicPayload(music, repeat=repeat))

    @staticmethod
    def _handle_event(event: _PygameEvent) -> bool:
        end_event = _pg_music.get_endevent()
        if end_event == NOEVENT:
            return False
        if event.type == end_event:
            return MusicStream.__update(event)
        return True

    @staticmethod
    def __update(event: _PygameEvent) -> bool:
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is None:
            return False
        MusicStream.__free_up_resource(played_music.music)
        next_music: Music | None
        if MusicStream.__playing.fadeout:
            MusicStream.__playing.fadeout = False
            played_music.repeat = 0
            MusicStream.__playing.stopped = played_music.music
            MusicStream.__playing.payload = None
            next_music = None
        else:
            if played_music.repeat < 0:
                return False
            queue: deque[_MusicPayload] = MusicStream.__queue
            if not queue:
                MusicStream.__playing.payload = next_music = None
            else:
                MusicStream.__playing.payload = payload = queue.popleft()
                next_music = payload.music
                if queue:
                    MusicStream.__set_pygame_music_queue(queue[0].music, queue[0].repeat)
        setattr(event, "finished", played_music.music)
        setattr(event, "next", next_music)
        return True

    @staticmethod
    def __set_pygame_music_queue(music: Music, repeat: int) -> None:
        with ExitStack() as exit_stack:
            _pg_music.queue(exit_stack.enter_context(music.open()), music.name, loops=repeat)
            MusicStream.__fp[music] = exit_stack.pop_all()

    @staticmethod
    def __free_up_resource(music: Music) -> None:
        try:
            stack = MusicStream.__fp.pop(music)
        except KeyError:
            pass
        else:
            stack.close()

    @staticmethod
    def __clear_queue() -> None:
        queue: deque[_MusicPayload] = MusicStream.__queue
        fp_dict = MusicStream.__fp
        with ExitStack() as stack:
            stack.callback(queue.clear)
            for fp_stack in filter(None, map(lambda p: fp_dict.pop(p.music, None), queue)):
                stack.enter_context(fp_stack)

    @staticmethod
    def __clear_all_resources() -> None:
        queue: deque[_MusicPayload] = MusicStream.__queue
        fp_dict = MusicStream.__fp
        with ExitStack() as stack:
            stack.callback(queue.clear)
            for music, fp_stack in fp_dict.items():
                stack.callback(fp_dict.__delitem__, music)
                stack.enter_context(fp_stack)


@dataclass
class _MusicPayload:
    music: Music
    repeat: int = field(kw_only=True)


import atexit
import functools

from ..system.utils.os import register_at_fork_if_supported

atexit.register(MusicStream.stop, unload=True)
register_at_fork_if_supported(after_in_child=functools.partial(MusicStream.stop, unload=True))

del atexit, functools, register_at_fork_if_supported
