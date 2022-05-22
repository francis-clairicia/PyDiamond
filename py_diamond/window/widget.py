# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Widgets module"""

from __future__ import annotations

__all__ = ["AbstractWidget"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from functools import cached_property
from operator import truth
from typing import ClassVar

from ..audio.sound import Sound
from .clickable import Clickable
from .cursor import AbstractCursor
from .display import Window
from .event import Event, KeyDownEvent, KeyEvent, KeyUpEvent, MouseButtonUpEvent
from .gui import BoundFocus
from .keyboard import Keyboard
from .scene import Scene


class AbstractWidget(Clickable):
    __default_focus_on_hover: ClassVar[bool] = False

    def __init__(
        self,
        master: Scene | Window,
        *,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: AbstractCursor | None = None,
        disabled_cursor: AbstractCursor | None = None,
        take_focus: bool = True,
        focus_on_hover: bool | None = None,
    ) -> None:
        if focus_on_hover is None:
            focus_on_hover = self.__default_focus_on_hover
        self.__focus_on_hover: bool = truth(focus_on_hover)
        Clickable.__init__(
            self,
            master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
        )
        self.focus.take(take_focus)
        self.event.bind(KeyDownEvent, lambda self, event: self.__handle_key_press_event(event, focus_handle_event=False))
        self.event.bind(KeyUpEvent, lambda self, event: self.__handle_key_press_event(event, focus_handle_event=False))

    def set_focus_on_hover(self, status: bool) -> None:
        self.__focus_on_hover = focus_on_hover = truth(status)
        if focus_on_hover and self.hover:
            self.focus.set()

    @classmethod
    def set_default_focus_on_hover(cls, status: bool) -> None:
        cls.__default_focus_on_hover = truth(status)

    @classmethod
    def get_default_focus_on_hover(cls) -> bool:
        return cls.__default_focus_on_hover

    def __handle_key_press_event(self, event: KeyEvent, focus_handle_event: bool) -> bool:
        if self._should_ignore_event(event):
            return False

        if not self.is_shown() or not focus_handle_event:
            self.active = self.hover = False
            return False

        valid_key: bool = truth(self._valid_key(event.key)) and self.hover

        match event:
            case KeyDownEvent() if valid_key:
                self.active = True
                self._on_press_down(event)
                return True
            case KeyDownEvent():
                self.active = False
                self._on_press_out(event)
                return False
            case KeyUpEvent() if self.active:
                self.active = False
                self._on_press_up(event)
                if not valid_key:
                    return False
                self.focus.set()
                self.play_click_sound()
                self._on_valid_click(event)
                self._on_hover()
                if self.state != Clickable.State.DISABLED:
                    self.invoke()
                return True
            case KeyUpEvent():
                self.active = False
                return False
        return False

    def _valid_key(self, key: int) -> bool:
        return key in (Keyboard.Key.RETURN, Keyboard.Key.KP_ENTER)

    def _ignore_key_event(self, event: KeyEvent) -> bool:
        return event.key in (
            Keyboard.Key.NUMLOCK,
            Keyboard.Key.CAPSLOCK,
            Keyboard.Key.SCROLLOCK,
            Keyboard.Key.RSHIFT,
            Keyboard.Key.LSHIFT,
            Keyboard.Key.RCTRL,
            Keyboard.Key.LCTRL,
            Keyboard.Key.RALT,
            Keyboard.Key.LALT,
            Keyboard.Key.RMETA,
            Keyboard.Key.LMETA,
            Keyboard.Key.LSUPER,
            Keyboard.Key.RSUPER,
            Keyboard.Key.MODE,
        )

    def _should_ignore_event(self, event: Event) -> bool:
        return super()._should_ignore_event(event) or (
            isinstance(event, (KeyUpEvent, KeyDownEvent)) and self._ignore_key_event(event)
        )

    def _should_ignore_mouse_position(self, mouse_pos: tuple[float, float]) -> bool:
        return super()._should_ignore_mouse_position(mouse_pos) or self.focus.get_mode() == self.focus.Mode.KEY

    def _focus_handle_event(self, event: Event) -> bool:
        if isinstance(event, (KeyUpEvent, KeyDownEvent)) and self.__handle_key_press_event(event, focus_handle_event=True):
            return True
        return self.event.process_event(event)

    def _focus_update(self) -> None:
        match self.focus.get_mode():
            case self.focus.Mode.KEY:
                self.hover = self.focus.has()
            case self.focus.Mode.MOUSE if self.__focus_on_hover and self.hover and not self.focus.has():
                self.focus.set()

    def _on_valid_click(self, event: KeyUpEvent | MouseButtonUpEvent) -> None:
        self.focus.set()
        if isinstance(event, MouseButtonUpEvent):
            return super()._on_valid_click(event)

    def _on_hover(self) -> None:
        if self.__focus_on_hover:
            self.focus.set()
        return super()._on_hover()

    def _on_press_down(self, event: KeyDownEvent) -> None:
        pass

    def _on_press_up(self, event: KeyUpEvent) -> None:
        pass

    def _on_press_out(self, event: KeyDownEvent) -> None:
        pass

    def _on_focus_set(self) -> None:
        pass

    def _on_focus_leave(self) -> None:
        pass

    @cached_property
    def focus(self) -> BoundFocus:
        return BoundFocus(self, self.scene)
