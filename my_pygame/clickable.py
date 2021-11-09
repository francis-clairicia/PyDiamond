# -*- coding: Utf-8 -*

from abc import abstractmethod
from typing import Dict, Optional, Tuple, Union
from enum import Enum, unique
from operator import truth

from pygame.mixer import Sound

from .scene import Scene
from .event import (
    Event,
    MouseButtonDownEvent,
    MouseButtonEvent,
    MouseButtonUpEvent,
    MouseMotionEvent,
)
from .window import Window
from .mouse import Mouse
from .drawable import Drawable
from .cursor import Cursor, SystemCursor

__all__ = ["Clickable"]


class Clickable:
    @unique
    class State(str, Enum):
        NORMAL = "normal"
        DISABLED = "disabled"

    def __init__(
        self,
        master: Union[Scene, Window],
        *,
        state: str = "normal",
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
    ) -> None:
        self.__master: Union[Scene, Window] = master
        self.__window: Window
        self.__scene: Optional[Scene]
        if isinstance(master, Scene):
            self.__window = master.window
            self.__scene = master
        else:
            self.__window = master
            self.__scene = None
        self.__state: Clickable.State = Clickable.State.NORMAL
        self.__hover: bool = False
        self.__active: bool = False
        self.__active_only_on_hover: bool = True
        self.__hover_sound: Optional[Sound] = None
        self.__click_sound: Dict[Clickable.State, Optional[Sound]] = dict.fromkeys(Clickable.State)
        self.__default_hover_cursor: Dict[Clickable.State, Cursor] = {
            Clickable.State.NORMAL: SystemCursor.CURSOR_HAND,
            Clickable.State.DISABLED: SystemCursor.CURSOR_NO,
        }
        self.__hover_cursor: Dict[Clickable.State, Cursor] = self.__default_hover_cursor.copy()
        if isinstance(hover_cursor, Cursor):
            self.__hover_cursor[Clickable.State.NORMAL] = hover_cursor
        if isinstance(disabled_cursor, Cursor):
            self.__hover_cursor[Clickable.State.DISABLED] = disabled_cursor

        self.state = state
        self.hover_sound = hover_sound
        self.click_sound = click_sound
        self.disabled_sound = disabled_sound
        master.bind_event(Event.Type.MOUSEBUTTONDOWN, self.__handle_click_event)
        master.bind_event(Event.Type.MOUSEBUTTONUP, self.__handle_click_event)
        master.bind_event(Event.Type.MOUSEMOTION, self._on_mouse_motion)
        master.bind_mouse_position(self.__handle_mouse_position)

    @abstractmethod
    def __invoke__(self) -> None:
        raise NotImplementedError

    def play_hover_sound(self) -> None:
        hover_sound: Optional[Sound] = self.__hover_sound
        if hover_sound is not None:
            hover_sound.play()

    def play_click_sound(self) -> None:
        click_sound: Optional[Sound] = self.__click_sound[self.__state]
        if click_sound is not None:
            click_sound.play()

    def get_default_cursor(self) -> Cursor:
        return self.__default_hover_cursor[Clickable.State.NORMAL]

    def get_default_disabled_cursor(self) -> Cursor:
        return self.__default_hover_cursor[Clickable.State.DISABLED]

    def set_cursor_to_default(self) -> None:
        self.__hover_cursor[Clickable.State.NORMAL] = self.__default_hover_cursor[Clickable.State.NORMAL]

    def set_disabled_cursor_to_default(self) -> None:
        self.__hover_cursor[Clickable.State.DISABLED] = self.__default_hover_cursor[Clickable.State.DISABLED]

    def set_active_only_on_hover(self, status: bool) -> None:
        self.__active_only_on_hover = truth(status)

    def __handle_click_event(self, event: MouseButtonEvent) -> None:
        if isinstance(self, Drawable) and not self.is_shown():
            return

        valid_click: bool = truth(event.button == Mouse.Button.LEFT and self._mouse_in_hitbox(event.pos))

        if isinstance(event, MouseButtonDownEvent):
            if valid_click:
                self.active = True
                self._on_click_down(event)
        elif isinstance(event, MouseButtonUpEvent):
            active, self.active = self.active, False
            if not active:
                return
            self._on_click_up(event)
            if valid_click:
                self.play_click_sound()
                self._on_hover()
                if self.__state != Clickable.State.DISABLED:
                    self.__invoke__()

    def __handle_mouse_position(self, mouse_pos: Tuple[float, float]) -> None:
        if isinstance(self, Drawable) and not self.is_shown():
            return
        self.hover = hover = self._mouse_in_hitbox(mouse_pos)
        if hover or (self.active and not self.__active_only_on_hover):
            self.__window.set_temporary_window_cursor(self.__hover_cursor[self.__state])

    @abstractmethod
    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        raise NotImplementedError

    def _on_change_state(self) -> None:
        pass

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        pass

    def _on_click_up(self, event: MouseButtonUpEvent) -> None:
        pass

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        pass

    def _on_hover(self) -> None:
        pass

    def _on_leave(self) -> None:
        pass

    def _on_active_set(self) -> None:
        pass

    @property
    def master(self) -> Union[Scene, Window]:
        return self.__master

    @property
    def window(self) -> Window:
        return self.__window

    @property
    def scene(self) -> Optional[Scene]:
        return self.__scene

    @property
    def state(self) -> str:
        return str(self.__state.value)

    @state.setter
    def state(self, state: str) -> None:
        if state == self.__state:
            return
        self.__state = Clickable.State(state)
        if self.hover:
            self._on_hover()
            if self.active:
                self._on_active_set()
        else:
            self._on_leave()
        self._on_change_state()

    @property
    def hover(self) -> bool:
        return self.__hover

    @hover.setter
    def hover(self, status: bool) -> None:
        status = truth(status)
        if status == self.__hover:
            return
        self.__hover = status
        if status is True:
            self.play_hover_sound()
            self._on_hover()
            if self.active:
                self._on_active_set()
        else:
            self._on_leave()

    @property
    def active(self) -> bool:
        return truth(self.__active and (self.__hover or not self.__active_only_on_hover))

    @active.setter
    def active(self, status: bool) -> None:
        status = truth(status)
        if status == self.__active:
            return
        self.__active = status
        if self.active:
            self._on_active_set()

    @property
    def hover_sound(self) -> Optional[Sound]:
        return self.__hover_sound

    @hover_sound.setter
    def hover_sound(self, sound: Optional[Sound]) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__hover_sound = sound

    @property
    def click_sound(self) -> Optional[Sound]:
        return self.__click_sound[Clickable.State.NORMAL]

    @click_sound.setter
    def click_sound(self, sound: Optional[Sound]) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__click_sound[Clickable.State.NORMAL] = sound

    @property
    def disabled_sound(self) -> Optional[Sound]:
        return self.__click_sound[Clickable.State.DISABLED]

    @disabled_sound.setter
    def disabled_sound(self, sound: Optional[Sound]) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__click_sound[Clickable.State.DISABLED] = sound

    @property
    def hover_cursor(self) -> Cursor:
        return self.__hover_cursor[Clickable.State.NORMAL]

    @hover_cursor.setter
    def hover_cursor(self, cursor: Cursor) -> None:
        self.__hover_cursor[Clickable.State.NORMAL] = cursor

    @property
    def disabled_cursor(self) -> Cursor:
        return self.__hover_cursor[Clickable.State.DISABLED]

    @disabled_cursor.setter
    def disabled_cursor(self, cursor: Cursor) -> None:
        self.__hover_cursor[Clickable.State.DISABLED] = cursor
