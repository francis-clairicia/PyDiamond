# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ScaleBar module"""

from __future__ import annotations

__all__ = ["ScaleBar"]


import sys
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Sequence

from ...graphics.color import BLACK, BLUE, GRAY, WHITE, Color
from ...graphics.progress import ProgressBar
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.validation import valid_integer
from ...window.event import Event, KeyDownEvent, KeyEvent, KeyUpEvent, MouseButtonDownEvent, MouseMotionEvent
from .abc import AbstractWidget

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...system.theme import ThemeType
    from ...window.clickable import Clickable
    from ...window.cursor import Cursor
    from ...window.display import Window
    from ...window.scene import Scene


class ScaleBar(ProgressBar, AbstractWidget):
    __theme_ignore__: ClassVar[Sequence[str]] = (
        "from_",
        "to",
        "default",
        "orient",
        "value_callback",
        "percent_callback",
    )
    __theme_override__: Sequence[str] = ("cursor_thickness",)

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "resolution",
        "highlight_color",
        "highlight_thickness",
        parent=ProgressBar.config,
    )

    resolution: OptionAttribute[int] = OptionAttribute()
    highlight_color: OptionAttribute[Color] = OptionAttribute()
    highlight_thickness: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: AbstractWidget | Clickable | Scene | Window,
        width: float,
        height: float,
        *,
        from_: float = 0,
        to: float = 1,
        default: float | None = None,
        percent_default: float | None = None,
        orient: str = "horizontal",
        value_callback: Callable[[float], None] | None = None,
        percent_callback: Callable[[float], None] | None = None,
        resolution: int = sys.float_info.dig,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        color: Color = WHITE,
        scale_color: Color = GRAY,
        cursor_thickness: int = 2,
        outline: int = 2,
        outline_color: Color = BLACK,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ):
        self.resolution = resolution
        self.highlight_color = highlight_color
        self.highlight_thickness = highlight_thickness

        super().__init__(
            # ProgressBar
            width=width,
            height=height,
            from_=from_,
            to=to,
            default=default,
            percent_default=percent_default,
            orient=orient,
            color=color,
            scale_color=scale_color,
            cursor_thickness=cursor_thickness,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=theme,
            # AbstractWidget
            master=master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            # Other
            **kwargs,
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
        return self.get_rect().collidepoint(mouse_pos)

    def _should_ignore_event(self, event: Event) -> bool:
        return super()._should_ignore_event(event) or (
            isinstance(event, (KeyDownEvent, KeyUpEvent)) and self._ignore_key_event(event)
        )

    def _ignore_key_event(self, event: KeyEvent) -> bool:
        return True

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        if self.active:
            self.__compute_scale_percent_by_mouse_pos(event.pos)
        return super()._on_click_down(event)

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        if self.active:
            self.__compute_scale_percent_by_mouse_pos(event.pos)
        return super()._on_mouse_motion(event)

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        super()._apply_only_scale()

    def _on_focus_set(self) -> None:
        self.__update_shape_outline()
        return super()._on_focus_set()

    def _on_focus_leave(self) -> None:
        self.__update_shape_outline()
        return super()._on_focus_leave()

    def __update_shape_outline(self) -> None:
        outline_color: Color
        outline: int
        if self.focus.has():
            outline_color = self.highlight_color
            outline = max(self.highlight_thickness, self.outline)
        else:
            outline_color = self.outline_color
            outline = self.outline
        super().config.only_set("outline", outline)
        super().config.only_set("outline_color", outline_color)

    def __compute_scale_percent_by_mouse_pos(self, mouse_pos: tuple[float, float]) -> None:
        if self.orient == ScaleBar.Orient.HORIZONTAL:
            self.percent = (mouse_pos[0] - self.left) / self.width
        else:
            self.percent = (mouse_pos[1] - self.top) / self.height

    config.add_value_validator_static("resolution", int)

    @config.add_value_validator_static("resolution")
    @staticmethod
    def __valid_resolution(value: int) -> None:
        max_float_digits = sys.float_info.dig
        if not (0 <= value <= max_float_digits):
            raise ValueError(f"resolution must be between 0 and sys.float_info.dig (actually: {max_float_digits}) included")

    @config.on_update("resolution")
    def __on_update_resolution(self) -> None:
        self.config.only_reset("value")

    @config.add_value_converter_on_set("value")
    def __apply_resolution_on_value(self, value: float) -> float:
        return round(value, self.resolution)

    @config.add_value_converter_on_set("percent")
    def __apply_resolution_on_percent(self, percent: float) -> float:
        start: float = self.from_value
        end: float = self.to_value
        if end <= start:
            return 0
        value: float = round(start + (percent * (end - start)), self.resolution)
        percent = (value - start) / (end - start)
        return percent

    config.reset_getter_setter_deleter("outline")
    config.reset_getter_setter_deleter("outline_color")

    config.add_value_validator_static("highlight_color", Color)
    config.add_value_converter_on_set_static("highlight_thickness", valid_integer(min_value=0))

    config.on_update("outline", __update_shape_outline)
    config.on_update("outline_color", __update_shape_outline)
    config.on_update("highlight_color", __update_shape_outline)
    config.on_update("highlight_thickness", __update_shape_outline)

    config.on_update("value", invoke)
    config.on_update("percent", invoke)
