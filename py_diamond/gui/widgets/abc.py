# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Widgets module"""

from __future__ import annotations

__all__ = ["AbstractWidget"]


from functools import cached_property
from typing import TYPE_CHECKING, ClassVar

from ...audio.sound import Sound
from ...window.clickable import Clickable
from ...window.cursor import AbstractCursor
from ...window.display import Window
from ...window.event import Event, KeyDownEvent, KeyEvent, KeyUpEvent, MouseButtonUpEvent
from ...window.keyboard import Keyboard
from ...window.scene import Scene
from ..focus import BoundFocus, BoundFocusMode
from ..scene import GUIScene


class AbstractWidget(Clickable):
    __default_focus_on_hover: ClassVar[bool] = False

    def __init__(
        self,
        master: AbstractWidget | Clickable | Scene | Window,
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
        self.__focus_on_hover: bool = bool(focus_on_hover)
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

    def get_focus_on_hover(self) -> bool:
        return self.__focus_on_hover

    def set_focus_on_hover(self, status: bool) -> None:
        self.__focus_on_hover = focus_on_hover = bool(status)
        if focus_on_hover and self.hover:
            self.focus.set()

    @classmethod
    def set_default_focus_on_hover(cls, status: bool | None) -> None:
        if status is not None:
            cls.__default_focus_on_hover = bool(status)
            return
        if cls is AbstractWidget:
            cls.__default_focus_on_hover = False
        else:
            try:
                del cls.__default_focus_on_hover
            except AttributeError:
                pass

    @classmethod
    def get_default_focus_on_hover(cls) -> bool:
        return cls.__default_focus_on_hover

    def __handle_key_press_event(self, event: KeyEvent, focus_handle_event: bool) -> bool:
        if not isinstance(self.scene, GUIScene) or self._should_ignore_event(event):
            return False

        if event.key in (
            Keyboard.Key.K_NUMLOCK,
            Keyboard.Key.K_CAPSLOCK,
            Keyboard.Key.K_SCROLLOCK,
            Keyboard.Key.K_RSHIFT,
            Keyboard.Key.K_LSHIFT,
            Keyboard.Key.K_RCTRL,
            Keyboard.Key.K_LCTRL,
            Keyboard.Key.K_RALT,
            Keyboard.Key.K_LALT,
            Keyboard.Key.K_RMETA,
            Keyboard.Key.K_LMETA,
            Keyboard.Key.K_LSUPER,
            Keyboard.Key.K_RSUPER,
            Keyboard.Key.K_MODE,
        ):
            return False

        if not self.is_shown():
            self.active = self.hover = False
            return False

        if not focus_handle_event:
            if not self.focus.has():
                self.active = self.hover = False
            return False

        valid_key: bool = bool(self._valid_key(event.key)) and self.hover

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
        return key in (Keyboard.Key.K_RETURN, Keyboard.Key.K_KP_ENTER)

    def _should_ignore_mouse_position(self, mouse_pos: tuple[float, float]) -> bool:
        return super()._should_ignore_mouse_position(mouse_pos) or self.focus.get_mode() == BoundFocusMode.KEY

    def _focus_handle_event(self, event: Event) -> bool:
        if isinstance(event, (KeyUpEvent, KeyDownEvent)) and self.__handle_key_press_event(event, focus_handle_event=True):
            return True
        return self.event.process_event(event)

    def _focus_update(self) -> None:
        match self.focus.get_mode():
            case BoundFocusMode.KEY:
                self.hover = self.focus.has()
            case BoundFocusMode.MOUSE if self.__focus_on_hover and self.hover and not self.focus.has():
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

    if TYPE_CHECKING:

        @property
        def master(self) -> AbstractWidget | Clickable | Scene | Window:
            ...

    @cached_property
    def focus(self) -> BoundFocus:
        return BoundFocus(self, self.scene)
