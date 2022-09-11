# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Button module"""

from __future__ import annotations

__all__ = ["Button", "ImageButton"]

from enum import auto, unique
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Literal, Sequence, TypeAlias, TypedDict, overload

from ...graphics.color import BLACK, BLUE, GRAY, GRAY_DARK, GRAY_LIGHT, TRANSPARENT, WHITE, Color
from ...graphics.drawable import Drawable
from ...graphics.image import Image
from ...graphics.rect import Rect
from ...graphics.shape import RectangleShape
from ...graphics.surface import Surface
from ...graphics.text import TextImage
from ...graphics.transformable import Transformable
from ...math import Vector2
from ...system.configuration import Configuration, ConfigurationTemplate, OptionAttribute, initializer
from ...system.enum import AutoLowerNameEnum
from ...system.theme import NoTheme, ThemedObjectMeta, ThemeType
from ...system.utils.typing import reflect_method_signature
from ...system.validation import valid_float, valid_integer, valid_optional_float
from ...window.clickable import Clickable
from .abc import AbstractWidget

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...graphics.font import Font
    from ...graphics.renderer import AbstractRenderer
    from ...window.cursor import Cursor
    from ...window.display import Window
    from ...window.scene import Scene

    _TupleFont: TypeAlias = tuple[str | None, int]
    _TextFont: TypeAlias = Font | _TupleFont


@TextImage.register_themed_subclass
class Button(Drawable, Transformable, AbstractWidget, metaclass=ThemedObjectMeta):
    Justify: TypeAlias = TextImage.Justify
    Compound: TypeAlias = TextImage.Compound

    __theme_ignore__: ClassVar[Sequence[str]] = ("callback",)
    __theme_associations__: ClassVar[dict[type, dict[str, str]]] = {
        TextImage: {
            "color": "fg",
            "distance": "distance_text_img",
        },
    }
    __theme_override__: Sequence[str] = (
        "outline",
        "outline_color",
    )

    @unique
    class HorizontalAlign(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        CENTER = auto()

    @unique
    class VerticalAlign(AutoLowerNameEnum):
        TOP = auto()
        BOTTOM = auto()
        CENTER = auto()

    __HORIZONTAL_ALIGN_POS: ClassVar[dict[str, str]] = {
        "left": "left",
        "right": "right",
        "center": "centerx",
    }
    __VERTICAL_ALIGN_POS: ClassVar[dict[str, str]] = {
        "top": "top",
        "bottom": "bottom",
        "center": "centery",
    }

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
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
        "highlight_color",
        "highlight_thickness",
        "img",
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

    fixed_width: OptionAttribute[float | None] = OptionAttribute()
    fixed_height: OptionAttribute[float | None] = OptionAttribute()
    x_add_size: OptionAttribute[float] = OptionAttribute()
    y_add_size: OptionAttribute[float] = OptionAttribute()
    background: OptionAttribute[Color] = OptionAttribute()
    foreground: OptionAttribute[Color] = OptionAttribute()
    bg: OptionAttribute[Color] = OptionAttribute()
    fg: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    hover_background: OptionAttribute[Color | None] = OptionAttribute()
    hover_foreground: OptionAttribute[Color | None] = OptionAttribute()
    hover_bg: OptionAttribute[Color | None] = OptionAttribute()
    hover_fg: OptionAttribute[Color | None] = OptionAttribute()
    active_background: OptionAttribute[Color | None] = OptionAttribute()
    active_foreground: OptionAttribute[Color | None] = OptionAttribute()
    active_bg: OptionAttribute[Color | None] = OptionAttribute()
    active_fg: OptionAttribute[Color | None] = OptionAttribute()
    disabled_background: OptionAttribute[Color] = OptionAttribute()
    disabled_foreground: OptionAttribute[Color] = OptionAttribute()
    disabled_bg: OptionAttribute[Color] = OptionAttribute()
    disabled_fg: OptionAttribute[Color] = OptionAttribute()
    disabled_hover_background: OptionAttribute[Color | None] = OptionAttribute()
    disabled_hover_foreground: OptionAttribute[Color | None] = OptionAttribute()
    disabled_hover_bg: OptionAttribute[Color | None] = OptionAttribute()
    disabled_hover_fg: OptionAttribute[Color | None] = OptionAttribute()
    disabled_active_background: OptionAttribute[Color | None] = OptionAttribute()
    disabled_active_foreground: OptionAttribute[Color | None] = OptionAttribute()
    disabled_active_bg: OptionAttribute[Color | None] = OptionAttribute()
    disabled_active_fg: OptionAttribute[Color | None] = OptionAttribute()
    img: OptionAttribute[Surface | None] = OptionAttribute()
    hover_img: OptionAttribute[Surface | None] = OptionAttribute()
    active_img: OptionAttribute[Surface | None] = OptionAttribute()
    disabled_img: OptionAttribute[Surface | None] = OptionAttribute()
    disabled_hover_img: OptionAttribute[Surface | None] = OptionAttribute()
    disabled_active_img: OptionAttribute[Surface | None] = OptionAttribute()
    highlight_color: OptionAttribute[Color] = OptionAttribute()
    highlight_thickness: OptionAttribute[int] = OptionAttribute()
    text_align_x: OptionAttribute[str] = OptionAttribute()
    text_align_y: OptionAttribute[str] = OptionAttribute()
    text_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()
    text_hover_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()
    text_active_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    @config.section_property(exclude_options={"img"})
    def text(self) -> Configuration[TextImage]:
        return self.__text.config

    @initializer
    def __init__(
        self,
        master: AbstractWidget | Clickable | Scene | Window,
        text: str = "",
        callback: Callable[[], None] | None = None,
        *,
        img: Surface | None = None,
        compound: str = "left",
        distance_text_img: float = 5,
        font: _TextFont | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        state: str = "normal",
        width: float | None = None,
        height: float | None = None,
        x_add_size: float = 20,
        y_add_size: float = 20,
        show_bg: bool = True,
        bg: Color = GRAY_LIGHT,
        fg: Color = BLACK,
        outline: int = 2,
        outline_color: Color = BLACK,
        hover_bg: Color | None = WHITE,
        hover_fg: Color | None = None,
        hover_sound: Sound | None = None,
        active_bg: Color | None = GRAY,
        active_fg: Color | None = None,
        click_sound: Sound | None = None,
        disabled_bg: Color = GRAY_DARK,
        disabled_fg: Color = BLACK,
        disabled_sound: Sound | None = None,
        disabled_hover_bg: Color | None = None,
        disabled_hover_fg: Color | None = None,
        disabled_active_bg: Color | None = None,
        disabled_active_fg: Color | None = None,
        hover_img: Surface | None = None,
        active_img: Surface | None = None,
        disabled_img: Surface | None = None,
        disabled_hover_img: Surface | None = None,
        disabled_active_img: Surface | None = None,
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        take_focus: bool = True,
        focus_on_hover: bool | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        text_align_x: str = "center",
        text_align_y: str = "center",
        text_offset: tuple[float, float] = (0, 0),
        text_hover_offset: tuple[float, float] = (0, 0),
        text_active_offset: tuple[float, float] = (0, 0),
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
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
        )
        self.outline = outline
        self.outline_color = outline_color
        self.__shape.set_visibility(show_bg)
        self.__bg_dict: dict[Clickable.State, _ButtonColor] = {
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
        self.__fg_dict: dict[Clickable.State, _ButtonColor] = {
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
        self.__img_dict: dict[Clickable.State, _ImageDict] = {
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
        self.highlight_color = highlight_color
        self.highlight_thickness = highlight_thickness
        self.__text_align_x: Button.HorizontalAlign
        self.__text_align_y: Button.VerticalAlign
        self.text_align_x = text_align_x
        self.text_align_y = text_align_y
        self.text_offset = text_offset
        self.text_hover_offset = text_hover_offset
        self.text_active_offset = text_active_offset

    def draw_onto(self, target: AbstractRenderer) -> None:
        angle: float = self.angle
        scale_x, scale_y = self.scale

        def compute_offset(offset: tuple[float, float]) -> tuple[float, float]:
            return offset[0] * scale_x, offset[1] * scale_y

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

    def get_local_size(self) -> tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self) -> None:
        callback: Callable[[], None] | None = self.callback
        if callable(callback):
            callback()

    @reflect_method_signature(TextImage.set_font)
    def text_set_font(self, *args: Any, **kwargs: Any) -> None:
        self.__text.set_font(*args, **kwargs)
        self.config.update_section("text")

    @reflect_method_signature(TextImage.set_custom_line_font)
    def text_set_custom_line_font(self, *args: Any, **kwargs: Any) -> None:
        self.__text.set_custom_line_font(*args, **kwargs)
        self.config.update_section("text")

    @reflect_method_signature(TextImage.remove_custom_line_font)
    def text_remove_custom_line_font(self, *args: Any, **kwargs: Any) -> None:
        self.__text.remove_custom_line_font(*args, **kwargs)
        self.config.update_section("text")

    @reflect_method_signature(TextImage.img_rotate)
    def img_rotate(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_rotate(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_rotation)
    def img_set_rotation(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_rotation(*args, **kwargs)
        self.__update_shape_size()

    @overload
    def img_set_scale(self, *, scale_x: float) -> None:
        ...

    @overload
    def img_set_scale(self, *, scale_y: float) -> None:
        ...

    @overload
    def img_set_scale(self, *, scale_x: float, scale_y: float) -> None:
        ...

    @overload
    def img_set_scale(self, __scale: float, /) -> None:
        ...

    @overload
    def img_set_scale(self, __scale: tuple[float, float], /) -> None:
        ...

    # @reflect_method_signature() doesn't work with overloads
    def img_set_scale(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_scale(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_scale_to_width)
    def img_scale_to_width(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_scale_to_width(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_scale_to_height)
    def img_scale_to_height(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_scale_to_height(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_scale_to_size)
    def img_scale_to_size(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_scale_to_size(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_min_width)
    def img_set_min_width(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_min_width(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_max_width)
    def img_set_max_width(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_max_width(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_min_height)
    def img_set_min_height(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_min_height(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_max_height)
    def img_set_max_height(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_max_height(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_min_size)
    def img_set_min_size(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_min_size(*args, **kwargs)
        self.__update_shape_size()

    @reflect_method_signature(TextImage.img_set_max_size)
    def img_set_max_size(self, *args: Any, **kwargs: Any) -> None:
        self.__text.img_set_max_size(*args, **kwargs)
        self.__update_shape_size()

    @overload
    def show_background(self) -> bool:
        ...

    @overload
    def show_background(self, status: bool) -> None:
        ...

    def show_background(self, status: bool | None = None) -> bool | None:
        if status is None:
            return self.__shape.is_shown()
        self.__shape.set_visibility(bool(status))
        return None

    def _apply_both_rotation_and_scale(self) -> None:
        self.__shape.set_rotation_and_scale(self.angle, self.scale)
        self.__text.set_rotation_and_scale(self.angle, self.scale)
        self.__update_shape_size()

    def _apply_only_scale(self) -> None:
        self.__shape.scale = self.__text.scale = self.scale
        self.__update_shape_size()

    def _apply_only_rotation(self) -> None:
        self.__shape.angle = self.__text.angle = self.angle
        self.__update_shape_size()

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        rect: Rect = Rect((0, 0), self.get_area_size(apply_rotation=False))
        center: tuple[float, float] = self.center
        rect.center = int(center[0]), int(center[1])
        pivot: Vector2 = Vector2(rect.center)
        mouse: Vector2 = Vector2(mouse_pos)
        mouse = pivot + (mouse - pivot).rotate(self.angle)
        return rect.collidepoint(mouse.x, mouse.y)

    def _on_hover(self) -> None:
        self.__set_state("hover")
        return super()._on_hover()

    def _on_leave(self) -> None:
        self.__set_state("normal")
        return super()._on_leave()

    def _on_active_set(self) -> None:
        self.__set_state("active")
        return super()._on_active_set()

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

    def _on_focus_set(self) -> None:
        self.__update_shape_outline()
        return super()._on_focus_set()

    def _on_focus_leave(self) -> None:
        self.__update_shape_outline()
        return super()._on_focus_leave()

    def __set_state(self, button_state: Literal["normal", "hover", "active"]) -> None:
        clickable_state: Clickable.State = Clickable.State(self.state)
        bg_color: Color | None = self.__bg_dict[clickable_state][button_state]
        if bg_color is None:
            bg_color = self.__bg_dict[clickable_state]["normal"]
        fg_color: Color | None = self.__fg_dict[clickable_state][button_state]
        if fg_color is None:
            fg_color = self.__fg_dict[clickable_state]["normal"]
        img: Surface | None = self.__img_dict[clickable_state][button_state]
        if img is None:
            img = self.__img_dict[clickable_state]["normal"]
        self.__shape.config.update(color=bg_color)
        self.__text.config.update(color=fg_color, img=img)
        self.config.update_section("text")

    def __update_state(self) -> None:
        if self.active:
            self._on_active_set()
        elif self.hover:
            self._on_hover()
        else:
            self._on_leave()

    def __update_shape_size(self) -> None:
        text_width, text_height = self.__text.get_local_size()
        scale_x, scale_y = self.scale
        x_add_size: float = self.x_add_size * scale_x
        y_add_size: float = self.y_add_size * scale_y
        fixed_width: float | None = self.fixed_width
        fixed_height: float | None = self.fixed_height

        new_size: tuple[float, float] = (
            text_width + x_add_size if fixed_width is None else fixed_width,
            text_height + y_add_size if fixed_height is None else fixed_height,
        )

        if self.config.has_initialization_context():
            self.__shape.local_size = new_size
        else:
            center = self.center
            self.__shape.local_size = new_size
            self.center = center

    config.on_section_update("text", __update_shape_size)

    config.add_value_converter_on_set_static("fixed_width", valid_optional_float(min_value=0))
    config.add_value_converter_on_set_static("fixed_height", valid_optional_float(min_value=0))

    config.on_update("fixed_width", __update_shape_size)
    config.on_update("fixed_height", __update_shape_size)

    config.add_value_converter_on_set_static("x_add_size", valid_float(min_value=0))
    config.add_value_converter_on_set_static("y_add_size", valid_float(min_value=0))
    config.on_update("x_add_size", __update_shape_size)
    config.on_update("y_add_size", __update_shape_size)

    __TupleState: TypeAlias = tuple[Clickable.State, Literal["normal", "hover", "active"]]
    __STATE: Final[dict[str, __TupleState]] = {
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

    @config.getter_with_key_from_map("background", __STATE)
    @config.getter_with_key_from_map("hover_background", __STATE)
    @config.getter_with_key_from_map("active_background", __STATE)
    @config.getter_with_key_from_map("disabled_background", __STATE)
    @config.getter_with_key_from_map("disabled_hover_background", __STATE)
    @config.getter_with_key_from_map("disabled_active_background", __STATE)
    def __get_background(self, key: __TupleState) -> Color | None:
        clickable_state, button_state = key
        return self.__bg_dict[clickable_state][button_state]

    @config.setter_with_key_from_map("background", __STATE)
    @config.setter_with_key_from_map("hover_background", __STATE)
    @config.setter_with_key_from_map("active_background", __STATE)
    @config.setter_with_key_from_map("disabled_background", __STATE)
    @config.setter_with_key_from_map("disabled_hover_background", __STATE)
    @config.setter_with_key_from_map("disabled_active_background", __STATE)
    def __set_background(self, key: __TupleState, color: Color | None) -> None:
        clickable_state, button_state = key
        self.__bg_dict[clickable_state][button_state] = color

    config.add_value_validator_static("background", Color)
    config.add_value_validator_static("hover_background", Color, accept_none=True)
    config.add_value_validator_static("active_background", Color, accept_none=True)
    config.add_value_validator_static("disabled_background", Color)
    config.add_value_validator_static("disabled_hover_background", Color, accept_none=True)
    config.add_value_validator_static("disabled_active_background", Color, accept_none=True)

    config.on_update("background", __update_state)
    config.on_update("hover_background", __update_state)
    config.on_update("active_background", __update_state)
    config.on_update("disabled_background", __update_state)
    config.on_update("disabled_hover_background", __update_state)
    config.on_update("disabled_active_background", __update_state)

    @config.getter_with_key_from_map("foreground", __STATE)
    @config.getter_with_key_from_map("hover_foreground", __STATE)
    @config.getter_with_key_from_map("active_foreground", __STATE)
    @config.getter_with_key_from_map("disabled_foreground", __STATE)
    @config.getter_with_key_from_map("disabled_hover_foreground", __STATE)
    @config.getter_with_key_from_map("disabled_active_foreground", __STATE)
    def __get_foreground(self, key: __TupleState) -> Color | None:
        clickable_state, button_state = key
        return self.__fg_dict[clickable_state][button_state]

    @config.setter_with_key_from_map("foreground", __STATE)
    @config.setter_with_key_from_map("hover_foreground", __STATE)
    @config.setter_with_key_from_map("active_foreground", __STATE)
    @config.setter_with_key_from_map("disabled_foreground", __STATE)
    @config.setter_with_key_from_map("disabled_hover_foreground", __STATE)
    @config.setter_with_key_from_map("disabled_active_foreground", __STATE)
    def __set_foreground(self, key: __TupleState, color: Color | None) -> None:
        clickable_state, button_state = key
        self.__fg_dict[clickable_state][button_state] = color

    config.add_value_validator_static("foreground", Color)
    config.add_value_validator_static("hover_foreground", Color, accept_none=True)
    config.add_value_validator_static("active_foreground", Color, accept_none=True)
    config.add_value_validator_static("disabled_foreground", Color)
    config.add_value_validator_static("disabled_hover_foreground", Color, accept_none=True)
    config.add_value_validator_static("disabled_active_foreground", Color, accept_none=True)

    config.on_update("foreground", __update_state)
    config.on_update("hover_foreground", __update_state)
    config.on_update("active_foreground", __update_state)
    config.on_update("disabled_foreground", __update_state)
    config.on_update("disabled_hover_foreground", __update_state)
    config.on_update("disabled_active_foreground", __update_state)

    @config.getter_with_key_from_map("img", __STATE)
    @config.getter_with_key_from_map("hover_img", __STATE)
    @config.getter_with_key_from_map("active_img", __STATE)
    @config.getter_with_key_from_map("disabled_img", __STATE)
    @config.getter_with_key_from_map("disabled_hover_img", __STATE)
    @config.getter_with_key_from_map("disabled_active_img", __STATE)
    def __get_img(self, key: __TupleState) -> Surface | None:
        clickable_state, button_state = key
        return self.__img_dict[clickable_state][button_state]

    @config.setter_with_key_from_map("img", __STATE)
    @config.setter_with_key_from_map("hover_img", __STATE)
    @config.setter_with_key_from_map("active_img", __STATE)
    @config.setter_with_key_from_map("disabled_img", __STATE)
    @config.setter_with_key_from_map("disabled_hover_img", __STATE)
    @config.setter_with_key_from_map("disabled_active_img", __STATE)
    def __set_img(self, key: __TupleState, img: Surface | None) -> None:
        clickable_state, button_state = key
        self.__img_dict[clickable_state][button_state] = img

    config.add_value_validator_static("img", Surface, accept_none=True)
    config.add_value_validator_static("hover_img", Surface, accept_none=True)
    config.add_value_validator_static("active_img", Surface, accept_none=True)
    config.add_value_validator_static("disabled_img", Surface, accept_none=True)
    config.add_value_validator_static("disabled_hover_img", Surface, accept_none=True)
    config.add_value_validator_static("disabled_active_img", Surface, accept_none=True)

    config.on_update("img", __update_state)
    config.on_update("hover_img", __update_state)
    config.on_update("active_img", __update_state)
    config.on_update("disabled_img", __update_state)
    config.on_update("disabled_hover_img", __update_state)
    config.on_update("disabled_active_img", __update_state)

    config.add_enum_converter("text_align_x", HorizontalAlign, return_value_on_get=True)
    config.add_enum_converter("text_align_y", VerticalAlign, return_value_on_get=True)

    @config.add_value_converter_on_set_static("text_offset")
    @config.add_value_converter_on_set_static("text_hover_offset")
    @config.add_value_converter_on_set_static("text_active_offset")
    @staticmethod
    def __text_offset_validator(offset: tuple[float, float]) -> tuple[float, float]:
        return (float(offset[0]), float(offset[1]))

    @config.getter_with_key("border_radius")
    @config.getter_with_key("border_top_left_radius")
    @config.getter_with_key("border_top_right_radius")
    @config.getter_with_key("border_bottom_left_radius")
    @config.getter_with_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> None:
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
    def callback(self) -> Callable[[], None] | None:
        self.__callback: Callable[[], None] | None
        return self.__callback

    @callback.setter
    def callback(self, callback: Callable[[], None] | None) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None


@Button.register_themed_subclass
class ImageButton(Drawable, Transformable, AbstractWidget, metaclass=ThemedObjectMeta):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
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
        "highlight_color",
        "highlight_thickness",
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
    hover_background: OptionAttribute[Color | None] = OptionAttribute()
    hover_bg: OptionAttribute[Color | None] = OptionAttribute()
    active_background: OptionAttribute[Color | None] = OptionAttribute()
    active_bg: OptionAttribute[Color | None] = OptionAttribute()
    disabled_background: OptionAttribute[Color] = OptionAttribute()
    disabled_bg: OptionAttribute[Color] = OptionAttribute()
    disabled_hover_background: OptionAttribute[Color | None] = OptionAttribute()
    disabled_hover_bg: OptionAttribute[Color | None] = OptionAttribute()
    disabled_active_background: OptionAttribute[Color | None] = OptionAttribute()
    disabled_active_bg: OptionAttribute[Color | None] = OptionAttribute()
    hover_img: OptionAttribute[Surface | None] = OptionAttribute()
    active_img: OptionAttribute[Surface | None] = OptionAttribute()
    disabled_img: OptionAttribute[Surface | None] = OptionAttribute()
    disabled_hover_img: OptionAttribute[Surface | None] = OptionAttribute()
    disabled_active_img: OptionAttribute[Surface | None] = OptionAttribute()
    highlight_color: OptionAttribute[Color] = OptionAttribute()
    highlight_thickness: OptionAttribute[int] = OptionAttribute()
    hover_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()
    active_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: AbstractWidget | Clickable | Scene | Window,
        img: Surface,
        callback: Callable[[], None] | None = None,
        *,
        hover_img: Surface | None = None,
        active_img: Surface | None = None,
        disabled_img: Surface | None = None,
        disabled_hover_img: Surface | None = None,
        disabled_active_img: Surface | None = None,
        state: str = "normal",
        x_add_size: float = 10,
        y_add_size: float = 10,
        bg: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        hover_bg: Color | None = None,
        active_bg: Color | None = None,
        disabled_bg: Color | None = None,
        disabled_hover_bg: Color | None = None,
        disabled_active_bg: Color | None = None,
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        hover_offset: tuple[float, float] = (0, 0),
        active_offset: tuple[float, float] = (0, 3),
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master=master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            **kwargs,
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
        )
        self.__bg_dict: dict[Clickable.State, _ButtonColor] = {
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
        self.__img_dict: dict[Clickable.State, _ImageButtonDict] = {
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
        self.outline = outline
        self.outline_color = outline_color
        self.highlight_color = highlight_color
        self.highlight_thickness = highlight_thickness
        self.hover_offset = hover_offset
        self.active_offset = active_offset

    def draw_onto(self, target: AbstractRenderer) -> None:
        scale_x, scale_y = self.scale

        def compute_offset(offset: tuple[float, float]) -> tuple[float, float]:
            return offset[0] * scale_x, offset[1] * scale_y

        shape: RectangleShape = self.__shape
        image: Image = self.__image

        shape.center = image.center = self.center
        if self.active:
            image.translate(compute_offset(self.active_offset))
        elif self.hover:
            image.translate(compute_offset(self.hover_offset))

        shape.draw_onto(target)
        image.draw_onto(target)

    def get_local_size(self) -> tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self) -> None:
        callback: Callable[[], None] | None = self.callback
        if callable(callback):
            callback()

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        self.__shape.scale = self.__image.scale = self.scale
        self.__update_shape_size()

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.get_rect().collidepoint(mouse_pos)

    def _on_hover(self) -> None:
        self.__set_state("hover")

    def _on_leave(self) -> None:
        self.__set_state("normal")

    def _on_active_set(self) -> None:
        self.__set_state("active")

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

    def __set_state(self, button_state: Literal["normal", "hover", "active"]) -> None:
        clickable_state: Clickable.State = Clickable.State(self.state)
        bg_color: Color | None = self.__bg_dict[clickable_state][button_state]
        if bg_color is None:
            bg_color = self.__bg_dict[clickable_state]["normal"]
        img: Surface | None = self.__img_dict[clickable_state][button_state]
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
        scale_x, scale_y = self.scale
        x_add_size: float = self.x_add_size * scale_x
        y_add_size: float = self.y_add_size * scale_y
        new_size: tuple[float, float] = (img_width + x_add_size, img_height + y_add_size)
        if self.config.has_initialization_context():
            self.__shape.local_size = new_size
        else:
            center = self.center
            self.__shape.local_size = new_size
            self.center = center

    @config.add_value_converter_on_set_static("hover_offset")
    @config.add_value_converter_on_set_static("active_offset")
    @staticmethod
    def __img_offset_validator(offset: tuple[float, float]) -> tuple[float, float]:
        return (float(offset[0]), float(offset[1]))

    config.add_value_converter_on_set_static("x_add_size", valid_float(min_value=0))
    config.add_value_converter_on_set_static("y_add_size", valid_float(min_value=0))
    config.on_update("x_add_size", __update_shape_size)
    config.on_update("y_add_size", __update_shape_size)

    __TupleState: TypeAlias = tuple[Clickable.State, Literal["normal", "hover", "active"]]
    __STATE: Final[dict[str, __TupleState]] = {
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

    @config.getter_with_key_from_map("background", __STATE)
    @config.getter_with_key_from_map("hover_background", __STATE)
    @config.getter_with_key_from_map("active_background", __STATE)
    @config.getter_with_key_from_map("disabled_background", __STATE)
    @config.getter_with_key_from_map("disabled_hover_background", __STATE)
    @config.getter_with_key_from_map("disabled_active_background", __STATE)
    def __get_background(self, key: __TupleState) -> Color | None:
        clickable_state, button_state = key
        return self.__bg_dict[clickable_state][button_state]

    @config.setter_with_key_from_map("background", __STATE)
    @config.setter_with_key_from_map("hover_background", __STATE)
    @config.setter_with_key_from_map("active_background", __STATE)
    @config.setter_with_key_from_map("disabled_background", __STATE)
    @config.setter_with_key_from_map("disabled_hover_background", __STATE)
    @config.setter_with_key_from_map("disabled_active_background", __STATE)
    def __set_background(self, key: __TupleState, color: Color | None) -> None:
        clickable_state, button_state = key
        self.__bg_dict[clickable_state][button_state] = color

    config.add_value_validator_static("background", Color)
    config.add_value_validator_static("hover_background", Color, accept_none=True)
    config.add_value_validator_static("active_background", Color, accept_none=True)
    config.add_value_validator_static("disabled_background", Color)
    config.add_value_validator_static("disabled_hover_background", Color, accept_none=True)
    config.add_value_validator_static("disabled_active_background", Color, accept_none=True)

    config.on_update("background", __update_state)
    config.on_update("hover_background", __update_state)
    config.on_update("active_background", __update_state)
    config.on_update("disabled_background", __update_state)
    config.on_update("disabled_hover_background", __update_state)
    config.on_update("disabled_active_background", __update_state)

    @config.getter_with_key_from_map("img", __STATE)
    @config.getter_with_key_from_map("hover_img", __STATE)
    @config.getter_with_key_from_map("active_img", __STATE)
    @config.getter_with_key_from_map("disabled_img", __STATE)
    @config.getter_with_key_from_map("disabled_hover_img", __STATE)
    @config.getter_with_key_from_map("disabled_active_img", __STATE)
    def __get_img(self, key: __TupleState) -> Surface | None:
        clickable_state, button_state = key
        return self.__img_dict[clickable_state][button_state]

    @config.setter_with_key_from_map("img", __STATE)
    @config.setter_with_key_from_map("hover_img", __STATE)
    @config.setter_with_key_from_map("active_img", __STATE)
    @config.setter_with_key_from_map("disabled_img", __STATE)
    @config.setter_with_key_from_map("disabled_hover_img", __STATE)
    @config.setter_with_key_from_map("disabled_active_img", __STATE)
    def __set_img(self, key: __TupleState, img: Surface | None) -> None:
        clickable_state, button_state = key
        self.__img_dict[clickable_state][button_state] = img

    config.add_value_validator_static("img", Surface)
    config.add_value_validator_static("hover_img", Surface, accept_none=True)
    config.add_value_validator_static("active_img", Surface, accept_none=True)
    config.add_value_validator_static("disabled_img", Surface, accept_none=True)
    config.add_value_validator_static("disabled_hover_img", Surface, accept_none=True)
    config.add_value_validator_static("disabled_active_img", Surface, accept_none=True)

    config.on_update("img", __update_state)
    config.on_update("hover_img", __update_state)
    config.on_update("active_img", __update_state)
    config.on_update("disabled_img", __update_state)
    config.on_update("disabled_hover_img", __update_state)
    config.on_update("disabled_active_img", __update_state)

    @config.getter_with_key("border_radius")
    @config.getter_with_key("border_top_left_radius")
    @config.getter_with_key("border_top_right_radius")
    @config.getter_with_key("border_bottom_left_radius")
    @config.getter_with_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> None:
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
    def callback(self) -> Callable[[], None] | None:
        self.__callback: Callable[[], None] | None
        return self.__callback

    @callback.setter
    def callback(self, callback: Callable[[], None] | None) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None


class _ButtonColor(TypedDict):
    normal: Color
    hover: Color | None
    active: Color | None


class _ImageDict(TypedDict):
    normal: Surface | None
    hover: Surface | None
    active: Surface | None


class _ImageButtonDict(TypedDict):
    normal: Surface
    hover: Surface | None
    active: Surface | None


@overload
def _copy_color(c: Color | None) -> Color | None:
    ...


@overload
def _copy_color(c: Color | None, default: Color) -> Color:
    ...


def _copy_color(c: Color | None, default: Color | None = None) -> Color | None:
    return Color(c) if c is not None else (None if default is None else _copy_color(default))


@overload
def _copy_img(surface: Surface | None) -> Surface | None:
    ...


@overload
def _copy_img(surface: Surface | None, default: Surface) -> Surface:
    ...


def _copy_img(surface: Surface | None, default: Surface | None = None) -> Surface | None:
    return surface.copy() if surface is not None else (None if default is None else _copy_img(default))
