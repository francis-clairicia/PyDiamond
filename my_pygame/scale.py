# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Callable, Optional, Tuple, Union
from operator import truth

from pygame.color import Color
from pygame.mixer import Sound
from pygame.event import Event

from .colors import BLACK, GRAY, WHITE
from .cursor import Cursor
from .clickable import Clickable
from .progress import ProgressBar
from .theme import NoTheme, ThemeType
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
        callback: Optional[Callable[[float], None]] = None,
        *,
        state: str = "normal",
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        cursor: Optional[Cursor] = None,
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
            cursor=cursor,
            disabled_cursor=disabled_cursor,
        )
        self.__callback: Optional[Callable[[float], None]] = callback
        self.set_active_only_on_hover(False)

    def copy(self) -> Scale:
        return Scale(
            master=self.master,
            width=self.local_width,
            height=self.local_height,
            from_=self.from_value,
            to=self.to_value,
            default=self.value,
            callback=self.__callback,
            state=self.state,
            hover_sound=self.hover_sound,
            click_sound=self.click_sound,
            disabled_sound=self.disabled_sound,
            cursor=self.cursor,
            disabled_cursor=self.disabled_cursor,
            color=self.color,
            scale_color=self.scale_color,
            outline=self.outline,
            outline_color=self.outline_color,
            border_radius=self.border_radius,
            border_top_left_radius=self.border_top_left_radius,
            border_top_right_radius=self.border_top_right_radius,
            border_bottom_left_radius=self.border_bottom_left_radius,
            border_bottom_right_radius=self.border_bottom_right_radius,
            theme=NoTheme,
        )

    def __invoke__(self) -> None:
        pass

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        return truth(self.rect.collidepoint(mouse_pos))

    def _on_click_down(self, event: Event) -> None:
        if self.active:
            self._on_mouse_motion(event)

    def _on_mouse_motion(self, event: Event) -> None:
        mouse_pos: Tuple[float, float] = event.pos
        if self.active:
            self.percent = (mouse_pos[0] - self.x) / self.width

    config = Configuration(parent=ProgressBar.config)

    @config.updater("value")
    @config.updater("percent")
    def __call_updater_callback(self) -> None:
        default_updater: Optional[Callable[[object], None]] = ProgressBar.config.get_updater("value")
        if callable(default_updater):
            default_updater(self)
        callback: Optional[Callable[[float], None]] = self.__callback
        if callable(callback):
            callback(self.value)
