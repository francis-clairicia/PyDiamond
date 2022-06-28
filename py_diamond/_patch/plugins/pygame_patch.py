# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = []  # type: list[str]

from functools import wraps
from typing import TYPE_CHECKING, Any, Callable, ParamSpec, TypeVar

from .._base import BasePatch, PatchContext

if TYPE_CHECKING:
    from pygame.event import _EventTypes

_P = ParamSpec("_P")
_R = TypeVar("_R")


# Backport of the one from py_diamond.system.utils.functools
def forbidden_call(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def not_callable(*args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"Call to function {func.__qualname__} is forbidden")

    setattr(not_callable, "__forbidden_call__", True)
    return not_callable


class PygameEventPatch(BasePatch):
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
            self.music.set_endevent = forbidden_call(self.music.set_endevent)

        if not self._event_name_patched():
            setattr(self.event, "event_name", self._make_event_name_wrapper())

        if not self._event_set_blocked_patched():
            setattr(self.event, "set_blocked", self._make_set_blocked_wrapper(QUIT, VIDEORESIZE, self.music.get_endevent()))

    def _event_set_blocked_patched(self) -> bool:
        return bool(getattr(self.event.set_blocked, "__set_blocked_wrapper__", False))

    def _music_set_endevent_patched(self) -> bool:
        return bool(getattr(self.music.set_endevent, "__forbidden_call__", False))

    def _event_name_patched(self) -> bool:
        return isinstance(getattr(self.event.event_name, "__event_name_dispatch_table__", None), dict)

    def _make_event_name_wrapper(self) -> Callable[[int], str]:
        _orig_pg_event_name = self.event.event_name

        @wraps(_orig_pg_event_name)
        def wrapper(type: int) -> str:
            type = int(type)
            dispatch_table: dict[int, str] = getattr(wrapper, "__event_name_dispatch_table__")
            try:
                name: str = dispatch_table[type]
            except KeyError:
                name = ""
            if not name:
                name = _orig_pg_event_name(type)
            return name

        setattr(wrapper, "__event_name_dispatch_table__", {})
        return wrapper

    def _make_set_blocked_wrapper(self, *forbidden_events: int) -> Callable[..., None]:
        _pg_event = self.event
        _orig_pg_event_set_blocked = self.event.set_blocked

        if not forbidden_events:
            return _orig_pg_event_set_blocked

        @wraps(_orig_pg_event_set_blocked)
        def wrapper(type: _EventTypes | None) -> None:
            caught_events: set[int]
            if type is not None:
                try:
                    event_set: set[int] = set(map(int, type))  # type: ignore[arg-type]
                except TypeError:  # Integer
                    event_set = {int(type)}  # type: ignore[arg-type]
                caught_events = event_set & set(forbidden_events)
            else:
                caught_events = set(forbidden_events)
            if caught_events:
                msg = f"{', '.join(map(_pg_event.event_name, caught_events))} must always be allowed"
                raise ValueError(msg)
            _orig_pg_event_set_blocked(type)

        setattr(wrapper, "__set_blocked_wrapper__", True)
        return wrapper


class PyDiamondEventPatch(BasePatch):
    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.AFTER_IMPORTING_SUBMODULES

    def setup(self) -> None:
        super().setup()

        from pygame import event

        self.event = event
        self.event_name_dispatch_table: dict[int, str]
        event_name_dispatch_table = getattr(self.event.event_name, "__event_name_dispatch_table__", None)
        if isinstance(event_name_dispatch_table, dict):
            self.event_name_dispatch_table = event_name_dispatch_table

    def teardown(self) -> None:
        del self.event

        try:
            del self.event_name_dispatch_table
        except AttributeError:
            pass

        return super().teardown()

    def run(self) -> None:
        if not hasattr(self, "event_name_dispatch_table"):
            return

        from pygame.mixer import music

        from ...window.event import BuiltinEvent

        self.event_name_dispatch_table[music.get_endevent()] = "MusicEndEvent"
        self.event_name_dispatch_table[BuiltinEvent.Type.MUSICEND] = "MusicEndEvent"
        self.event_name_dispatch_table[BuiltinEvent.Type.SCREENSHOT] = "ScreenshotEvent"
