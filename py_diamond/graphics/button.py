# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Button module"""

from __future__ import annotations

__all__ = ["Button", "ImageButton", "MetaButton"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import Enum, unique
from operator import truth
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Dict, Final, Literal, Optional, Tuple, Type, TypedDict, Union, overload

from ..math import Vector2
from ..system.configuration import Configuration, OptionAttribute, initializer
from ..system.utils import valid_float, valid_optional_float
from ..window.clickable import Clickable
from .color import BLACK, GRAY, GRAY_DARK, GRAY_LIGHT, TRANSPARENT, WHITE, Color
from .drawable import MetaTDrawable, TDrawable
from .image import Image
from .rect import Rect
from .shape import RectangleShape
from .surface import Surface
from .text import TextImage
from .theme import MetaThemedObject, NoTheme, ThemeType

if TYPE_CHECKING:
    from ..audio.sound import Sound
    from ..window.cursor import Cursor
    from ..window.display import Window
    from ..window.scene import Scene
    from .font import Font
    from .renderer import Renderer

    _TextFont = Union[Font, Tuple[Optional[str], int]]


class MetaButton(MetaTDrawable, MetaThemedObject):
    pass


@TextImage.register_themed_subclass
@RectangleShape.register_themed_subclass
class Button(TDrawable, Clickable, metaclass=MetaButton):
    Justify: Type[TextImage.Justify] = TextImage.Justify
    Compound: Type[TextImage.Compound] = TextImage.Compound

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

    __HORIZONTAL_ALIGN_POS: ClassVar[Dict[str, str]] = {
        "left": "left",
        "right": "right",
        "center": "centerx",
    }
    __VERTICAL_ALIGN_POS: ClassVar[Dict[str, str]] = {
        "top": "top",
        "bottom": "bottom",
        "center": "centery",
    }

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

    text: OptionAttribute[str] = OptionAttribute()
    text_font: OptionAttribute[Font] = OptionAttribute()
    text_justify: OptionAttribute[str] = OptionAttribute()
    text_wrap: OptionAttribute[int] = OptionAttribute()
    text_shadow: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    text_shadow_x: OptionAttribute[float] = OptionAttribute()
    text_shadow_y: OptionAttribute[float] = OptionAttribute()
    text_shadow_color: OptionAttribute[Color] = OptionAttribute()
    img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    compound: OptionAttribute[str] = OptionAttribute()
    distance_text_img: OptionAttribute[float] = OptionAttribute()
    fixed_width: OptionAttribute[Optional[float]] = OptionAttribute()
    fixed_height: OptionAttribute[Optional[float]] = OptionAttribute()
    x_add_size: OptionAttribute[float] = OptionAttribute()
    y_add_size: OptionAttribute[float] = OptionAttribute()
    background: OptionAttribute[Color] = OptionAttribute()
    foreground: OptionAttribute[Color] = OptionAttribute()
    bg: OptionAttribute[Color] = OptionAttribute()
    fg: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    hover_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    hover_foreground: OptionAttribute[Optional[Color]] = OptionAttribute()
    hover_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    hover_fg: OptionAttribute[Optional[Color]] = OptionAttribute()
    active_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    active_foreground: OptionAttribute[Optional[Color]] = OptionAttribute()
    active_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    active_fg: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_background: OptionAttribute[Color] = OptionAttribute()
    disabled_foreground: OptionAttribute[Color] = OptionAttribute()
    disabled_bg: OptionAttribute[Color] = OptionAttribute()
    disabled_fg: OptionAttribute[Color] = OptionAttribute()
    disabled_hover_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_hover_foreground: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_hover_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_hover_fg: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_active_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_active_foreground: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_active_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_active_fg: OptionAttribute[Optional[Color]] = OptionAttribute()
    hover_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    active_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    disabled_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    disabled_hover_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    disabled_active_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    text_align_x: OptionAttribute[str] = OptionAttribute()
    text_align_y: OptionAttribute[str] = OptionAttribute()
    text_offset: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    text_hover_offset: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    text_active_offset: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        /,
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
        theme: Optional[ThemeType] = None,
    ) -> None:
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

    def draw_onto(self, /, target: Renderer) -> None:
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
        shape.draw_onto(target)
        text.draw_onto(target)

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self, /) -> Tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self, /) -> None:
        callback: Optional[Callable[[], None]] = self.callback
        if callable(callback):
            callback()

    def text_set_font(
        self,
        /,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> None:
        self.__text.set_font(font, bold, italic, underline)
        self.__update_shape_size()

    def text_set_custom_line_font(self, /, index: int, font: Font) -> None:
        self.__text.set_custom_line_font(index, font)
        self.__update_shape_size()

    def text_remove_custom_line_font(self, /, index: int) -> None:
        self.__text.remove_custom_line_font(index)
        self.__update_shape_size()

    def img_rotate(self, /, angle_offset: float) -> None:
        self.__text.img_rotate(angle_offset)
        self.__update_shape_size()

    def img_set_rotation(self, /, angle: float) -> None:
        self.__text.img_set_rotation(angle)
        self.__update_shape_size()

    def img_set_scale(self, /, scale: float) -> None:
        self.__text.img_set_scale(scale)
        self.__update_shape_size()

    def img_scale_to_width(self, /, width: float) -> None:
        self.__text.img_scale_to_width(width)
        self.__update_shape_size()

    def img_scale_to_height(self, /, height: float) -> None:
        self.__text.img_scale_to_height(height)
        self.__update_shape_size()

    def img_scale_to_size(self, /, size: Tuple[float, float]) -> None:
        self.__text.img_scale_to_size(size)
        self.__update_shape_size()

    def img_set_min_width(self, /, width: float) -> None:
        self.__text.img_set_min_width(width)
        self.__update_shape_size()

    def img_set_max_width(self, /, width: float) -> None:
        self.__text.set_max_width(width)
        self.__update_shape_size()

    def img_set_min_height(self, /, height: float) -> None:
        self.__text.set_min_height(height)
        self.__update_shape_size()

    def img_set_max_height(self, /, height: float) -> None:
        self.__text.img_set_max_height(height)
        self.__update_shape_size()

    def img_set_min_size(self, /, size: Tuple[float, float]) -> None:
        self.__text.img_set_min_size(size)
        self.__update_shape_size()

    def img_set_max_size(self, /, size: Tuple[float, float]) -> None:
        self.__text.img_set_max_size(size)
        self.__update_shape_size()

    @overload
    def show_background(self, /) -> bool:
        ...

    @overload
    def show_background(self, /, status: bool) -> None:
        ...

    def show_background(self, /, status: Optional[bool] = None) -> Optional[bool]:
        if status is None:
            return self.__shape.is_shown()
        self.__shape.set_visibility(truth(status))
        return None

    def _apply_both_rotation_and_scale(self, /) -> None:
        self.__shape.scale = self.__text.scale = self.scale
        self.__shape.angle = self.__text.angle = self.angle
        self.__update_shape_size()

    def _apply_only_scale(self, /) -> None:
        self.__shape.scale = self.__text.scale = self.scale
        self.__update_shape_size()

    def _apply_only_rotation(self, /) -> None:
        self.__shape.angle = self.__text.angle = self.angle
        self.__update_shape_size()

    def _mouse_in_hitbox(self, /, mouse_pos: Tuple[float, float]) -> bool:
        rect: Rect = Rect((0, 0), self.get_area_size(apply_rotation=False))
        center: Tuple[float, float] = self.center
        rect.center = int(center[0]), int(center[1])
        pivot: Vector2 = Vector2(rect.center)
        mouse: Vector2 = Vector2(mouse_pos)
        mouse = pivot + (mouse - pivot).rotate(self.angle)
        return truth(rect.collidepoint(mouse.x, mouse.y))

    def _on_hover(self, /) -> None:
        self.__set_state("hover")
        return super()._on_hover()

    def _on_leave(self, /) -> None:
        self.__set_state("normal")
        return super()._on_leave()

    def _on_active_set(self, /) -> None:
        self.__set_state("active")
        return super()._on_active_set()

    def __set_state(self, /, button_state: Literal["normal", "hover", "active"]) -> None:
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

    def __update_state(self, /) -> None:
        if self.active:
            self.__set_state("active")
        elif self.hover:
            self.__set_state("hover")
        else:
            self.__set_state("normal")

    def __update_shape_size(self, /) -> None:
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

    @config.getter_key("text", use_key="message")
    @config.getter_key("text_font", use_key="font")
    @config.getter_key("text_justify", use_key="justify")
    @config.getter_key("text_wrap", use_key="wrap")
    @config.getter_key("text_shadow", use_key="shadow")
    @config.getter_key("text_shadow_x", use_key="shadow_x")
    @config.getter_key("text_shadow_y", use_key="shadow_y")
    @config.getter_key("text_shadow_color", use_key="shadow_color")
    @config.getter_key("compound")
    @config.getter_key("distance_text_img", use_key="distance")
    def __get_text_option(self, /, option: str) -> Any:
        return self.__text.config.get(option)

    @config.setter_key("text", use_key="message")
    @config.setter_key("text_font", use_key="font")
    @config.setter_key("text_justify", use_key="justify")
    @config.setter_key("text_wrap", use_key="wrap")
    @config.setter_key("text_shadow", use_key="shadow")
    @config.setter_key("text_shadow_x", use_key="shadow_x")
    @config.setter_key("text_shadow_y", use_key="shadow_y")
    @config.setter_key("text_shadow_color", use_key="shadow_color")
    @config.setter_key("compound")
    @config.setter_key("distance_text_img", use_key="distance")
    def __set_text_option(self, /, option: str, value: Any) -> None:
        return self.__text.config.set(option, value)

    config.on_update("text", __update_shape_size)
    config.on_update("text_font", __update_shape_size)
    config.on_update("text_justify", __update_shape_size)
    config.on_update("text_wrap", __update_shape_size)
    config.on_update("text_shadow", __update_shape_size)
    config.on_update("text_shadow_x", __update_shape_size)
    config.on_update("text_shadow_y", __update_shape_size)
    config.on_update("text_shadow_color", __update_shape_size)
    config.on_update("compound", __update_shape_size)
    config.on_update("distance_text_img", __update_shape_size)

    config.value_converter_static("fixed_width", valid_optional_float(min_value=0))
    config.value_converter_static("fixed_height", valid_optional_float(min_value=0))

    config.on_update("fixed_width", __update_shape_size)
    config.on_update("fixed_height", __update_shape_size)

    config.value_converter_static("x_add_size", valid_float(min_value=0))
    config.value_converter_static("y_add_size", valid_float(min_value=0))
    config.on_update("x_add_size", __update_shape_size)
    config.on_update("y_add_size", __update_shape_size)

    __STATE: Final[Dict[str, Tuple[Clickable.State, Literal["normal", "hover", "active"]]]] = {
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

    @config.getter_key("background")
    @config.getter_key("hover_background")
    @config.getter_key("active_background")
    @config.getter_key("disabled_background")
    @config.getter_key("disabled_hover_background")
    @config.getter_key("disabled_active_background")
    def __get_background(self, /, option: str) -> Optional[Color]:
        clickable_state, button_state = Button.__STATE[option]
        return self.__bg_dict[clickable_state][button_state]

    @config.setter_key("background")
    @config.setter_key("hover_background")
    @config.setter_key("active_background")
    @config.setter_key("disabled_background")
    @config.setter_key("disabled_hover_background")
    @config.setter_key("disabled_active_background")
    def __set_background(self, /, option: str, color: Optional[Color]) -> None:
        clickable_state, button_state = Button.__STATE[option]
        self.__bg_dict[clickable_state][button_state] = color

    config.value_validator_static("background", Color)
    config.value_validator_static("hover_background", Color, accept_none=True)
    config.value_validator_static("active_background", Color, accept_none=True)
    config.value_validator_static("disabled_background", Color)
    config.value_validator_static("disabled_hover_background", Color, accept_none=True)
    config.value_validator_static("disabled_active_background", Color, accept_none=True)

    config.on_update("background", __update_state)
    config.on_update("hover_background", __update_state)
    config.on_update("active_background", __update_state)
    config.on_update("disabled_background", __update_state)
    config.on_update("disabled_hover_background", __update_state)
    config.on_update("disabled_active_background", __update_state)

    config.set_autocopy("foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_foreground", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_foreground", copy_on_get=True, copy_on_set=True)

    @config.getter_key("foreground")
    @config.getter_key("hover_foreground")
    @config.getter_key("active_foreground")
    @config.getter_key("disabled_foreground")
    @config.getter_key("disabled_hover_foreground")
    @config.getter_key("disabled_active_foreground")
    def __get_foreground(self, /, option: str) -> Optional[Color]:
        clickable_state, button_state = Button.__STATE[option]
        return self.__fg_dict[clickable_state][button_state]

    @config.setter_key("foreground")
    @config.setter_key("hover_foreground")
    @config.setter_key("active_foreground")
    @config.setter_key("disabled_foreground")
    @config.setter_key("disabled_hover_foreground")
    @config.setter_key("disabled_active_foreground")
    def __set_foreground(self, /, option: str, color: Optional[Color]) -> None:
        clickable_state, button_state = Button.__STATE[option]
        self.__fg_dict[clickable_state][button_state] = color

    config.value_validator_static("foreground", Color)
    config.value_validator_static("hover_foreground", Color, accept_none=True)
    config.value_validator_static("active_foreground", Color, accept_none=True)
    config.value_validator_static("disabled_foreground", Color)
    config.value_validator_static("disabled_hover_foreground", Color, accept_none=True)
    config.value_validator_static("disabled_active_foreground", Color, accept_none=True)

    config.on_update("foreground", __update_state)
    config.on_update("hover_foreground", __update_state)
    config.on_update("active_foreground", __update_state)
    config.on_update("disabled_foreground", __update_state)
    config.on_update("disabled_hover_foreground", __update_state)
    config.on_update("disabled_active_foreground", __update_state)

    config.set_autocopy("img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_img", copy_on_get=True, copy_on_set=True)

    @config.getter_key("img")
    @config.getter_key("hover_img")
    @config.getter_key("active_img")
    @config.getter_key("disabled_img")
    @config.getter_key("disabled_hover_img")
    @config.getter_key("disabled_active_img")
    def __get_img(self, /, option: str) -> Optional[Surface]:
        clickable_state, button_state = Button.__STATE[option]
        return self.__img_dict[clickable_state][button_state]

    @config.setter_key("img")
    @config.setter_key("hover_img")
    @config.setter_key("active_img")
    @config.setter_key("disabled_img")
    @config.setter_key("disabled_hover_img")
    @config.setter_key("disabled_active_img")
    def __set_img(self, /, option: str, img: Optional[Surface]) -> None:
        clickable_state, button_state = Button.__STATE[option]
        self.__img_dict[clickable_state][button_state] = img

    config.value_validator_static("img", Surface, accept_none=True)
    config.value_validator_static("hover_img", Surface, accept_none=True)
    config.value_validator_static("active_img", Surface, accept_none=True)
    config.value_validator_static("disabled_img", Surface, accept_none=True)
    config.value_validator_static("disabled_hover_img", Surface, accept_none=True)
    config.value_validator_static("disabled_active_img", Surface, accept_none=True)

    config.on_update("img", __update_state)
    config.on_update("hover_img", __update_state)
    config.on_update("active_img", __update_state)
    config.on_update("disabled_img", __update_state)
    config.on_update("disabled_hover_img", __update_state)
    config.on_update("disabled_active_img", __update_state)

    config.enum("text_align_x", HorizontalAlign, return_value=True)
    config.enum("text_align_y", VerticalAlign, return_value=True)

    @config.value_converter_static("text_offset")
    @config.value_converter_static("text_hover_offset")
    @config.value_converter_static("text_active_offset")
    @staticmethod
    def __text_offset_validator(offset: Tuple[float, float]) -> Tuple[float, float]:
        return (float(offset[0]), float(offset[1]))

    @config.getter_key("outline")
    @config.getter_key("outline_color")
    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_shape_option(self, /, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_key("outline")
    @config.setter_key("outline_color")
    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_shape_option(self, /, option: str, value: Any) -> None:
        return self.__shape.config.set(option, value)

    @property
    def callback(self, /) -> Optional[Callable[[], None]]:
        self.__callback: Optional[Callable[[], None]]
        return self.__callback

    @callback.setter
    def callback(self, /, callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None


@Button.register
class ImageButton(TDrawable, Clickable, metaclass=MetaButton):
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

    img: OptionAttribute[Surface] = OptionAttribute()
    x_add_size: OptionAttribute[float] = OptionAttribute()
    y_add_size: OptionAttribute[float] = OptionAttribute()
    background: OptionAttribute[Color] = OptionAttribute()
    bg: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    hover_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    hover_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    active_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    active_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_background: OptionAttribute[Color] = OptionAttribute()
    disabled_bg: OptionAttribute[Color] = OptionAttribute()
    disabled_hover_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_hover_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_active_background: OptionAttribute[Optional[Color]] = OptionAttribute()
    disabled_active_bg: OptionAttribute[Optional[Color]] = OptionAttribute()
    hover_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    active_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    disabled_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    disabled_hover_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    disabled_active_img: OptionAttribute[Optional[Surface]] = OptionAttribute()
    hover_offset: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    active_offset: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        /,
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
        theme: Optional[ThemeType] = None,
    ) -> None:
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

    def draw_onto(self, /, target: Renderer) -> None:
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

        shape.draw_onto(target)
        image.draw_onto(target)

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self, /) -> Tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self, /) -> None:
        callback: Optional[Callable[[], None]] = self.callback
        if callable(callback):
            callback()

    def _apply_both_rotation_and_scale(self, /) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self, /) -> None:
        raise NotImplementedError

    def _apply_only_scale(self, /) -> None:
        self.__shape.scale = self.__image.scale = self.scale
        self.__update_shape_size()

    def _mouse_in_hitbox(self, /, mouse_pos: Tuple[float, float]) -> bool:
        return truth(self.rect.collidepoint(mouse_pos))

    def _on_hover(self, /) -> None:
        self.__set_state("hover")

    def _on_leave(self, /) -> None:
        self.__set_state("normal")

    def _on_active_set(self, /) -> None:
        self.__set_state("active")

    def __set_state(self, /, button_state: Literal["normal", "hover", "active"]) -> None:
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

    def __update_state(self, /) -> None:
        if self.active:
            self.__set_state("active")
        elif self.hover:
            self.__set_state("hover")
        else:
            self.__set_state("normal")

    def __update_shape_size(self, /) -> None:
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

    @config.value_converter_static("hover_offset")
    @config.value_converter_static("active_offset")
    @staticmethod
    def __img_offset_validator(offset: Tuple[float, float]) -> Tuple[float, float]:
        return (float(offset[0]), float(offset[1]))

    config.value_converter_static("x_add_size", valid_float(min_value=0))
    config.value_converter_static("y_add_size", valid_float(min_value=0))
    config.on_update("x_add_size", __update_shape_size)
    config.on_update("y_add_size", __update_shape_size)

    __STATE: Final[Dict[str, Tuple[Clickable.State, Literal["normal", "hover", "active"]]]] = {
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

    @config.getter_key("background")
    @config.getter_key("hover_background")
    @config.getter_key("active_background")
    @config.getter_key("disabled_background")
    @config.getter_key("disabled_hover_background")
    @config.getter_key("disabled_active_background")
    def __get_background(self, /, option: str) -> Optional[Color]:
        clickable_state, button_state = ImageButton.__STATE[option]
        return self.__bg_dict[clickable_state][button_state]

    @config.setter_key("background")
    @config.setter_key("hover_background")
    @config.setter_key("active_background")
    @config.setter_key("disabled_background")
    @config.setter_key("disabled_hover_background")
    @config.setter_key("disabled_active_background")
    def __set_background(self, /, option: str, color: Optional[Color]) -> None:
        clickable_state, button_state = ImageButton.__STATE[option]
        self.__bg_dict[clickable_state][button_state] = color

    config.value_validator_static("background", Color)
    config.value_validator_static("hover_background", Color, accept_none=True)
    config.value_validator_static("active_background", Color, accept_none=True)
    config.value_validator_static("disabled_background", Color)
    config.value_validator_static("disabled_hover_background", Color, accept_none=True)
    config.value_validator_static("disabled_active_background", Color, accept_none=True)

    config.on_update("background", __update_state)
    config.on_update("hover_background", __update_state)
    config.on_update("active_background", __update_state)
    config.on_update("disabled_background", __update_state)
    config.on_update("disabled_hover_background", __update_state)
    config.on_update("disabled_active_background", __update_state)

    config.set_autocopy("img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("active_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_hover_img", copy_on_get=True, copy_on_set=True)
    config.set_autocopy("disabled_active_img", copy_on_get=True, copy_on_set=True)

    @config.getter_key("img")
    @config.getter_key("hover_img")
    @config.getter_key("active_img")
    @config.getter_key("disabled_img")
    @config.getter_key("disabled_hover_img")
    @config.getter_key("disabled_active_img")
    def __get_img(self, /, option: str) -> Optional[Surface]:
        clickable_state, button_state = ImageButton.__STATE[option]
        return self.__img_dict[clickable_state][button_state]

    @config.setter_key("img")
    @config.setter_key("hover_img")
    @config.setter_key("active_img")
    @config.setter_key("disabled_img")
    @config.setter_key("disabled_hover_img")
    @config.setter_key("disabled_active_img")
    def __set_img(self, /, option: str, img: Optional[Surface]) -> None:
        clickable_state, button_state = ImageButton.__STATE[option]
        self.__img_dict[clickable_state][button_state] = img

    config.value_validator_static("img", Surface)
    config.value_validator_static("hover_img", Surface, accept_none=True)
    config.value_validator_static("active_img", Surface, accept_none=True)
    config.value_validator_static("disabled_img", Surface, accept_none=True)
    config.value_validator_static("disabled_hover_img", Surface, accept_none=True)
    config.value_validator_static("disabled_active_img", Surface, accept_none=True)

    config.on_update("img", __update_state)
    config.on_update("hover_img", __update_state)
    config.on_update("active_img", __update_state)
    config.on_update("disabled_img", __update_state)
    config.on_update("disabled_hover_img", __update_state)
    config.on_update("disabled_active_img", __update_state)

    @config.getter_key("outline")
    @config.getter_key("outline_color")
    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_shape_option(self, /, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_key("outline")
    @config.setter_key("outline_color")
    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_shape_option(self, /, option: str, value: Any) -> None:
        return self.__shape.config.set(option, value)

    @property
    def callback(self, /) -> Optional[Callable[[], None]]:
        self.__callback: Optional[Callable[[], None]]
        return self.__callback

    @callback.setter
    def callback(self, /, callback: Optional[Callable[[], None]]) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None


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
