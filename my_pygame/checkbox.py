# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, Callable, Generic, Optional, Tuple, TypeVar, Union
from operator import truth

from pygame.color import Color
from pygame.mixer import Sound
from pygame.surface import Surface

from .drawable import Drawable, ThemedDrawable
from .clickable import Clickable
from .colors import BLACK
from .window import Window
from .scene import Scene
from .shape import RectangleShape, DiagonalCrossShape
from .image import Image
from .cursor import Cursor
from .theme import NoTheme, ThemeType
from .configuration import ConfigAttribute, Configuration

__all__ = ["CheckBox", "BooleanCheckBox"]

_OnValue = TypeVar("_OnValue")
_OffValue = TypeVar("_OffValue")

NoDefaultValue: Any = object()


@RectangleShape.register
class CheckBox(ThemedDrawable, Clickable, Generic[_OnValue, _OffValue]):
    def __init__(
        self,
        master: Union[Scene, Window],
        width: float,
        height: float,
        color: Color,
        callback: Optional[Callable[[Union[_OnValue, _OffValue]], None]] = None,
        *,
        off_value: _OffValue,
        on_value: _OnValue,
        value: Union[_OnValue, _OffValue] = NoDefaultValue,
        outline: int = 2,
        outline_color: Color = BLACK,
        img: Optional[Surface] = None,
        callback_at_init: bool = True,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        state: str = "normal",
        cursor: Optional[Cursor] = None,
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
        ThemedDrawable.__init__(self)
        Clickable.__init__(
            self,
            master=master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            cursor=cursor,
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
        self.__cross: DiagonalCrossShape = DiagonalCrossShape(
            width=0.7 * width, height=0.7 * height, color=outline_color, line_width=0.2, theme=NoTheme
        )
        self.__on_changed_value: Optional[Callable[[Union[_OnValue, _OffValue]], None]] = callback
        self.__active_img: Optional[Image] = Image(img) if img is not None else None
        self.__on_value: _OnValue = on_value
        self.__off_value: _OffValue = off_value
        self.__value: Union[_OnValue, _OffValue] = off_value
        if value in [on_value, off_value]:
            self.__value = value
        elif value is not NoDefaultValue:
            raise ValueError(f"'value' parameter doesn't fit with on/off values")
        if callback_at_init and callable(callback):
            callback(self.__value)

    def copy(self) -> CheckBox[_OnValue, _OffValue]:
        return CheckBox(
            master=self.master,
            width=self.__shape.local_width,
            height=self.__shape.local_height,
            color=self.__shape.color,
            off_value=self.__off_value,
            on_value=self.__on_value,
            value=self.__value,
            outline=self.__shape.outline,
            outline_color=self.__shape.outline_color,
            img=self.__active_img.get() if self.__active_img is not None else None,
            callback=self.__on_changed_value,
            state=self.state,
            cursor=self.cursor,
            disabled_cursor=self.disabled_cursor,
            hover_sound=self.hover_sound,
            click_sound=self.click_sound,
            disabled_sound=self.disabled_sound,
            theme=NoTheme,
        )

    def draw_onto(self, surface: Surface) -> None:
        shape: RectangleShape = self.__shape
        active_img: Optional[Image] = self.__active_img
        active: Drawable
        active_cross: DiagonalCrossShape = self.__cross

        shape.center = center = self.center
        shape.draw_onto(surface)
        if self.__value == self.__on_value:
            if active_img is not None:
                active = active_img
            else:
                active = active_cross
            active.center = center
            active.draw_onto(surface)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> Tuple[float, float]:
        return self.__shape.get_size()

    def __invoke__(self) -> None:
        self.value = self.__on_value if self.value == self.__off_value else self.__off_value

    def get_value(self) -> Union[_OnValue, _OffValue]:
        return self.__value

    def set_value(self, value: Union[_OnValue, _OffValue]) -> None:
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

    def _apply_rotation_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        self.__shape.set_rotation(angle)
        self.__shape.set_scale(scale)
        if self.__active_img is not None:
            self.__active_img.set_rotation(angle)
            self.__active_img.set_scale(scale)
        w, h = self.__shape.get_size()
        self.__cross.local_size = (0.7 * w), (0.7 * h)

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

    value: ConfigAttribute[Union[_OnValue, _OffValue]] = ConfigAttribute()
    local_width: ConfigAttribute[float] = ConfigAttribute()
    local_height: ConfigAttribute[float] = ConfigAttribute()
    local_size: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    color: ConfigAttribute[Color] = ConfigAttribute()
    outline: ConfigAttribute[int] = ConfigAttribute()
    outline_color: ConfigAttribute[Color] = ConfigAttribute()
    border_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_right_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_right_radius: ConfigAttribute[int] = ConfigAttribute()

    config.getter_no_name("value", get_value)
    config.setter_no_name("value", set_value)

    @config.getter("local_width")
    @config.getter("local_height")
    @config.getter("local_size")
    @config.getter("color")
    @config.getter("outline")
    @config.getter("outline_color")
    @config.getter("border_radius")
    @config.getter("border_top_left_radius")
    @config.getter("border_top_right_radius")
    @config.getter("border_bottom_left_radius")
    @config.getter("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter("local_width")
    @config.setter("local_height")
    @config.setter("local_size")
    @config.setter("color")
    @config.setter("outline")
    @config.setter("outline_color")
    @config.setter("border_radius")
    @config.setter("border_top_left_radius")
    @config.setter("border_top_right_radius")
    @config.setter("border_bottom_left_radius")
    @config.setter("border_bottom_right_radius")
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
    def callback(self) -> Optional[Callable[[Union[_OnValue, _OffValue]], None]]:
        return self.__on_changed_value


class BooleanCheckBox(CheckBox[bool, bool]):
    def __init__(
        self,
        master: Union[Scene, Window],
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
        cursor: Optional[Cursor] = None,
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
            value=truth(value),
            outline=outline,
            outline_color=outline_color,
            img=img,
            callback=callback,
            state=state,
            cursor=cursor,
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

    def copy(self) -> BooleanCheckBox:
        return BooleanCheckBox(
            master=self.master,
            width=self.local_width,
            height=self.local_height,
            color=self.color,
            off_value=self.off_value,
            on_value=self.on_value,
            value=self.value,
            outline=self.outline,
            outline_color=self.outline_color,
            img=self.img,
            callback=self.callback,
            state=self.state,
            cursor=self.cursor,
            disabled_cursor=self.disabled_cursor,
            hover_sound=self.hover_sound,
            click_sound=self.click_sound,
            disabled_sound=self.disabled_sound,
            theme=NoTheme,
        )
