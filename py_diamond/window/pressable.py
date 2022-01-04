# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Pressable objects module"""

__all__ = ["Pressable"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from operator import truth
from typing import Optional, Union

from ..audio.sound import Sound
from ..graphics.drawable import Drawable
from .clickable import Clickable
from .cursor import Cursor
from .display import Window
from .event import Event, KeyDownEvent, KeyEventType, KeyUpEvent
from .gui import SupportsFocus
from .keyboard import Keyboard
from .scene import Scene


class Pressable(Clickable):
    def __init__(
        self,
        /,
        master: Union[Scene, Window],
        *,
        state: str = "normal",
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
        take_focus: bool = True,
    ) -> None:
        Clickable.__init__(
            self,
            master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            take_focus=take_focus,
        )
        master.event.bind_event(Event.Type.KEYDOWN, self.__handle_key_press_event)
        master.event.bind_event(Event.Type.KEYUP, self.__handle_key_press_event)

    def __handle_key_press_event(self, /, event: KeyEventType) -> bool:
        if isinstance(self, Drawable) and not self.is_shown():
            self.active = self.hover = False
            return False

        valid_click: bool = truth(self._valid_key(event.key))
        if isinstance(self, SupportsFocus):
            self.hover = hover = self.focus.has()
            valid_click = valid_click and hover

        if isinstance(event, KeyDownEvent):
            if valid_click:
                self.active = True
                self._on_press_down(event)
                return True
            self._on_press_out(event)
        elif isinstance(event, KeyUpEvent):
            active = self.active
            self.active = False
            if not active:
                return False
            self._on_press_up(event)
            if valid_click:
                self.play_click_sound()
                self._on_hover()
                if self.state != Clickable.State.DISABLED:
                    self.invoke()
                return True
        return False

    def _valid_key(self, /, key: int) -> bool:
        return key in (Keyboard.Key.RETURN, Keyboard.Key.KP_ENTER)

    def _focus_update(self, /) -> None:
        super()._focus_update()
        if isinstance(self, SupportsFocus) and self.focus.get_mode() == self.focus.Mode.KEY:
            self.hover = self.focus.has()

    def _on_press_down(self, /, event: KeyDownEvent) -> None:
        pass

    def _on_press_up(self, /, event: KeyUpEvent) -> None:
        pass

    def _on_press_out(self, /, event: KeyDownEvent) -> None:
        pass