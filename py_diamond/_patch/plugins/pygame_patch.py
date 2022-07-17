# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

from __future__ import annotations

__all__ = []  # type: list[str]

from functools import wraps
from typing import TYPE_CHECKING, Callable

from .._base import PatchContext, RequiredPatch

if TYPE_CHECKING:
    from pygame.event import Event as _Event, _EventTypes


class PygamePatch(RequiredPatch):
    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.AFTER_IMPORTING_PYGAME

    def setup(self) -> None:
        super().setup()

        from pygame import event
        from pygame.mixer import music

        self.event = event
        self.music = music

    def teardown(self) -> None:
        del self.event, self.music

        return super().teardown()

    def run(self) -> None:
        from pygame.constants import QUIT, VIDEORESIZE

        if not self._music_set_endevent_patched():
            self.music.set_endevent(self.event.custom_type())
            setattr(self.music, "set_endevent", self._make_music_set_endevent_wrapper())

        if not self._event_name_patched():
            setattr(self.event, "event_name", self._make_event_name_wrapper())

        if not self._event_set_blocked_patched():
            setattr(self.event, "set_blocked", self._make_event_set_blocked_wrapper(QUIT, VIDEORESIZE, self.music.get_endevent()))

        if not self._event_post_patched():
            setattr(self.event, "post", self._make_event_post_wrapper(self.music.get_endevent()))

    def _event_set_blocked_patched(self) -> bool:
        return bool(getattr(self.event.set_blocked, "__set_blocked_wrapper__", False))

    def _music_set_endevent_patched(self) -> bool:
        return bool(getattr(self.music.set_endevent, "__set_endevent_wrapper__", False))

    def _event_name_patched(self) -> bool:
        return isinstance(getattr(self.event.event_name, "__event_name_dispatch_table__", None), dict)

    def _event_post_patched(self) -> bool:
        return bool(getattr(self.event.post, "__post_wrapper__", False))

    def _make_music_set_endevent_wrapper(self) -> Callable[[int], None]:
        _orig_pg_music_set_endevent = self.music.set_endevent

        @wraps(_orig_pg_music_set_endevent)
        def patch_set_endevent(event_type: int) -> None:
            func_qualname = _orig_pg_music_set_endevent.__qualname__
            raise TypeError(f"Call to function {func_qualname} is forbidden")

        setattr(patch_set_endevent, "__set_endevent_wrapper__", True)
        return patch_set_endevent

    def _make_event_name_wrapper(self) -> Callable[[int], str]:
        _orig_pg_event_name = self.event.event_name

        @wraps(_orig_pg_event_name)
        def patch_event_name(type: int) -> str:
            type = int(type)
            dispatch_table: dict[int, str] = getattr(patch_event_name, "__event_name_dispatch_table__")
            try:
                name: str = dispatch_table[type]
            except KeyError:
                name = ""
            if not name:
                name = _orig_pg_event_name(type)
            return name

        setattr(patch_event_name, "__event_name_dispatch_table__", {})
        return patch_event_name

    def _make_event_set_blocked_wrapper(self, *forbidden_events: int) -> Callable[[_EventTypes | None], None]:
        _pg_event = self.event
        _orig_pg_event_set_blocked = self.event.set_blocked

        if not forbidden_events:
            return _orig_pg_event_set_blocked

        @wraps(_orig_pg_event_set_blocked)
        def patch_set_blocked(type: _EventTypes | None) -> None:
            caught_events: tuple[int, ...]
            if type is not None:
                event_set: set[int]
                try:
                    iter(type)  # type: ignore[arg-type]
                except TypeError:  # Integer
                    event_set = {int(type)}  # type: ignore[arg-type]
                else:
                    type = tuple(type)  # type: ignore[arg-type]  # Preserve values in case it is an iterator
                    event_set = set(map(int, type))
                event_set.intersection_update(forbidden_events)
                caught_events = tuple(e for e in forbidden_events if e in event_set)
            else:
                caught_events = forbidden_events
            if caught_events:
                raise ValueError(f"{', '.join(map(_pg_event.event_name, caught_events))} must always be allowed")
            return _orig_pg_event_set_blocked(type)

        setattr(patch_set_blocked, "__set_blocked_wrapper__", True)
        setattr(patch_set_blocked, "__forbidden_events__", forbidden_events)
        return patch_set_blocked

    def _make_event_post_wrapper(self, *forbidden_events: int) -> Callable[[_Event], bool]:
        _pg_event = self.event
        _orig_pg_event_post = self.event.post

        if not forbidden_events:
            return _orig_pg_event_post

        @wraps(_orig_pg_event_post)
        def patch_post(event: _Event) -> bool:
            if event.type in forbidden_events:
                raise ValueError(f"{_pg_event.event_name(event.type)} cannot be added externally")
            return _orig_pg_event_post(event)

        setattr(patch_post, "__post_wrapper__", True)
        setattr(patch_post, "__forbidden_events__", forbidden_events)
        return patch_post
