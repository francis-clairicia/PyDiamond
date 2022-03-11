# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ScaleBar module"""

from __future__ import annotations

__all__ = ["ScaleBar"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from operator import truth
from typing import TYPE_CHECKING, Callable, ClassVar, Sequence

from ..system.configuration import Configuration, initializer
from ..window.clickable import Clickable
from ..window.event import MouseButtonDownEvent, MouseMotionEvent
from .color import BLACK, GRAY, WHITE, Color
from .progress import ProgressBar

if TYPE_CHECKING:
    from ..audio.sound import Sound
    from ..window.cursor import Cursor
    from ..window.display import Window
    from ..window.scene import Scene
    from .theme import ThemeType


class ScaleBar(ProgressBar, Clickable):
    __theme_ignore__: ClassVar[Sequence[str]] = (
        "from_",
        "to",
        "default",
        "orient",
        "value_callback",
        "percent_callback",
    )

    config = Configuration(parent=ProgressBar.config)

    @initializer
    def __init__(
        self,
        master: Scene | Window,
        width: float,
        height: float,
        *,
        from_: float = 0,
        to: float = 1,
        default: float | None = None,
        orient: str = "horizontal",
        value_callback: Callable[[float], None] | None = None,
        percent_callback: Callable[[float], None] | None = None,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
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
        theme: ThemeType | None = None,
    ):
        ProgressBar.__init__(
            self,
            width=width,
            height=height,
            from_=from_,
            to=to,
            default=default,
            orient=orient,
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
        self.__value_callback: Callable[[float], None] | None = value_callback
        self.__percent_callback: Callable[[float], None] | None = percent_callback
        self.set_active_only_on_hover(False)

    def invoke(self) -> None:
        callback: Callable[[float], None] | None

        callback = self.__value_callback
        if callable(callback):
            callback(self.value)

        callback = self.__percent_callback
        if callable(callback):
            callback(self.percent)

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return truth(self.rect.collidepoint(mouse_pos))

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        if self.active:
            self.__compute_scale_percent_by_mouse_pos(event.pos)
        return super()._on_click_down(event)

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        if self.active:
            self.__compute_scale_percent_by_mouse_pos(event.pos)
        return super()._on_mouse_motion(event)

    def __compute_scale_percent_by_mouse_pos(self, mouse_pos: tuple[float, float]) -> None:
        if self.orient == ScaleBar.Orient.HORIZONTAL:
            self.percent = (mouse_pos[0] - self.left) / self.width
        else:
            self.percent = (mouse_pos[1] - self.top) / self.height

    config.on_update("value", invoke)
    config.on_update("percent", invoke)
