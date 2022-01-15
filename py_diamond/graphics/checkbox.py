# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Checkbox module"""

from __future__ import annotations

__all__ = ["BooleanCheckBox", "CheckBox", "MetaCheckBox"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from operator import truth
from typing import TYPE_CHECKING, Any, Callable, Generic, Optional, Tuple, TypeVar

from ..system.configuration import Configuration, OptionAttribute
from ..window.clickable import Clickable
from .color import BLACK, Color
from .drawable import MetaTDrawable, TDrawable
from .image import Image
from .shape import DiagonalCrossShape, RectangleShape
from .surface import Surface
from .theme import MetaThemedObject, NoTheme, ThemeType

if TYPE_CHECKING:
    from ..audio.sound import Sound
    from ..window.cursor import Cursor
    from ..window.display import Window
    from ..window.scene import Scene
    from .renderer import Renderer

_OnValue = TypeVar("_OnValue")
_OffValue = TypeVar("_OffValue")

NoDefaultValue: Any = object()


class MetaCheckBox(MetaTDrawable, MetaThemedObject):
    pass


@RectangleShape.register_themed_subclass
class CheckBox(TDrawable, Clickable, Generic[_OnValue, _OffValue], metaclass=MetaCheckBox):
    config: Configuration = Configuration(
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
    )

    value: OptionAttribute[_OnValue | _OffValue] = OptionAttribute()
    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    def __init__(
        self,
        master: Scene | Window,
        width: float,
        height: float,
        color: Color,
        callback: Optional[Callable[[_OnValue | _OffValue], None]] = None,
        *,
        off_value: _OffValue,
        on_value: _OnValue,
        value: _OnValue | _OffValue = NoDefaultValue,
        outline: int = 2,
        outline_color: Color = BLACK,
        img: Optional[Surface] = None,
        callback_at_init: bool = True,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        state: str = "normal",
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: Optional[ThemeType] = None,
    ) -> None:
        if on_value == off_value:
            raise ValueError("'On' value and 'Off' value are identical")
        TDrawable.__init__(self)
        Clickable.__init__(
            self,
            master=master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
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
            theme=NoTheme,
        )
        self.__cross_aspect_ratio: float = 0.7
        self.__cross: DiagonalCrossShape = DiagonalCrossShape(
            width=self.__cross_aspect_ratio * width,
            height=self.__cross_aspect_ratio * height,
            color=outline_color,
            line_width=0.2,
            theme=NoTheme,
        )
        self.__on_changed_value: Optional[Callable[[_OnValue | _OffValue], None]] = callback
        self.__active_img: Optional[Image] = Image(img) if img is not None else None
        self.__on_value: _OnValue = on_value
        self.__off_value: _OffValue = off_value
        self.__value: _OnValue | _OffValue = off_value
        if value in [on_value, off_value]:
            self.__value = value
        elif value is not NoDefaultValue:
            raise ValueError(f"'value' parameter doesn't fit with on/off values")
        if callback_at_init and callable(callback):
            callback(self.__value)

    def draw_onto(self, target: Renderer) -> None:
        shape: RectangleShape = self.__shape
        active_img: Optional[Image] = self.__active_img
        active: TDrawable
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

    def get_local_size(self) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> Tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self) -> None:
        self.value = self.__on_value if self.value == self.__off_value else self.__off_value

    def get_value(self) -> _OnValue | _OffValue:
        return self.__value

    def set_value(self, value: _OnValue | _OffValue) -> None:
        if value not in [self.__on_value, self.__off_value]:
            raise ValueError(f"{value!r} is not {self.__on_value!r} or {self.__off_value!r}")
        if value == self.__value:
            return
        self.__value = value
        callback = self.__on_changed_value
        if callable(callback):
            callback(value)

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        return truth(self.__shape.rect.collidepoint(mouse_pos))

    def _apply_both_rotation_and_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        self.__shape.set_rotation(angle)
        self.__shape.set_scale(scale)
        if self.__active_img is not None:
            self.__active_img.set_rotation(angle)
            self.__active_img.set_scale(scale)
        self.__cross.set_rotation(angle)
        self.__cross.set_scale(scale)

    def _apply_only_rotation(self) -> None:
        angle: float = self.angle
        self.__shape.set_rotation(angle)
        if self.__active_img is not None:
            self.__active_img.set_rotation(angle)
        self.__cross.set_rotation(angle)

    def _apply_only_scale(self) -> None:
        scale: float = self.scale
        self.__shape.set_scale(scale)
        if self.__active_img is not None:
            self.__active_img.set_scale(scale)
        self.__cross.set_scale(scale)

    config.getter("value", get_value)
    config.setter("value", set_value)

    @config.getter_key("local_width")
    @config.getter_key("local_height")
    @config.getter_key("local_size")
    @config.getter_key("color")
    @config.getter_key("outline")
    @config.getter_key("outline_color")
    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_key("local_width")
    @config.setter_key("local_height")
    @config.setter_key("local_size")
    @config.setter_key("color")
    @config.setter_key("outline")
    @config.setter_key("outline_color")
    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> Any:
        return self.__shape.config.set(option, value)

    @property
    def img(self) -> Optional[Surface]:
        return self.__active_img.get() if self.__active_img is not None else None

    @property
    def on_value(self) -> _OnValue:
        return self.__on_value

    @property
    def off_value(self) -> _OffValue:
        return self.__off_value

    @property
    def callback(self) -> Optional[Callable[[_OnValue | _OffValue], None]]:
        return self.__on_changed_value


class BooleanCheckBox(CheckBox[bool, bool]):
    def __init__(
        self,
        master: Scene | Window,
        width: float,
        height: float,
        color: Color,
        *,
        off_value: bool = False,
        on_value: bool = True,
        value: bool = NoDefaultValue,
        outline: int = 2,
        outline_color: Color = BLACK,
        img: Optional[Surface] = None,
        callback: Optional[Callable[[bool], None]] = None,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        state: str = "normal",
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(
            master=master,
            width=width,
            height=height,
            color=color,
            off_value=truth(off_value),
            on_value=truth(on_value),
            value=value,
            outline=outline,
            outline_color=outline_color,
            img=img,
            callback=callback,
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
