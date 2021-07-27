# -*- coding: Utf-8 -*

from abc import ABCMeta, abstractmethod
from typing import Callable, Dict, Optional, Tuple, Union
from enum import Enum, unique
from operator import truth

import pygame

from pygame.event import Event
from pygame.mixer import Sound

from .scene import Scene
from .window import Window
from .mouse import Mouse
from .drawable import Drawable


class Clickable(metaclass=ABCMeta):
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
        on_click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        # cursor=None,
        # disabled_cursor=None
    ) -> None:
        self.__master: Window
        self.__scene: Optional[Scene]
        if isinstance(master, Scene):
            self.__master = master.window
            self.__scene = master
        else:
            self.__master = master
            self.__scene = None
        self.__state: Clickable.State = Clickable.State.NORMAL
        self.__hover: bool = False
        self.__active: bool = False
        self.__hover_sound: Optional[Sound] = None
        self.__on_click_sound: Dict[Clickable.State, Optional[Sound]] = dict.fromkeys(Clickable.State)

        self.state = state
        self.hover_sound = hover_sound
        self.on_click_sound = on_click_sound
        self.disabled_sound = disabled_sound
        master.bind_event(pygame.MOUSEBUTTONDOWN, self.__handle_click_event)
        master.bind_event(pygame.MOUSEBUTTONUP, self.__handle_click_event)
        master.bind_event(pygame.MOUSEMOTION, lambda event: self._on_mouse_motion(event))
        master.bind_mouse_position(self.__handle_mouse_position)

    @abstractmethod
    def invoke(self) -> None:
        raise NotImplementedError

    def play_hover_sound(self) -> None:
        hover_sound: Optional[Sound] = self.__hover_sound
        if hover_sound is not None:
            hover_sound.play()

    def play_on_click_sound(self) -> None:
        on_click_sound: Optional[Sound] = self.__on_click_sound[self.__state]
        if on_click_sound is not None:
            on_click_sound.play()

    def __handle_click_event(self, event: Event) -> None:
        if isinstance(self, Drawable) and not self.is_shown():
            return

        valid_click: Callable[[], bool] = lambda: event.button == Mouse.LEFT and self._mouse_in_hitbox(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN:
            if valid_click():
                self.active = True
                self._on_click_down(event)
        elif event.type == pygame.MOUSEBUTTONUP:
            active, self.active = self.active, False
            if not active:
                return
            self._on_click_up(event)
            if valid_click():
                self.play_on_click_sound()
                self._on_hover()
                if self.__state != Clickable.State.DISABLED:
                    self.invoke()

    def __handle_mouse_position(self, mouse_pos: Tuple[float, float]) -> None:
        if isinstance(self, Drawable) and not self.is_shown():
            return
        self.hover = self._mouse_in_hitbox(mouse_pos)

    @abstractmethod
    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        raise NotImplementedError

    def _on_change_state(self) -> None:
        pass

    def _on_click_down(self, event: Event) -> None:
        pass

    def _on_click_up(self, event: Event) -> None:
        pass

    def _on_mouse_motion(self, event: Event) -> None:
        pass

    def _on_hover(self) -> None:
        pass

    def _on_leave(self) -> None:
        pass

    def _on_active_set(self) -> None:
        pass

    @property
    def master(self) -> Window:
        return self.__master

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
        return truth(self.__active and self.__hover)

    @active.setter
    def active(self, status: bool) -> None:
        status = truth(status)
        if status == self.__active:
            return
        self.__active = status
        if status is True:
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
    def on_click_sound(self) -> Optional[Sound]:
        return self.__on_click_sound[Clickable.State.NORMAL]

    @on_click_sound.setter
    def on_click_sound(self, sound: Optional[Sound]) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__on_click_sound[Clickable.State.NORMAL] = sound

    @property
    def disabled_sound(self) -> Optional[Sound]:
        return self.__on_click_sound[Clickable.State.DISABLED]

    @disabled_sound.setter
    def disabled_sound(self, sound: Optional[Sound]) -> None:
        if sound is not None and not isinstance(sound, Sound):
            raise TypeError(f"sound must be a '{Sound.__module__}.{Sound.__name__}' object")
        self.__on_click_sound[Clickable.State.DISABLED] = sound
