# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, Callable, Dict, Literal, Optional, Tuple, TypedDict, Union, overload
from enum import Enum, unique
from operator import truth

from pygame.color import Color
from pygame.font import Font
from pygame.math import Vector2
from pygame.mixer import Sound
from pygame.rect import Rect
from pygame.surface import Surface

from .drawable import ThemedDrawable
from .clickable import Clickable
from .shape import RectangleShape
from .text import TextImage
from .window import Window
from .scene import Scene
from .colors import TRANSPARENT, WHITE, GRAY, GRAY_LIGHT, GRAY_DARK, BLACK
from .theme import NoTheme, ThemeType
from .cursor import Cursor
from .image import Image
from .configuration import ConfigAttribute, Configuration, initializer, no_object
from .utils import valid_float

__all__ = ["Button", "ImageButton"]

_TextFont = Union[Font, Tuple[Optional[str], int]]


class _ButtonColor(TypedDict):
    normal: Color
    hover: Optional[Color]
    active: Optional[Color]


class _ImageDict(TypedDict):
    normal: Optional[Surface]
    hover: Optional[Surface]
    active: Optional[Surface]


class _ImageButtonDict(TypedDict):
    normal: Surface
    hover: Optional[Surface]
    active: Optional[Surface]


@overload
def _copy_color(c: Optional[Color]) -> Optional[Color]:
    ...


@overload
def _copy_color(c: Optional[Color], default: Color) -> Color:
    ...


def _copy_color(c: Optional[Color], default: Optional[Color] = None) -> Optional[Color]:
    return Color(c) if c is not None else (None if default is None else _copy_color(default))


@overload
def _copy_img(surface: Optional[Surface]) -> Optional[Surface]:
    ...


@overload
def _copy_img(surface: Optional[Surface], default: Surface) -> Surface:
    ...


def _copy_img(surface: Optional[Surface], default: Optional[Surface] = None) -> Optional[Surface]:
    return surface.copy() if surface is not None else (None if default is None else _copy_img(default))


@TextImage.register
@RectangleShape.register
class Button(ThemedDrawable, Clickable):
    Justify = TextImage.Justify
    Compound = TextImage.Compound

    @unique
    class HorizontalAlign(str, Enum):
        LEFT = "left"
        RIGHT = "right"
        CENTER = "center"

    @unique
    class VerticalAlign(str, Enum):
        TOP = "top"
        BOTTOM = "bottom"
        CENTER = "center"

    __HORIZONTAL_ALIGN_POS: Dict[str, str] = {
        "left": "left",
        "right": "right",
        "center": "centerx",
    }
    __VERTICAL_ALIGN_POS: Dict[str, str] = {
        "top": "top",
        "bottom": "bottom",
        "center": "centery",
    }

    @initializer
    def __init__(
        self,
        master: Union[Scene, Window],
        text: str = "",
        callback: Optional[Callable[[], None]] = None,
        *,
        img: Optional[Surface] = None,
        compound: str = "left",
        distance_text_img: float = 5,
        font: Optional[_TextFont] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        state: str = "normal",
        width: Optional[float] = None,
        height: Optional[float] = None,
        x_add_size: float = 20,
        y_add_size: float = 20,
        show_bg: bool = True,
        bg: Color = GRAY_LIGHT,
        fg: Color = BLACK,
        outline: int = 2,
        outline_color: Color = BLACK,
        hover_bg: Optional[Color] = WHITE,
        hover_fg: Optional[Color] = None,
        hover_sound: Optional[Sound] = None,
        active_bg: Optional[Color] = GRAY,
        active_fg: Optional[Color] = None,
        click_sound: Optional[Sound] = None,
        disabled_bg: Color = GRAY_DARK,
        disabled_fg: Color = BLACK,
        disabled_sound: Optional[Sound] = None,
        disabled_hover_bg: Optional[Color] = None,
        disabled_hover_fg: Optional[Color] = None,
        disabled_active_bg: Optional[Color] = None,
        disabled_active_fg: Optional[Color] = None,
        hover_img: Optional[Surface] = None,
        active_img: Optional[Surface] = None,
        disabled_img: Optional[Surface] = None,
        disabled_hover_img: Optional[Surface] = None,
        disabled_active_img: Optional[Surface] = None,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
        text_align_x: str = "center",
        text_align_y: str = "center",
        text_offset: Tuple[float, float] = (0, 0),
        text_hover_offset: Tuple[float, float] = (0, 0),
        text_active_offset: Tuple[float, float] = (0, 0),
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: Optional[ThemeType] = None
    ) -> None:
        ThemedDrawable.__init__(self)
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
        self.__text: TextImage = TextImage(
            message=text,
            img=img,
            compound=compound,
            distance=distance_text_img,
            font=font,
            bold=bold,
            italic=italic,
            underline=underline,
            color=fg,
            wrap=wrap,
            justify=justify,
            shadow_x=shadow_x,
            shadow_y=shadow_y,
            shadow_color=shadow_color,
            theme=NoTheme,
        )
        self.callback = callback
        self.x_add_size = x_add_size
        self.y_add_size = y_add_size
        self.fixed_width = width
        self.fixed_height = height
        self.__shape: RectangleShape = RectangleShape(
            width=0,
            height=0,
            color=bg,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=NoTheme,
        )
        self.__shape.set_visibility(show_bg)
        self.__bg_dict: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {
                "normal": Color(bg),
                "hover": _copy_color(hover_bg),
                "active": _copy_color(active_bg),
            },
            Clickable.State.DISABLED: {
                "normal": Color(disabled_bg),
                "hover": _copy_color(disabled_hover_bg),
                "active": _copy_color(disabled_active_bg),
            },
        }
        self.__fg_dict: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {
                "normal": Color(fg),
                "hover": _copy_color(hover_fg),
                "active": _copy_color(active_fg),
            },
            Clickable.State.DISABLED: {
                "normal": Color(disabled_fg),
                "hover": _copy_color(disabled_hover_fg),
                "active": _copy_color(disabled_active_fg),
            },
        }
        self.__img_dict: Dict[Clickable.State, _ImageDict] = {
            Clickable.State.NORMAL: {
                "normal": _copy_img(img),
                "hover": _copy_img(hover_img),
                "active": _copy_img(active_img),
            },
            Clickable.State.DISABLED: {
                "normal": _copy_img(disabled_img),
                "hover": _copy_img(disabled_hover_img),
                "active": _copy_img(disabled_active_img),
            },
        }
        self.__text_align_x: Button.HorizontalAlign
        self.__text_align_y: Button.VerticalAlign
        self.text_align_x = text_align_x
        self.text_align_y = text_align_y
        self.text_offset = text_offset
        self.text_hover_offset = text_hover_offset
        self.text_active_offset = text_active_offset

    def copy(self) -> Button:
        b: Button = Button(
            master=self.master,
            text=self.__text.message,
            img=self.__img_dict[Clickable.State.NORMAL]["normal"],
            compound=self.__text.compound,
            distance_text_img=self.__text.distance,
            font=self.__text.font,
            wrap=self.__text.wrap,
            justify=self.__text.justify,
            shadow_x=self.__text.shadow_x,
            shadow_y=self.__text.shadow_y,
            shadow_color=self.__text.shadow_color,
            callback=self.callback,
            state=self.state,
            width=self.fixed_width,
            height=self.fixed_height,
            x_add_size=self.x_add_size,
            y_add_size=self.y_add_size,
            show_bg=self.__shape.is_shown(),
            bg=self.__bg_dict[Clickable.State.NORMAL]["normal"],
            fg=self.__fg_dict[Clickable.State.NORMAL]["normal"],
            outline=self.__shape.outline,
            outline_color=self.__shape.outline_color,
            hover_bg=self.__bg_dict[Clickable.State.NORMAL]["hover"],
            hover_fg=self.__fg_dict[Clickable.State.NORMAL]["hover"],
            hover_sound=self.hover_sound,
            active_bg=self.__bg_dict[Clickable.State.NORMAL]["active"],
            active_fg=self.__fg_dict[Clickable.State.NORMAL]["active"],
            click_sound=self.click_sound,
            disabled_bg=self.__bg_dict[Clickable.State.DISABLED]["normal"],
            disabled_fg=self.__fg_dict[Clickable.State.DISABLED]["normal"],
            disabled_sound=self.disabled_sound,
            disabled_hover_bg=self.__bg_dict[Clickable.State.DISABLED]["hover"],
            disabled_hover_fg=self.__fg_dict[Clickable.State.DISABLED]["hover"],
            disabled_active_bg=self.__bg_dict[Clickable.State.DISABLED]["active"],
            disabled_active_fg=self.__fg_dict[Clickable.State.DISABLED]["active"],
            hover_img=self.__img_dict[Clickable.State.NORMAL]["hover"],
            active_img=self.__img_dict[Clickable.State.NORMAL]["active"],
            disabled_img=self.__img_dict[Clickable.State.DISABLED]["normal"],
            disabled_hover_img=self.__img_dict[Clickable.State.DISABLED]["hover"],
            disabled_active_img=self.__img_dict[Clickable.State.DISABLED]["active"],
            hover_cursor=self.hover_cursor,
            disabled_cursor=self.disabled_cursor,
            text_align_x=self.__text_align_x,
            text_align_y=self.__text_align_y,
            text_offset=self.text_offset,
            text_hover_offset=self.text_hover_offset,
            text_active_offset=self.text_active_offset,
            border_radius=self.__shape.border_radius,
            border_top_left_radius=self.__shape.border_top_left_radius,
            border_top_right_radius=self.__shape.border_top_right_radius,
            border_bottom_left_radius=self.__shape.border_bottom_left_radius,
            border_bottom_right_radius=self.__shape.border_bottom_right_radius,
            theme=NoTheme,
        )
        b.img_set_scale(self.__text.get_img_scale())
        return b

    def draw_onto(self, surface: Surface) -> None:
        angle: float = self.angle
        scale: float = self.scale

        def compute_offset(offset: Tuple[float, float]) -> Tuple[float, float]:
            return offset[0] * scale, offset[1] * scale

        text_align_x: str = Button.__HORIZONTAL_ALIGN_POS[self.__text_align_x]
        text_align_y: str = Button.__VERTICAL_ALIGN_POS[self.__text_align_y]

        shape: RectangleShape = self.__shape
        text: TextImage = self.__text

        shape.center = center = self.center
        text.set_position(
            **{
                text_align_x: getattr(shape, text_align_x),
                text_align_y: getattr(shape, text_align_y),
            }
        )
        text.translate(compute_offset(self.text_offset))
        if self.state != Clickable.State.DISABLED:
            if self.active:
                text.translate(compute_offset(self.text_active_offset))
            elif self.hover:
                text.translate(compute_offset(self.text_hover_offset))
        text.rotate_around_point(angle, center)
        shape.draw_onto(surface)
        text.draw_onto(surface)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> Tuple[float, float]:
        return self.__shape.get_size()

    def __invoke__(self) -> None:
        callback: Optional[Callable[[], None]] = self.callback
        if callable(callback):
            callback()

    def text_set_font(
        self,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> None:
        self.__text.set_font(font, bold, italic, underline)
        self.__update_shape_size()

    def text_set_custom_line_font(self, index: int, font: Font) -> None:
        self.__text.set_custom_line_font(index, font)
        self.__update_shape_size()

    def text_remove_custom_line_font(self, index: int) -> None:
        self.__text.remove_custom_line_font(index)
        self.__update_shape_size()

    def img_rotate(self, angle_offset: float) -> None:
        self.__text.img_rotate(angle_offset)
        self.__update_shape_size()

    def img_set_rotation(self, angle: float) -> None:
        self.__text.img_set_rotation(angle)
        self.__update_shape_size()

    def img_set_scale(self, scale: float) -> None:
        self.__text.img_set_scale(scale)
        self.__update_shape_size()

    def img_scale_to_width(self, width: float) -> None:
        self.__text.img_scale_to_width(width)
        self.__update_shape_size()

    def img_scale_to_height(self, height: float) -> None:
        self.__text.img_scale_to_height(height)
        self.__update_shape_size()

    def img_scale_to_size(self, size: Tuple[float, float]) -> None:
        self.__text.img_scale_to_size(size)
        self.__update_shape_size()

    def img_set_min_width(self, width: float) -> None:
        self.__text.img_set_min_width(width)
        self.__update_shape_size()

    def img_set_max_width(self, width: float) -> None:
        self.__text.set_max_width(width)
        self.__update_shape_size()

    def img_set_min_height(self, height: float) -> None:
        self.__text.set_min_height(height)
        self.__update_shape_size()

    def img_set_max_height(self, height: float) -> None:
        self.__text.img_set_max_height(height)
        self.__update_shape_size()

    def img_set_min_size(self, size: Tuple[float, float]) -> None:
        self.__text.img_set_min_size(size)
        self.__update_shape_size()

    def img_set_max_size(self, size: Tuple[float, float]) -> None:
        self.__text.img_set_max_size(size)
        self.__update_shape_size()

    @overload
    def show_background(self) -> bool:
        ...

    @overload
    def show_background(self, status: bool) -> None:
        ...

    def show_background(self, status: Optional[bool] = None) -> Optional[bool]:
        if status is None:
            return self.__shape.is_shown()
        self.__shape.set_visibility(truth(status))
        return None

    def _apply_rotation_scale(self) -> None:
        self.__shape.scale = self.__text.scale = self.scale
        self.__shape.angle = self.__text.angle = self.angle
        self.__update_shape_size()

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        rect: Rect = Rect((0, 0), self.get_area(apply_rotation=False))
        center: Tuple[float, float] = self.center
        rect.center = int(center[0]), int(center[1])
        pivot: Vector2 = Vector2(rect.center)  # type: ignore[arg-type]
        mouse: Vector2 = Vector2(mouse_pos)  # type: ignore[arg-type]
        mouse = pivot + (mouse - pivot).rotate(self.angle)
        return truth(rect.collidepoint(mouse.x, mouse.y))

    def _on_hover(self) -> None:
        self.__set_state("hover")

    def _on_leave(self) -> None:
        self.__set_state("normal")

    def _on_active_set(self) -> None:
        self.__set_state("active")

    def __set_state(self, button_state: Literal["normal", "hover", "active"]) -> None:
        clickable_state: Clickable.State = Clickable.State(self.state)
        bg_color: Optional[Color] = self.__bg_dict[clickable_state][button_state]
        if bg_color is None:
            bg_color = self.__bg_dict[clickable_state]["normal"]
        fg_color: Optional[Color] = self.__fg_dict[clickable_state][button_state]
        if fg_color is None:
            fg_color = self.__fg_dict[clickable_state]["normal"]
        img: Optional[Surface] = self.__img_dict[clickable_state][button_state]
        if img is None:
            img = self.__img_dict[clickable_state]["normal"]
        self.__shape.config(color=bg_color)
        self.__text.config(color=fg_color, img=img)
        self.__update_shape_size()

    def __update_state(self) -> None:
        if self.active:
            self.__set_state("active")
        elif self.hover:
            self.__set_state("hover")
        else:
            self.__set_state("normal")

    def __update_shape_size(self) -> None:
        text_width, text_height = self.__text.get_local_size()
        x_add_size: float = self.x_add_size * self.scale
        y_add_size: float = self.y_add_size * self.scale
        fixed_width: Optional[float] = self.fixed_width
        fixed_height: Optional[float] = self.fixed_height

        new_size: Tuple[float, float] = (
            text_width + x_add_size if fixed_width is None else fixed_width,
            text_height + y_add_size if fixed_height is None else fixed_height,
        )

        if self.config.has_initialization_context():
            self.__shape.local_size = new_size
        else:
            center = self.center
            self.__shape.local_size = new_size
            self.center = center

    config: Configuration = Configuration(
        "text",
        "text_font",
        "text_justify",
        "text_wrap",
        "text_shadow",
        "text_shadow_x",
        "text_shadow_y",
        "text_shadow_color",
        "img",
        "compound",
        "distance_text_img",
        "fixed_width",
        "fixed_height",
        "x_add_size",
        "y_add_size",
        "background",
        "foreground",
        "outline",
        "outline_color",
        "hover_background",
        "hover_foreground",
        "active_background",
        "active_foreground",
        "disabled_background",
        "disabled_foreground",
        "disabled_hover_background",
        "disabled_hover_foreground",
        "disabled_active_background",
        "disabled_active_foreground",
        "hover_img",
        "active_img",
        "disabled_img",
        "disabled_hover_img",
        "disabled_active_img",
        "text_align_x",
        "text_align_y",
        "text_offset",
        "text_hover_offset",
        "text_active_offset",
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
    )

    config.set_alias("background", "bg")
    config.set_alias("foreground", "fg")
    config.set_alias("hover_background", "hover_bg")
    config.set_alias("hover_foreground", "hover_fg")
    config.set_alias("active_background", "active_bg")
    config.set_alias("active_foreground", "active_fg")
    config.set_alias("disabled_background", "disabled_bg")
    config.set_alias("disabled_foreground", "disabled_fg")
    config.set_alias("disabled_hover_background", "disabled_hover_bg")
    config.set_alias("disabled_hover_foreground", "disabled_hover_fg")
    config.set_alias("disabled_active_background", "disabled_active_bg")
    config.set_alias("disabled_active_foreground", "disabled_active_fg")

    config.register_copy_func(Color, _copy_color)
    config.register_copy_func(Surface, _copy_img, allow_subclass=True)

    text: ConfigAttribute[str] = ConfigAttribute()
    text_font: ConfigAttribute[Font] = ConfigAttribute()
    text_justify: ConfigAttribute[str] = ConfigAttribute()
    text_wrap: ConfigAttribute[int] = ConfigAttribute()
    text_shadow: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    text_shadow_x: ConfigAttribute[float] = ConfigAttribute()
    text_shadow_y: ConfigAttribute[float] = ConfigAttribute()
    text_shadow_color: ConfigAttribute[Color] = ConfigAttribute()
    img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    compound: ConfigAttribute[str] = ConfigAttribute()
    distance_text_img: ConfigAttribute[float] = ConfigAttribute()
    fixed_width: ConfigAttribute[Optional[float]] = ConfigAttribute()
    fixed_height: ConfigAttribute[Optional[float]] = ConfigAttribute()
    x_add_size: ConfigAttribute[float] = ConfigAttribute()
    y_add_size: ConfigAttribute[float] = ConfigAttribute()
    background: ConfigAttribute[Color] = ConfigAttribute()
    foreground: ConfigAttribute[Color] = ConfigAttribute()
    bg: ConfigAttribute[Color] = ConfigAttribute()
    fg: ConfigAttribute[Color] = ConfigAttribute()
    outline: ConfigAttribute[int] = ConfigAttribute()
    outline_color: ConfigAttribute[Color] = ConfigAttribute()
    hover_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    hover_foreground: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    hover_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    hover_fg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    active_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    active_foreground: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    active_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    active_fg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_background: ConfigAttribute[Color] = ConfigAttribute()
    disabled_foreground: ConfigAttribute[Color] = ConfigAttribute()
    disabled_bg: ConfigAttribute[Color] = ConfigAttribute()
    disabled_fg: ConfigAttribute[Color] = ConfigAttribute()
    disabled_hover_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_hover_foreground: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_hover_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_hover_fg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_active_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_active_foreground: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_active_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_active_fg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    hover_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    active_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    disabled_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    disabled_hover_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    disabled_active_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    text_align_x: ConfigAttribute[str] = ConfigAttribute()
    text_align_y: ConfigAttribute[str] = ConfigAttribute()
    text_offset: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    text_hover_offset: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    text_active_offset: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    border_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_right_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_right_radius: ConfigAttribute[int] = ConfigAttribute()

    __TEXT_OPTION: Dict[str, str] = {
        "text": "message",
        "text_font": "font",
        "text_justify": "justify",
        "text_wrap": "wrap",
        "text_shadow": "shadow",
        "text_shadow_x": "shadow_x",
        "text_shadow_y": "shadow_y",
        "text_shadow_color": "shadow_color",
        "compound": "compound",
        "distance_text_img": "distance",
    }

    @config.getter("text")
    @config.getter("text_font")
    @config.getter("text_justify")
    @config.getter("text_wrap")
    @config.getter("text_shadow")
    @config.getter("text_shadow_x")
    @config.getter("text_shadow_y")
    @config.getter("text_shadow_color")
    @config.getter("compound")
    @config.getter("distance_text_img")
    def __get_text_option(self, option: str) -> Any:
        return self.__text.config.get(Button.__TEXT_OPTION[option])

    @config.setter("text")
    @config.setter("text_font")
    @config.setter("text_justify")
    @config.setter("text_wrap")
    @config.setter("text_shadow")
    @config.setter("text_shadow_x")
    @config.setter("text_shadow_y")
    @config.setter("text_shadow_color")
    @config.setter("compound")
    @config.setter("distance_text_img")
    def __set_text_option(self, option: str, value: Any) -> None:
        return self.__text.config.set(Button.__TEXT_OPTION[option], value)

    config.updater("text", __update_shape_size)
    config.updater("text_font", __update_shape_size)
    config.updater("text_justify", __update_shape_size)
    config.updater("text_wrap", __update_shape_size)
    config.updater("text_shadow", __update_shape_size)
    config.updater("text_shadow_x", __update_shape_size)
    config.updater("text_shadow_y", __update_shape_size)
    config.updater("text_shadow_color", __update_shape_size)
    config.updater("compound", __update_shape_size)
    config.updater("distance_text_img", __update_shape_size)

    @config.validator("fixed_width")
    @config.validator("fixed_height")
    @staticmethod
    def __fixed_size_validator(size: Optional[float]) -> Optional[float]:
        if size is None:
            return None
        return max(float(size), 0)

    config.updater("fixed_width", __update_shape_size)
    config.updater("fixed_height", __update_shape_size)

    config.validator("x_add_size", no_object(valid_float(min_value=0)))
    config.validator("y_add_size", no_object(valid_float(min_value=0)))
    config.updater("x_add_size", __update_shape_size)
    config.updater("y_add_size", __update_shape_size)

    __STATE: Dict[str, Tuple[Clickable.State, Literal["normal", "hover", "active"]]] = {
        "background": (Clickable.State.NORMAL, "normal"),
        "hover_background": (Clickable.State.NORMAL, "hover"),
        "active_background": (Clickable.State.NORMAL, "active"),
        "disabled_background": (Clickable.State.DISABLED, "normal"),
        "disabled_hover_background": (Clickable.State.DISABLED, "hover"),
        "disabled_active_background": (Clickable.State.DISABLED, "active"),
        "foreground": (Clickable.State.NORMAL, "normal"),
        "hover_foreground": (Clickable.State.NORMAL, "hover"),
        "active_foreground": (Clickable.State.NORMAL, "active"),
        "disabled_foreground": (Clickable.State.DISABLED, "normal"),
        "disabled_hover_foreground": (Clickable.State.DISABLED, "hover"),
        "disabled_active_foreground": (Clickable.State.DISABLED, "active"),
        "img": (Clickable.State.NORMAL, "normal"),
        "hover_img": (Clickable.State.NORMAL, "hover"),
        "active_img": (Clickable.State.NORMAL, "active"),
        "disabled_img": (Clickable.State.DISABLED, "normal"),
        "disabled_hover_img": (Clickable.State.DISABLED, "hover"),
        "disabled_active_img": (Clickable.State.DISABLED, "active"),
    }

    config.set_autocopy("background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_background", copy_on_get=True, copy_on_set=True)

    @config.getter("background")
    @config.getter("hover_background")
    @config.getter("active_background")
    @config.getter("disabled_background")
    @config.getter("disabled_hover_background")
    @config.getter("disabled_active_background")
    def __get_background(self, option: str) -> Optional[Color]:
        clickable_state, button_state = Button.__STATE[option]
        return self.__bg_dict[clickable_state][button_state]

    @config.setter("background")
    @config.setter("hover_background")
    @config.setter("active_background")
    @config.setter("disabled_background")
    @config.setter("disabled_hover_background")
    @config.setter("disabled_active_background")
    def __set_background(self, option: str, color: Optional[Color]) -> None:
        clickable_state, button_state = Button.__STATE[option]
        self.__bg_dict[clickable_state][button_state] = color

    config.validator("background", Color)
    config.validator("hover_background", (Color, type(None)))
    config.validator("active_background", (Color, type(None)))
    config.validator("disabled_background", Color)
    config.validator("disabled_hover_background", (Color, type(None)))
    config.validator("disabled_active_background", (Color, type(None)))

    config.updater("background", __update_state)
    config.updater("hover_background", __update_state)
    config.updater("active_background", __update_state)
    config.updater("disabled_background", __update_state)
    config.updater("disabled_hover_background", __update_state)
    config.updater("disabled_active_background", __update_state)

    config.set_autocopy("foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_foreground", copy_on_get=True, copy_on_set=True)

    @config.getter("foreground")
    @config.getter("hover_foreground")
    @config.getter("active_foreground")
    @config.getter("disabled_foreground")
    @config.getter("disabled_hover_foreground")
    @config.getter("disabled_active_foreground")
    def __get_foreground(self, option: str) -> Optional[Color]:
        clickable_state, button_state = Button.__STATE[option]
        return self.__fg_dict[clickable_state][button_state]

    @config.setter("foreground")
    @config.setter("hover_foreground")
    @config.setter("active_foreground")
    @config.setter("disabled_foreground")
    @config.setter("disabled_hover_foreground")
    @config.setter("disabled_active_foreground")
    def __set_foreground(self, option: str, color: Optional[Color]) -> None:
        clickable_state, button_state = Button.__STATE[option]
        self.__fg_dict[clickable_state][button_state] = color

    config.validator("foreground", Color)
    config.validator("hover_foreground", (Color, type(None)))
    config.validator("active_foreground", (Color, type(None)))
    config.validator("disabled_foreground", Color)
    config.validator("disabled_hover_foreground", (Color, type(None)))
    config.validator("disabled_active_foreground", (Color, type(None)))

    config.updater("foreground", __update_state)
    config.updater("hover_foreground", __update_state)
    config.updater("active_foreground", __update_state)
    config.updater("disabled_foreground", __update_state)
    config.updater("disabled_hover_foreground", __update_state)
    config.updater("disabled_active_foreground", __update_state)

    config.set_autocopy("img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_img", copy_on_get=True, copy_on_set=True)

    @config.getter("img")
    @config.getter("hover_img")
    @config.getter("active_img")
    @config.getter("disabled_img")
    @config.getter("disabled_hover_img")
    @config.getter("disabled_active_img")
    def __get_img(self, option: str) -> Optional[Surface]:
        clickable_state, button_state = Button.__STATE[option]
        return self.__img_dict[clickable_state][button_state]

    @config.setter("img")
    @config.setter("hover_img")
    @config.setter("active_img")
    @config.setter("disabled_img")
    @config.setter("disabled_hover_img")
    @config.setter("disabled_active_img")
    def __set_img(self, option: str, img: Optional[Surface]) -> None:
        clickable_state, button_state = Button.__STATE[option]
        self.__img_dict[clickable_state][button_state] = img

    config.validator("img", (Surface, type(None)))
    config.validator("hover_img", (Surface, type(None)))
    config.validator("active_img", (Surface, type(None)))
    config.validator("disabled_img", (Surface, type(None)))
    config.validator("disabled_hover_img", (Surface, type(None)))
    config.validator("disabled_active_img", (Surface, type(None)))

    config.updater("img", __update_state)
    config.updater("hover_img", __update_state)
    config.updater("active_img", __update_state)
    config.updater("disabled_img", __update_state)
    config.updater("disabled_hover_img", __update_state)
    config.updater("disabled_active_img", __update_state)

    config.enum("text_align_x", HorizontalAlign, return_value=True)
    config.enum("text_align_y", VerticalAlign, return_value=True)

    @config.validator("text_offset")
    @config.validator("text_hover_offset")
    @config.validator("text_active_offset")
    @staticmethod
    def __text_offset_validator(offset: Tuple[float, float]) -> Tuple[float, float]:
        return (float(offset[0]), float(offset[1]))

    @config.getter("outline")
    @config.getter("outline_color")
    @config.getter("border_radius")
    @config.getter("border_top_left_radius")
    @config.getter("border_top_right_radius")
    @config.getter("border_bottom_left_radius")
    @config.getter("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

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
    def callback(self) -> Optional[Callable[[], None]]:
        self.__callback: Optional[Callable[[], None]]
        return self.__callback

    @callback.setter
    def callback(self, callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None


@Button.register
class ImageButton(ThemedDrawable, Clickable):
    @initializer
    def __init__(
        self,
        master: Union[Scene, Window],
        img: Surface,
        callback: Optional[Callable[[], None]] = None,
        *,
        hover_img: Optional[Surface] = None,
        active_img: Optional[Surface] = None,
        disabled_img: Optional[Surface] = None,
        disabled_hover_img: Optional[Surface] = None,
        disabled_active_img: Optional[Surface] = None,
        state: str = "normal",
        x_add_size: float = 20,
        y_add_size: float = 20,
        bg: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        hover_bg: Optional[Color] = None,
        active_bg: Optional[Color] = None,
        disabled_bg: Optional[Color] = None,
        disabled_hover_bg: Optional[Color] = None,
        disabled_active_bg: Optional[Color] = None,
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        hover_cursor: Optional[Cursor] = None,
        disabled_cursor: Optional[Cursor] = None,
        hover_offset: Tuple[float, float] = (0, 0),
        active_offset: Tuple[float, float] = (0, 3),
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: Optional[ThemeType] = None
    ) -> None:
        ThemedDrawable.__init__(self)
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
        self.__image: Image = Image(img)
        self.callback = callback
        self.x_add_size = x_add_size
        self.y_add_size = y_add_size
        self.__shape: RectangleShape = RectangleShape(
            width=0,
            height=0,
            color=bg,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=NoTheme,
        )
        self.__bg_dict: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {
                "normal": Color(bg),
                "hover": _copy_color(hover_bg),
                "active": _copy_color(active_bg),
            },
            Clickable.State.DISABLED: {
                "normal": _copy_color(disabled_bg, default=bg),
                "hover": _copy_color(disabled_hover_bg),
                "active": _copy_color(disabled_active_bg),
            },
        }
        self.__img_dict: Dict[Clickable.State, _ImageButtonDict] = {
            Clickable.State.NORMAL: {
                "normal": img.copy(),
                "hover": _copy_img(hover_img),
                "active": _copy_img(active_img),
            },
            Clickable.State.DISABLED: {
                "normal": _copy_img(disabled_img, default=img),
                "hover": _copy_img(disabled_hover_img),
                "active": _copy_img(disabled_active_img),
            },
        }
        self.hover_offset = hover_offset
        self.active_offset = active_offset

    def copy(self) -> ImageButton:
        return ImageButton(
            master=self.master,
            img=self.__img_dict[Clickable.State.NORMAL]["normal"],
            callback=self.callback,
            state=self.state,
            x_add_size=self.x_add_size,
            y_add_size=self.y_add_size,
            bg=self.__bg_dict[Clickable.State.NORMAL]["normal"],
            outline=self.__shape.outline,
            outline_color=self.__shape.outline_color,
            hover_bg=self.__bg_dict[Clickable.State.NORMAL]["hover"],
            active_bg=self.__bg_dict[Clickable.State.NORMAL]["active"],
            disabled_bg=self.__bg_dict[Clickable.State.DISABLED]["normal"],
            disabled_hover_bg=self.__bg_dict[Clickable.State.DISABLED]["hover"],
            disabled_active_bg=self.__bg_dict[Clickable.State.DISABLED]["active"],
            hover_sound=self.hover_sound,
            click_sound=self.click_sound,
            disabled_sound=self.disabled_sound,
            hover_img=self.__img_dict[Clickable.State.NORMAL]["hover"],
            active_img=self.__img_dict[Clickable.State.NORMAL]["active"],
            disabled_img=self.__img_dict[Clickable.State.DISABLED]["normal"],
            disabled_hover_img=self.__img_dict[Clickable.State.DISABLED]["hover"],
            disabled_active_img=self.__img_dict[Clickable.State.DISABLED]["active"],
            hover_cursor=self.hover_cursor,
            disabled_cursor=self.disabled_cursor,
            hover_offset=self.hover_offset,
            active_offset=self.active_offset,
            border_radius=self.__shape.border_radius,
            border_top_left_radius=self.__shape.border_top_left_radius,
            border_top_right_radius=self.__shape.border_top_right_radius,
            border_bottom_left_radius=self.__shape.border_bottom_left_radius,
            border_bottom_right_radius=self.__shape.border_bottom_right_radius,
            theme=NoTheme,
        )

    def draw_onto(self, surface: Surface) -> None:
        scale: float = self.scale

        def compute_offset(offset: Tuple[float, float]) -> Tuple[float, float]:
            return offset[0] * scale, offset[1] * scale

        shape: RectangleShape = self.__shape
        image: Image = self.__image

        shape.center = image.center = self.center
        if self.active:
            image.translate(compute_offset(self.active_offset))
        elif self.hover:
            image.translate(compute_offset(self.hover_offset))

        shape.draw_onto(surface)
        image.draw_onto(surface)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> Tuple[float, float]:
        return self.__shape.get_size()

    def __invoke__(self) -> None:
        callback: Optional[Callable[[], None]] = self.callback
        if callable(callback):
            callback()

    def _apply_rotation_scale(self) -> None:
        if self.angle != 0:
            raise NotImplementedError
        self.__shape.scale = self.__image.scale = self.scale
        self.__update_shape_size()

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        return truth(self.rect.collidepoint(mouse_pos))

    def _on_hover(self) -> None:
        self.__set_state("hover")

    def _on_leave(self) -> None:
        self.__set_state("normal")

    def _on_active_set(self) -> None:
        self.__set_state("active")

    def __set_state(self, button_state: Literal["normal", "hover", "active"]) -> None:
        clickable_state: Clickable.State = Clickable.State(self.state)
        bg_color: Optional[Color] = self.__bg_dict[clickable_state][button_state]
        if bg_color is None:
            bg_color = self.__bg_dict[clickable_state]["normal"]
        img: Optional[Surface] = self.__img_dict[clickable_state][button_state]
        if img is None:
            img = self.__img_dict[clickable_state]["normal"]
        self.__shape.color = bg_color
        self.__image.set(img)
        self.__update_shape_size()

    def __update_state(self) -> None:
        if self.active:
            self.__set_state("active")
        elif self.hover:
            self.__set_state("hover")
        else:
            self.__set_state("normal")

    def __update_shape_size(self) -> None:
        img_width, img_height = self.__image.get_local_size()
        scale: float = self.scale
        x_add_size: float = self.x_add_size * scale
        y_add_size: float = self.y_add_size * scale
        new_size: Tuple[float, float] = (img_width + x_add_size, img_height + y_add_size)
        if self.config.has_initialization_context():
            self.__shape.local_size = new_size
        else:
            center = self.center
            self.__shape.local_size = new_size
            self.center = center

    config: Configuration = Configuration(
        "img",
        "x_add_size",
        "y_add_size",
        "background",
        "outline",
        "outline_color",
        "hover_background",
        "active_background",
        "disabled_background",
        "disabled_hover_background",
        "disabled_active_background",
        "hover_img",
        "active_img",
        "disabled_img",
        "disabled_hover_img",
        "disabled_active_img",
        "hover_offset",
        "active_offset",
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
    )

    config.set_alias("background", "bg")
    config.set_alias("hover_background", "hover_bg")
    config.set_alias("active_background", "active_bg")
    config.set_alias("disabled_background", "disabled_bg")
    config.set_alias("disabled_hover_background", "disabled_hover_bg")
    config.set_alias("disabled_active_background", "disabled_active_bg")

    config.register_copy_func(Color, _copy_color)
    config.register_copy_func(Surface, _copy_img, allow_subclass=True)

    img: ConfigAttribute[Surface] = ConfigAttribute()
    x_add_size: ConfigAttribute[float] = ConfigAttribute()
    y_add_size: ConfigAttribute[float] = ConfigAttribute()
    background: ConfigAttribute[Color] = ConfigAttribute()
    bg: ConfigAttribute[Color] = ConfigAttribute()
    outline: ConfigAttribute[int] = ConfigAttribute()
    outline_color: ConfigAttribute[Color] = ConfigAttribute()
    hover_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    hover_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    active_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    active_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_background: ConfigAttribute[Color] = ConfigAttribute()
    disabled_bg: ConfigAttribute[Color] = ConfigAttribute()
    disabled_hover_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_hover_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_active_background: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    disabled_active_bg: ConfigAttribute[Optional[Color]] = ConfigAttribute()
    hover_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    active_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    disabled_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    disabled_hover_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    disabled_active_img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    hover_offset: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    active_offset: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    border_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_top_right_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_left_radius: ConfigAttribute[int] = ConfigAttribute()
    border_bottom_right_radius: ConfigAttribute[int] = ConfigAttribute()

    @config.validator("hover_offset")
    @config.validator("active_offset")
    @staticmethod
    def __img_offset_validator(offset: Tuple[float, float]) -> Tuple[float, float]:
        return (float(offset[0]), float(offset[1]))

    config.validator("x_add_size", no_object(valid_float(min_value=0)))
    config.validator("y_add_size", no_object(valid_float(min_value=0)))
    config.updater("x_add_size", __update_shape_size)
    config.updater("y_add_size", __update_shape_size)

    __STATE: Dict[str, Tuple[Clickable.State, Literal["normal", "hover", "active"]]] = {
        "background": (Clickable.State.NORMAL, "normal"),
        "hover_background": (Clickable.State.NORMAL, "hover"),
        "active_background": (Clickable.State.NORMAL, "active"),
        "disabled_background": (Clickable.State.DISABLED, "normal"),
        "disabled_hover_background": (Clickable.State.DISABLED, "hover"),
        "disabled_active_background": (Clickable.State.DISABLED, "active"),
        "img": (Clickable.State.NORMAL, "normal"),
        "hover_img": (Clickable.State.NORMAL, "hover"),
        "active_img": (Clickable.State.NORMAL, "active"),
        "disabled_img": (Clickable.State.DISABLED, "normal"),
        "disabled_hover_img": (Clickable.State.DISABLED, "hover"),
        "disabled_active_img": (Clickable.State.DISABLED, "active"),
    }

    config.set_autocopy("background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_background", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_background", copy_on_get=True, copy_on_set=True)

    @config.getter("background")
    @config.getter("hover_background")
    @config.getter("active_background")
    @config.getter("disabled_background")
    @config.getter("disabled_hover_background")
    @config.getter("disabled_active_background")
    def __get_background(self, option: str) -> Optional[Color]:
        clickable_state, button_state = ImageButton.__STATE[option]
        return self.__bg_dict[clickable_state][button_state]

    @config.setter("background")
    @config.setter("hover_background")
    @config.setter("active_background")
    @config.setter("disabled_background")
    @config.setter("disabled_hover_background")
    @config.setter("disabled_active_background")
    def __set_background(self, option: str, color: Optional[Color]) -> None:
        clickable_state, button_state = ImageButton.__STATE[option]
        self.__bg_dict[clickable_state][button_state] = color

    config.validator("background", Color)
    config.validator("hover_background", (Color, type(None)))
    config.validator("active_background", (Color, type(None)))
    config.validator("disabled_background", Color)
    config.validator("disabled_hover_background", (Color, type(None)))
    config.validator("disabled_active_background", (Color, type(None)))

    config.updater("background", __update_state)
    config.updater("hover_background", __update_state)
    config.updater("active_background", __update_state)
    config.updater("disabled_background", __update_state)
    config.updater("disabled_hover_background", __update_state)
    config.updater("disabled_active_background", __update_state)

    config.set_autocopy("img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_img", copy_on_get=True, copy_on_set=True)

    @config.getter("img")
    @config.getter("hover_img")
    @config.getter("active_img")
    @config.getter("disabled_img")
    @config.getter("disabled_hover_img")
    @config.getter("disabled_active_img")
    def __get_img(self, option: str) -> Optional[Surface]:
        clickable_state, button_state = ImageButton.__STATE[option]
        return self.__img_dict[clickable_state][button_state]

    @config.setter("img")
    @config.setter("hover_img")
    @config.setter("active_img")
    @config.setter("disabled_img")
    @config.setter("disabled_hover_img")
    @config.setter("disabled_active_img")
    def __set_img(self, option: str, img: Optional[Surface]) -> None:
        clickable_state, button_state = ImageButton.__STATE[option]
        self.__img_dict[clickable_state][button_state] = img

    config.validator("img", Surface)
    config.validator("hover_img", (Surface, type(None)))
    config.validator("active_img", (Surface, type(None)))
    config.validator("disabled_img", (Surface, type(None)))
    config.validator("disabled_hover_img", (Surface, type(None)))
    config.validator("disabled_active_img", (Surface, type(None)))

    config.updater("img", __update_state)
    config.updater("hover_img", __update_state)
    config.updater("active_img", __update_state)
    config.updater("disabled_img", __update_state)
    config.updater("disabled_hover_img", __update_state)
    config.updater("disabled_active_img", __update_state)

    @config.getter("outline")
    @config.getter("outline_color")
    @config.getter("border_radius")
    @config.getter("border_top_left_radius")
    @config.getter("border_top_right_radius")
    @config.getter("border_bottom_left_radius")
    @config.getter("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

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
    def callback(self) -> Optional[Callable[[], None]]:
        self.__callback: Optional[Callable[[], None]]
        return self.__callback

    @callback.setter
    def callback(self, callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None
