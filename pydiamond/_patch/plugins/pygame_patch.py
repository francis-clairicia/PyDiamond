# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

from __future__ import annotations

__all__ = []  # type: list[str]

from functools import wraps
from types import BuiltinFunctionType
from typing import TYPE_CHECKING, Callable, no_type_check

from .._base import PatchContext, RequiredPatch

if TYPE_CHECKING:
    from pygame._sdl2.controller import Controller as _Controller
    from pygame.event import Event as _Event, _EventTypes


class PygamePatch(RequiredPatch):
    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.AFTER_IMPORTING_PYGAME

    def setup(self) -> None:
        super().setup()

        import pygame._sdl2.controller as controller
        import pygame.display as display
        import pygame.event as event
        from pygame.mixer import music

        self.display = display
        self.event = event
        self.music = music
        self.controller = controller

    def teardown(self) -> None:
        del self.event, self.music, self.display, self.controller

        return super().teardown()

    def run(self) -> None:
        from pygame.constants import QUIT

        if not self._music_set_endevent_patched():
            self.music.set_endevent(self.event.custom_type())
            setattr(self.music, "set_endevent", self._make_music_set_endevent_wrapper())

        if not self._event_name_patched():
            setattr(self.event, "event_name", self._make_event_name_wrapper())

        if not self._event_set_blocked_patched():
            setattr(self.event, "set_blocked", self._make_event_set_blocked_wrapper(QUIT, self.music.get_endevent()))

        if not self._event_post_patched():
            setattr(self.event, "post", self._make_event_post_wrapper(QUIT, self.music.get_endevent()))

        if not self._controller_patched():
            setattr(self.controller, "Controller", self._make_controller_subclass())

    def _event_set_blocked_patched(self) -> bool:
        return bool(
            not isinstance(self.event.set_blocked, BuiltinFunctionType)
            and getattr(self.event.set_blocked, "__set_blocked_wrapper__", False)
        )

    def _music_set_endevent_patched(self) -> bool:
        return bool(
            not isinstance(self.music.set_endevent, BuiltinFunctionType)
            and getattr(self.music.set_endevent, "__set_endevent_wrapper__", False)
        )

    def _event_name_patched(self) -> bool:
        return isinstance(
            not isinstance(self.event.event_name, BuiltinFunctionType)
            and getattr(self.event.event_name, "__event_name_dispatch_table__", None),
            dict,
        )

    def _event_post_patched(self) -> bool:
        return bool(not isinstance(self.event.post, BuiltinFunctionType) and getattr(self.event.post, "__post_wrapper__", False))

    def _controller_patched(self) -> bool:
        return bool(getattr(self.controller.Controller, "__pydiamond_patch__", False))

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

        dispatch_table: dict[int, str] = {}

        @wraps(_orig_pg_event_name)
        def patch_event_name(type: int) -> str:
            type = int(type)
            try:
                name: str = dispatch_table[type]
            except KeyError:
                name = ""
            if not name:
                name = _orig_pg_event_name(type)
            return name

        setattr(patch_event_name, "__event_name_dispatch_table__", dispatch_table)
        return patch_event_name

    def _make_event_set_blocked_wrapper(self, *forbidden_events: int) -> Callable[[_EventTypes | None], None]:
        _pg_display = self.display
        _pg_event = self.event
        _orig_pg_event_set_blocked = self.event.set_blocked

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

        def get_forbidden_events() -> tuple[int, ...]:
            nonlocal forbidden_events

            return forbidden_events

        def add_forbidden_events(*events: int) -> None:
            nonlocal forbidden_events

            if not events:
                return

            forbidden_events = tuple(set(forbidden_events).union(map(int, events)))
            if _pg_display.get_init():
                _pg_event.set_allowed(forbidden_events)

        setattr(patch_set_blocked, "__set_blocked_wrapper__", True)
        setattr(patch_set_blocked, "__get_forbidden_events__", get_forbidden_events)
        setattr(patch_set_blocked, "__add_forbidden_events__", add_forbidden_events)
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

    def _make_controller_subclass(self) -> type[_Controller]:
        _pg_controller = self.controller

        from typing_extensions import final

        @final
        @no_type_check
        class Controller(_pg_controller.Controller):  # type: ignore[name-defined, misc]
            __qualname__ = _pg_controller.Controller.__qualname__
            __module__ = _pg_controller.Controller.__module__

            __pydiamond_patch__ = True

            @wraps(_pg_controller.Controller.__init_subclass__)
            def __init_subclass__(cls) -> None:
                raise TypeError(f"{cls.__module__}.{cls.__qualname__} cannot be subclassed")

            @wraps(_pg_controller.Controller.__new__)
            def __new__(cls, index: int) -> Controller:
                controllers: list[Controller] = getattr(_pg_controller.Controller, "_controllers")
                try:
                    return next(c for c in controllers if c.id == index)
                except StopIteration:
                    return super().__new__(cls)

            @wraps(_pg_controller.Controller.__init__)
            def __init__(self, index: int) -> None:
                if index != self.id or not self.get_init():
                    super().__init__(index)

            def __eq__(self, other: object, /) -> bool:
                if not isinstance(other, self.__class__):
                    return NotImplemented
                return self.id == other.id

            def __ne__(self, other: object, /) -> bool:
                return not (self == other)

            def __hash__(self) -> int:
                return hash((self.__class__, self.id))

            if TYPE_CHECKING:

                @property
                def id(self) -> int:
                    ...

        return Controller
