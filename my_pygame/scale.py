# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Callable, Optional, Tuple, Union
from operator import truth

from pygame.color import Color
from pygame.mixer import Sound

from my_pygame.event import MouseButtonDownEvent, MouseMotionEvent

from .colors import BLACK, GRAY, WHITE
from .cursor import Cursor
from .clickable import Clickable
from .progress import ProgressBar
from .theme import ThemeType
from .scene import Scene
from .window import Window
from .configuration import Configuration, initializer


class Scale(ProgressBar, Clickable):
    @initializer
    def __init__(
        self,
        master: Union[Scene, Window],
        width: float,
        height: float,
        from_: float = 0,
        to: float = 1,
        default: Optional[float] = None,
        value_callback: Optional[Callable[[float], None]] = None,
        percent_callback: Optional[Callable[[float], None]] = None,
        *,
        state: str = "normal",
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
        color: Color = WHITE,
        scale_color: Color = GRAY,
        outline: int = 2,
        outline_color: Color = BLACK,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        theme: Optional[ThemeType] = None,
    ):
        ProgressBar.__init__(
            self,
            width=width,
            height=height,
            from_=from_,
            to=to,
            default=default,
            color=color,
            scale_color=scale_color,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=theme,
        )
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
        self.__value_callback: Optional[Callable[[float], None]] = value_callback
        self.__percent_callback: Optional[Callable[[float], None]] = percent_callback
        self.set_active_only_on_hover(False)

    def __invoke__(self) -> None:
        callback: Optional[Callable[[float], None]]

        callback = self.__value_callback
        if callable(callback):
            callback(self.value)

        callback = self.__percent_callback
        if callable(callback):
            callback(self.percent)

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        return truth(self.rect.collidepoint(mouse_pos))

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        if self.active:
            mouse_pos: Tuple[float, float] = event.pos
            self.percent = (mouse_pos[0] - self.x) / self.width

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        mouse_pos: Tuple[float, float] = event.pos
        if self.active:
            self.percent = (mouse_pos[0] - self.x) / self.width

    config = Configuration(parent=ProgressBar.config)

    config.updater("value", __invoke__)
    config.updater("percent", __invoke__)
