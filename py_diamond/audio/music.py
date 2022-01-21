# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Music module"""

from __future__ import annotations

__all__ = ["Music", "MusicStream"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from atexit import register as atexit
from dataclasses import dataclass, field
from typing import Final, List

from pygame.event import Event as _PygameEvent, custom_type as _pg_event_custom_type, post as _pg_event_post
from pygame.mixer import get_init as _pg_mixer_get_init, music as _pg_music

from ..system.duplicate import MetaNoDuplicate
from ..system.namespace import MetaClassNamespace
from ..system.utils import forbidden_call


class Music(metaclass=MetaNoDuplicate):
    __slots__ = ("__f",)

    def __init__(self, filepath: str) -> None:
        self.__f: str = str(filepath)

    def __repr__(self) -> str:
        return f"<{type(self).__name__} {self.filepath!r}>"

    def play(self, repeat: int = 0, *, fade_ms: int = 0) -> None:
        MusicStream.play(self, repeat=repeat, fade_ms=fade_ms)

    def queue(self, repeat: int = 0) -> None:
        MusicStream.queue(self, repeat=repeat)

    @property
    def filepath(self, /) -> str:
        return self.__f


class MusicStream(metaclass=MetaClassNamespace, frozen=True):
    MUSICEND: Final[int] = _pg_event_custom_type()
    _pg_music.set_endevent(_pg_event_custom_type())
    _pg_music.set_endevent = forbidden_call(_pg_music.set_endevent)

    @dataclass
    class _PlayingMusic:
        payload: _MusicPayload | None = None
        fadeout: bool = False

    __queue: List[_MusicPayload] = []
    __playing: _PlayingMusic = _PlayingMusic()

    @staticmethod
    def play(music: Music, *, repeat: int = 0, fade_ms: int = 0) -> None:
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is not None and played_music.music is music:
            return
        MusicStream.stop()
        repeat = max(int(repeat), -1)
        _pg_music.load(music.filepath)
        _pg_music.play(repeat, fade_ms=fade_ms)
        MusicStream.__playing.payload = _MusicPayload(music, repeat=repeat)

    @staticmethod
    @atexit
    def stop() -> None:
        queue: List[_MusicPayload] = MusicStream.__queue
        queue.clear()
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is not None:
            played_music.repeat = 0
        MusicStream.__playing.payload = None
        MusicStream.__playing.fadeout = False
        if _pg_mixer_get_init():
            _pg_music.stop()
            _pg_music.unload()
        if played_music is not None:
            MusicStream.__post_event(played_music.music, None)

    @staticmethod
    def is_busy() -> bool:
        return _pg_music.get_busy()

    @staticmethod
    def pause() -> None:
        return _pg_music.pause()

    @staticmethod
    def unpause() -> None:
        return _pg_music.unpause()

    @staticmethod
    def fadeout(milliseconds: int) -> None:
        MusicStream.__playing.fadeout = True
        return _pg_music.fadeout(milliseconds)

    @staticmethod
    def get_volume() -> float:
        return _pg_music.get_volume()

    @staticmethod
    def set_volume(volume: float) -> None:
        volume = min(max(float(volume), 0), 1)
        return _pg_music.set_volume(volume)

    @staticmethod
    def queue(music: Music, *, repeat: int = 0) -> None:
        repeat = int(repeat)
        if repeat < 0:
            raise ValueError("Cannot set infinite loop for queued musics")
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if played_music is None:
            MusicStream.play(music, repeat=repeat)
            return
        if played_music.repeat < 0:
            raise ValueError(f"The playing music loops infinitely, queued musics will not be set")
        queue: List[_MusicPayload] = MusicStream.__queue
        if not queue:
            _pg_music.queue(music.filepath, loops=repeat)
        queue.append(_MusicPayload(music, repeat=repeat))

    @staticmethod
    def __update() -> None:
        played_music: _MusicPayload | None = MusicStream.__playing.payload
        if MusicStream.__playing.fadeout:
            MusicStream.stop()
            return
        if played_music is None or played_music.repeat < 0:
            return
        next_music: Music | None
        played_music.repeat -= 1
        if played_music.repeat >= 0:
            next_music = played_music.music
        else:
            queue: List[_MusicPayload] = MusicStream.__queue
            if not queue:
                MusicStream.__playing.payload = next_music = None
            else:
                MusicStream.__playing.payload = payload = queue.pop(0)
                next_music = payload.music
                if queue:
                    _pg_music.queue(queue[0].music.filepath, loops=queue[0].repeat)
        MusicStream.__post_event(played_music.music, next_music)

    @staticmethod
    def __post_event(finished_music: Music, next_music: Music | None) -> bool:
        return _pg_event_post(_PygameEvent(MusicStream.MUSICEND, finished=finished_music, next=next_music))


@dataclass
class _MusicPayload:
    music: Music
    repeat: int = field(kw_only=True)


del atexit, _pg_event_custom_type
