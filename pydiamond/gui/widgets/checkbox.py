# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Checkbox module"""

from __future__ import annotations

__all__ = ["BooleanCheckBox", "CheckBox"]

from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic, Sequence, TypeVar

from ...graphics.color import BLACK, BLUE, Color
from ...graphics.drawable import Drawable
from ...graphics.image import Image
from ...graphics.shape import DiagonalCrossShape, RectangleShape
from ...graphics.surface import Surface
from ...graphics.transformable import Transformable
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.theme import ThemedObjectMeta, ThemeType
from ...system.validation import valid_integer
from .abc import AbstractWidget

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...graphics.renderer import AbstractRenderer
    from ...window.clickable import Clickable
    from ...window.cursor import Cursor
    from ...window.display import Window
    from ...window.scene import Scene

_OnValue = TypeVar("_OnValue")
_OffValue = TypeVar("_OffValue")

NoDefaultValue: Any = object()


class CheckBox(Drawable, Transformable, AbstractWidget, Generic[_OnValue, _OffValue], metaclass=ThemedObjectMeta):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "value",
        "local_width",
        "local_height",
        "local_size",
        "color",
        "outline",
        "outline_color",
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
        "highlight_color",
        "highlight_thickness",
    )

    value: OptionAttribute[_OnValue | _OffValue] = OptionAttribute()
    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()
    color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()
    highlight_color: OptionAttribute[Color] = OptionAttribute()
    highlight_thickness: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: AbstractWidget | Clickable | Scene | Window,
        width: float,
        height: float,
        color: Color,
        callback: Callable[[_OnValue | _OffValue], None] | None = None,
        *,
        off_value: _OffValue,
        on_value: _OnValue,
        value: _OnValue | _OffValue = NoDefaultValue,
        outline: int = 2,
        outline_color: Color = BLACK,
        img: Surface | None = None,
        callback_at_init: bool = True,
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        state: str = "normal",
        take_focus: bool = True,
        focus_on_hover: bool | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        if on_value == off_value:
            raise ValueError("'On' value and 'Off' value are identical")
        super().__init__(
            master=master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            take_focus=take_focus,
            focus_on_hover=focus_on_hover,
            **kwargs,
        )
        self.__shape: RectangleShape = RectangleShape(
            width=width,
            height=height,
            color=color,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        self.outline = outline
        self.outline_color = outline_color
        self.highlight_color = highlight_color
        self.highlight_thickness = highlight_thickness
        self.__cross_aspect_ratio: float = 0.7
        self.__cross: DiagonalCrossShape = DiagonalCrossShape(
            width=self.__cross_aspect_ratio * width,
            height=self.__cross_aspect_ratio * height,
            color=outline_color,
            line_width_percent=0.2,
        )
        self.__on_changed_value: Callable[[_OnValue | _OffValue], None] | None = callback
        self.__active_img: Image | None = Image(img) if img is not None else None
        self.__on_value: _OnValue = on_value
        self.__off_value: _OffValue = off_value
        self.__value: _OnValue | _OffValue = off_value
        if value in (on_value, off_value):
            self.__value = value
        elif value is not NoDefaultValue:
            raise ValueError("'value' parameter doesn't fit with on/off values")
        if callback_at_init and callable(callback):
            callback(self.__value)

    def draw_onto(self, target: AbstractRenderer) -> None:
        shape: RectangleShape = self.__shape
        active_img: Image | None = self.__active_img
        active: Image | DiagonalCrossShape
        active_cross: DiagonalCrossShape = self.__cross

        shape.center = center = self.center
        shape.draw_onto(target)
        if self.__value == self.__on_value:
            if active_img is not None:
                active = active_img
            else:
                active = active_cross
            active.center = center
            active.draw_onto(target)

    def get_local_size(self) -> tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self) -> None:
        self.value = self.__on_value if self.value == self.__off_value else self.__off_value

    def get_value(self) -> _OnValue | _OffValue:
        return self.__value

    def set_value(self, value: _OnValue | _OffValue) -> None:
        if value not in (self.__on_value, self.__off_value):
            raise ValueError(f"{value!r} is not {self.__on_value!r} or {self.__off_value!r}")
        if value == self.__value:
            return
        self.__value = value
        callback = self.__on_changed_value
        if callable(callback):
            callback(value)

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.__shape.get_rect().collidepoint(mouse_pos)

    def _apply_both_rotation_and_scale(self) -> None:
        angle: float = self.angle
        scale: tuple[float, float] = self.scale
        self.__shape.set_rotation_and_scale(angle, scale)
        if self.__active_img is not None:
            self.__active_img.set_rotation_and_scale(angle, scale)
        self.__cross.set_rotation_and_scale(angle, scale)

    def _apply_only_rotation(self) -> None:
        angle: float = self.angle
        self.__shape.set_rotation(angle)
        if self.__active_img is not None:
            self.__active_img.set_rotation(angle)
        self.__cross.set_rotation(angle)

    def _apply_only_scale(self) -> None:
        scale: tuple[float, float] = self.scale
        self.__shape.set_scale(scale)
        if self.__active_img is not None:
            self.__active_img.set_scale(scale)
        self.__cross.set_scale(scale)

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
        self.__shape.config.update(outline=outline, outline_color=outline_color)

    config.getter("value", get_value)
    config.setter("value", set_value)

    @config.getter_with_key("local_width")
    @config.getter_with_key("local_height")
    @config.getter_with_key("local_size")
    @config.getter_with_key("color")
    @config.getter_with_key("border_radius")
    @config.getter_with_key("border_top_left_radius")
    @config.getter_with_key("border_top_right_radius")
    @config.getter_with_key("border_bottom_left_radius")
    @config.getter_with_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_with_key("local_width")
    @config.setter_with_key("local_height")
    @config.setter_with_key("local_size")
    @config.setter_with_key("color")
    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> Any:
        return self.__shape.config.set(option, value)

    config.add_value_converter_on_set_static("outline", valid_integer(min_value=0))
    config.add_value_validator_static("outline_color", Color)
    config.add_value_validator_static("highlight_color", Color)
    config.add_value_converter_on_set_static("highlight_thickness", valid_integer(min_value=0))

    config.on_update("outline", __update_shape_outline)
    config.on_update("outline_color", __update_shape_outline)
    config.on_update("highlight_color", __update_shape_outline)
    config.on_update("highlight_thickness", __update_shape_outline)

    @property
    def img(self) -> Surface | None:
        return self.__active_img.get() if self.__active_img is not None else None

    @property
    def on_value(self) -> _OnValue:
        return self.__on_value

    @property
    def off_value(self) -> _OffValue:
        return self.__off_value

    @property
    def callback(self) -> Callable[[_OnValue | _OffValue], None] | None:
        return self.__on_changed_value


class BooleanCheckBox(CheckBox[bool, bool]):
    __theme_ignore__: Sequence[str] = (
        "on_value",
        "off_value",
    )

    def __init__(
        self,
        master: AbstractWidget | Clickable | Scene | Window,
        width: float,
        height: float,
        color: Color,
        *,
        off_value: bool = False,
        on_value: bool = True,
        value: bool = NoDefaultValue,
        outline: int = 2,
        outline_color: Color = BLACK,
        img: Surface | None = None,
        callback: Callable[[bool], None] | None = None,
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        state: str = "normal",
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__(
            master=master,
            width=width,
            height=height,
            color=color,
            off_value=bool(off_value),
            on_value=bool(on_value),
            value=value,
            outline=outline,
            outline_color=outline_color,
            img=img,
            callback=callback,
            highlight_color=highlight_color,
            highlight_thickness=highlight_thickness,
            state=state,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=theme,
        )
