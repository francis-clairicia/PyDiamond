# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Callable, Dict, Literal, Optional, Tuple, TypedDict, Union, overload
from enum import Enum, unique
from operator import truth

from pygame.color import Color
from pygame.font import Font
from pygame.mixer import Sound
from pygame.surface import Surface

from .drawable import ThemedDrawable
from .clickable import Clickable
from .shape import RectangleShape
from .text import Text
from .window import Window
from .scene import Scene
from .colors import WHITE, GRAY, GRAY_LIGHT, GRAY_DARK, BLACK
from .theme import NoTheme, Theme

_ButtonCallback = Callable[[], None]
_TextFont = Union[Font, Tuple[Optional[str], int]]


class _ButtonColor(TypedDict):
    normal: Color
    hover: Optional[Color]
    active: Optional[Color]


class Button(ThemedDrawable, Clickable):
    Justify = Text.Justify

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

    __HORIZONTAL_ALIGN_POS: Dict[HorizontalAlign, str] = {
        HorizontalAlign.LEFT: "left",
        HorizontalAlign.RIGHT: "right",
        HorizontalAlign.CENTER: "centerx",
    }
    __VERTICAL_ALIGN_POS: Dict[VerticalAlign, str] = {
        VerticalAlign.TOP: "top",
        VerticalAlign.BOTTOM: "bottom",
        VerticalAlign.CENTER: "centery",
    }

    def __init__(
        self,
        master: Union[Scene, Window],
        text: str = "",
        *,
        font: Optional[_TextFont] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        callback: Optional[_ButtonCallback] = None,
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
        on_click_sound: Optional[Sound] = None,
        disabled_bg: Color = GRAY_DARK,
        disabled_fg: Color = BLACK,
        disabled_sound: Optional[Sound] = None,
        disabled_hover_bg: Optional[Color] = None,
        disabled_hover_fg: Optional[Color] = None,
        disabled_active_bg: Optional[Color] = None,
        disabled_active_fg: Optional[Color] = None,
        # highlight_color=BLUE,
        # highlight_thickness=2,
        # cursor=None,
        # disabled_cursor=None,
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
        theme: Optional[Theme] = None
    ) -> None:
        ThemedDrawable.__init__(self)
        Clickable.__init__(
            self,
            master=master,
            state=state,
            hover_sound=hover_sound,
            on_click_sound=on_click_sound,
            disabled_sound=disabled_sound,
        )
        self.__text: Text = Text(
            message=text,
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
        self.__callback: Optional[_ButtonCallback] = callback if callable(callback) else None
        self.__x_add_size: float = max(float(x_add_size), 0)
        self.__y_add_size: float = max(float(y_add_size), 0)
        self.__fixed_width: Optional[float] = max(float(width), 0) if width is not None else None
        self.__fixed_height: Optional[float] = max(float(height), 0) if height is not None else None
        self.__shape: RectangleShape = RectangleShape(
            width=self.__text.width + self.__x_add_size if self.__fixed_width is None else self.__fixed_width,
            height=self.__text.height + self.__y_add_size if self.__fixed_height is None else self.__fixed_height,
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
        self.__bg: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {
                "normal": Color(bg),
                "hover": Color(hover_bg) if hover_bg is not None else None,
                "active": Color(active_bg) if active_bg is not None else None,
            },
            Clickable.State.DISABLED: {
                "normal": Color(disabled_bg),
                "hover": Color(disabled_hover_bg) if disabled_hover_bg is not None else None,
                "active": Color(disabled_active_bg) if disabled_active_bg is not None else None,
            },
        }
        self.__fg: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {
                "normal": Color(fg),
                "hover": Color(hover_fg) if hover_fg is not None else None,
                "active": Color(active_fg) if active_fg is not None else None,
            },
            Clickable.State.DISABLED: {
                "normal": Color(disabled_fg),
                "hover": Color(disabled_hover_fg) if disabled_hover_fg is not None else None,
                "active": Color(disabled_active_fg) if disabled_active_fg is not None else None,
            },
        }
        self.__text_align_x: Button.HorizontalAlign = Button.HorizontalAlign(text_align_x)
        self.__text_align_y: Button.VerticalAlign = Button.VerticalAlign(text_align_y)
        self.__text_offset: Tuple[float, float] = text_offset
        self.__text_hover_offset: Tuple[float, float] = text_hover_offset
        self.__text_active_offset: Tuple[float, float] = text_active_offset

    def copy(self) -> Button:
        return Button(
            master=self.scene if self.scene is not None else self.master,
            text=self.__text.message,
            font=self.__text.font,
            wrap=self.__text.wrap,
            justify=self.__text.justify,
            shadow_x=self.__text.shadow_x,
            shadow_y=self.__text.shadow_y,
            shadow_color=self.__text.shadow_color,
            callback=self.__callback,
            state=self.state,
            width=self.__fixed_width,
            height=self.__fixed_height,
            x_add_size=self.__x_add_size,
            y_add_size=self.__y_add_size,
            show_bg=self.__shape.is_shown(),
            bg=self.__bg[Clickable.State.NORMAL]["normal"],
            fg=self.__fg[Clickable.State.NORMAL]["normal"],
            outline=self.__shape.outline,
            outline_color=self.__shape.outline_color,
            hover_bg=self.__bg[Clickable.State.NORMAL]["hover"],
            hover_fg=self.__fg[Clickable.State.NORMAL]["hover"],
            hover_sound=self.hover_sound,
            active_bg=self.__bg[Clickable.State.NORMAL]["active"],
            active_fg=self.__fg[Clickable.State.NORMAL]["active"],
            on_click_sound=self.on_click_sound,
            disabled_bg=self.__bg[Clickable.State.DISABLED]["normal"],
            disabled_fg=self.__fg[Clickable.State.DISABLED]["normal"],
            disabled_sound=self.disabled_sound,
            disabled_hover_bg=self.__bg[Clickable.State.DISABLED]["hover"],
            disabled_hover_fg=self.__fg[Clickable.State.DISABLED]["hover"],
            disabled_active_bg=self.__bg[Clickable.State.DISABLED]["active"],
            disabled_active_fg=self.__fg[Clickable.State.DISABLED]["active"],
            text_align_x=self.__text_align_x,
            text_align_y=self.__text_align_y,
            text_offset=self.__text_offset,
            text_hover_offset=self.__text_hover_offset,
            text_active_offset=self.__text_active_offset,
            border_radius=self.__shape.border_radius,
            border_top_left_radius=self.__shape.border_top_left_radius,
            border_top_right_radius=self.__shape.border_top_right_radius,
            border_bottom_left_radius=self.__shape.border_bottom_left_radius,
            border_bottom_right_radius=self.__shape.border_bottom_right_radius,
            theme=NoTheme,
        )

    def draw_onto(self, surface: Surface) -> None:
        text_align_x: str = Button.__HORIZONTAL_ALIGN_POS[self.__text_align_x]
        text_align_y: str = Button.__VERTICAL_ALIGN_POS[self.__text_align_y]
        self.__shape.center = self.center
        self.__text.set_position(
            **{
                text_align_x: getattr(self.__shape, text_align_x),
                text_align_y: getattr(self.__shape, text_align_y),
            }
        )
        self.__text.translate(self.__text_offset)
        if self.state != Clickable.State.DISABLED:
            if self.active:
                self.__text.translate(self.__text_active_offset)
            elif self.hover:
                self.__text.translate(self.__text_hover_offset)
        self.__shape.draw_onto(surface)
        self.__text.draw_onto(surface)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> Tuple[float, float]:
        return self.__shape.get_size()

    def invoke(self) -> None:
        if callable(self.__callback):
            self.__callback()

    def set_text_font(
        self,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> None:
        self.__text.set_font(font, bold, italic, underline)
        self.__update_shape_size()

    def set_text_custom_line_font(self, index: int, font: Font) -> None:
        self.__text.set_custom_line_font(index, font)
        self.__update_shape_size()

    def remove_text_custom_line_font(self, index: int) -> None:
        self.__text.remove_custom_line_font(index)
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

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        return truth(self.rect.collidepoint(mouse_pos))

    def _on_hover(self) -> None:
        self.__set_color("hover")

    def _on_leave(self) -> None:
        self.__set_color("normal")

    def _on_active_set(self) -> None:
        self.__set_color("active")

    def __set_color(self, button_state: Union[Literal["normal"], Literal["hover"], Literal["active"]]) -> None:
        clickable_state: Clickable.State = Clickable.State(self.state)
        bg_color: Optional[Color] = self.__bg[clickable_state][button_state]
        if bg_color is None:
            bg_color = self.__bg[clickable_state]["normal"]
        fg_color: Optional[Color] = self.__fg[clickable_state][button_state]
        if fg_color is None:
            fg_color = self.__fg[clickable_state]["normal"]
        self.__shape.color = bg_color
        self.__text.color = fg_color

    def __update_colors(self) -> None:
        if self.active:
            self.__set_color("active")
        elif self.hover:
            self.__set_color("hover")
        else:
            self.__set_color("normal")

    def __update_shape_size(self) -> None:
        center = self.center
        self.__shape.local_size = (
            self.__text.width + self.__x_add_size if self.__fixed_width is None else self.__fixed_width,
            self.__text.height + self.__y_add_size if self.__fixed_height is None else self.__fixed_height,
        )
        self.center = center

    @property
    def text(self) -> str:
        return self.__text.message

    @text.setter
    def text(self, string: str) -> None:
        self.__text.message = string
        self.__update_shape_size()

    @property
    def text_font(self) -> Font:
        return self.__text.font

    @text_font.setter
    def text_font(self, font: Font) -> None:
        self.set_text_font(font)

    @property
    def text_justify(self) -> str:
        return self.__text.justify

    @text_justify.setter
    def text_justify(self, justify: str) -> None:
        self.__text.justify = justify
        self.__update_shape_size()

    @property
    def text_wrap(self) -> int:
        return self.__text.wrap

    @text_wrap.setter
    def text_wrap(self, value: int) -> None:
        self.__text.wrap = value
        self.__update_shape_size()

    @property
    def text_shadow(self) -> Tuple[float, float]:
        return self.__text.shadow

    @text_shadow.setter
    def text_shadow(self, shadow: Tuple[float, float]) -> None:
        self.__text.shadow = shadow
        self.__update_shape_size()

    @property
    def text_shadow_x(self) -> float:
        return self.__text.shadow_x

    @text_shadow_x.setter
    def text_shadow_x(self, shadow: float) -> None:
        self.__text.shadow_x = shadow
        self.__update_shape_size()

    @property
    def text_shadow_y(self) -> float:
        return self.__text.shadow_y

    @text_shadow_y.setter
    def text_shadow_y(self, shadow: float) -> None:
        self.__text.shadow_y = shadow
        self.__update_shape_size()

    @property
    def text_shadow_color(self) -> Color:
        return self.__text.shadow_color

    @text_shadow_color.setter
    def text_shadow_color(self, color: Color) -> None:
        self.__text.shadow_color = color

    @property
    def callback(self) -> Optional[_ButtonCallback]:
        return self.__callback

    @callback.setter
    def callback(self, callback: Optional[_ButtonCallback]) -> None:
        if callable(callback):
            self.__callback = callback
        else:
            self.__callback = None

    @property
    def fixed_width(self) -> Optional[float]:
        return self.__fixed_width

    @fixed_width.setter
    def fixed_width(self, width: Optional[float]) -> None:
        if width == self.__fixed_width:
            return
        if width is None:
            self.__fixed_width = None
        else:
            self.__fixed_width = max(float(width), 0)
        self.__update_shape_size()

    @property
    def fixed_height(self) -> Optional[float]:
        return self.__fixed_height

    @fixed_height.setter
    def fixed_height(self, height: Optional[float]) -> None:
        if height == self.__fixed_height:
            return
        if height is None:
            self.__fixed_height = None
        else:
            self.__fixed_height = max(float(height), 0)
        self.__update_shape_size()

    @property
    def x_add_size(self) -> float:
        return self.__x_add_size

    @x_add_size.setter
    def x_add_size(self, offset: float) -> None:
        offset = max(offset, 0)
        if offset != self.__x_add_size:
            self.__x_add_size = offset
            self.__update_shape_size()

    @property
    def y_add_size(self) -> float:
        return self.__y_add_size

    @y_add_size.setter
    def y_add_size(self, offset: float) -> None:
        offset = max(offset, 0)
        if offset != self.__y_add_size:
            self.__y_add_size = offset
            self.__update_shape_size()

    @property
    def background(self) -> Color:
        return Color(self.__bg[Clickable.State.NORMAL]["normal"])

    @background.setter
    def background(self, color: Color) -> None:
        self.__bg[Clickable.State.NORMAL]["normal"] = Color(color)
        self.__update_colors()

    @property
    def bg(self) -> Color:
        return self.background

    @bg.setter
    def bg(self, color: Color) -> None:
        self.background = color

    @property
    def foreground(self) -> Color:
        return Color(self.__fg[Clickable.State.NORMAL]["normal"])

    @foreground.setter
    def foreground(self, color: Color) -> None:
        self.__fg[Clickable.State.NORMAL]["normal"] = Color(color)
        self.__update_colors()

    @property
    def fg(self) -> Color:
        return self.foreground

    @fg.setter
    def fg(self, color: Color) -> None:
        self.foreground = color

    @property
    def outline(self) -> int:
        return self.__shape.outline

    @outline.setter
    def outline(self, outline: int) -> None:
        self.__shape.outline = outline

    @property
    def outline_color(self) -> Color:
        return self.__shape.outline_color

    @outline_color.setter
    def outline_color(self, color: Color) -> None:
        self.__shape.outline_color = color

    @property
    def hover_background(self) -> Optional[Color]:
        c: Optional[Color] = self.__bg[Clickable.State.NORMAL]["hover"]
        return Color(c) if c is not None else None

    @hover_background.setter
    def hover_background(self, color: Optional[Color]) -> None:
        self.__bg[Clickable.State.NORMAL]["hover"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def hover_bg(self) -> Optional[Color]:
        return self.hover_background

    @hover_bg.setter
    def hover_bg(self, color: Optional[Color]) -> None:
        self.hover_background = color

    @property
    def hover_foreground(self) -> Optional[Color]:
        c: Optional[Color] = self.__fg[Clickable.State.NORMAL]["hover"]
        return Color(c) if c is not None else None

    @hover_foreground.setter
    def hover_foreground(self, color: Optional[Color]) -> None:
        self.__fg[Clickable.State.NORMAL]["hover"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def hover_fg(self) -> Optional[Color]:
        return self.hover_foreground

    @hover_fg.setter
    def hover_fg(self, color: Optional[Color]) -> None:
        self.hover_foreground = color

    @property
    def active_background(self) -> Optional[Color]:
        c: Optional[Color] = self.__bg[Clickable.State.NORMAL]["active"]
        return Color(c) if c is not None else None

    @active_background.setter
    def active_background(self, color: Optional[Color]) -> None:
        self.__bg[Clickable.State.NORMAL]["active"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def active_bg(self) -> Optional[Color]:
        return self.active_background

    @active_bg.setter
    def active_bg(self, color: Optional[Color]) -> None:
        self.active_background = color

    @property
    def active_foreground(self) -> Optional[Color]:
        c: Optional[Color] = self.__fg[Clickable.State.NORMAL]["active"]
        return Color(c) if c is not None else None

    @active_foreground.setter
    def active_foreground(self, color: Optional[Color]) -> None:
        self.__fg[Clickable.State.NORMAL]["active"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def active_fg(self) -> Optional[Color]:
        return self.active_foreground

    @active_fg.setter
    def active_fg(self, color: Optional[Color]) -> None:
        self.active_foreground = color

    @property
    def disabled_background(self) -> Color:
        return Color(self.__bg[Clickable.State.DISABLED]["normal"])

    @disabled_background.setter
    def disabled_background(self, color: Color) -> None:
        self.__bg[Clickable.State.DISABLED]["normal"] = Color(color)
        self.__update_colors()

    @property
    def disabled_bg(self) -> Color:
        return self.disabled_background

    @disabled_bg.setter
    def disabled_bg(self, color: Color) -> None:
        self.disabled_background = color

    @property
    def disabled_foreground(self) -> Color:
        return Color(self.__fg[Clickable.State.DISABLED]["normal"])

    @disabled_foreground.setter
    def disabled_foreground(self, color: Color) -> None:
        self.__fg[Clickable.State.DISABLED]["normal"] = Color(color)
        self.__update_colors()

    @property
    def disabled_fg(self) -> Color:
        return self.disabled_foreground

    @disabled_fg.setter
    def disabled_fg(self, color: Color) -> None:
        self.disabled_foreground = color

    @property
    def disabled_hover_background(self) -> Optional[Color]:
        c: Optional[Color] = self.__bg[Clickable.State.DISABLED]["hover"]
        return Color(c) if c is not None else None

    @disabled_hover_background.setter
    def disabled_hover_background(self, color: Optional[Color]) -> None:
        self.__bg[Clickable.State.DISABLED]["hover"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def disabled_hover_bg(self) -> Optional[Color]:
        return self.disabled_hover_background

    @disabled_hover_bg.setter
    def disabled_hover_bg(self, color: Optional[Color]) -> None:
        self.disabled_hover_background = color

    @property
    def disabled_hover_foreground(self) -> Optional[Color]:
        c: Optional[Color] = self.__fg[Clickable.State.DISABLED]["hover"]
        return Color(c) if c is not None else None

    @disabled_hover_foreground.setter
    def disabled_hover_foreground(self, color: Optional[Color]) -> None:
        self.__fg[Clickable.State.DISABLED]["hover"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def disabled_hover_fg(self) -> Optional[Color]:
        return self.disabled_hover_foreground

    @disabled_hover_fg.setter
    def disabled_hover_fg(self, color: Optional[Color]) -> None:
        self.disabled_hover_foreground = color

    @property
    def disabled_active_background(self) -> Optional[Color]:
        c: Optional[Color] = self.__bg[Clickable.State.DISABLED]["active"]
        return Color(c) if c is not None else None

    @disabled_active_background.setter
    def disabled_active_background(self, color: Optional[Color]) -> None:
        self.__bg[Clickable.State.DISABLED]["active"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def disabled_active_bg(self) -> Optional[Color]:
        return self.disabled_active_background

    @disabled_active_bg.setter
    def disabled_active_bg(self, color: Optional[Color]) -> None:
        self.disabled_active_background = color

    @property
    def disabled_active_foreground(self) -> Optional[Color]:
        c: Optional[Color] = self.__fg[Clickable.State.DISABLED]["active"]
        return Color(c) if c is not None else None

    @disabled_active_foreground.setter
    def disabled_active_foreground(self, color: Optional[Color]) -> None:
        self.__fg[Clickable.State.DISABLED]["active"] = Color(color) if color is not None else None
        self.__update_colors()

    @property
    def disabled_active_fg(self) -> Optional[Color]:
        return self.disabled_active_foreground

    @disabled_active_fg.setter
    def disabled_active_fg(self, color: Optional[Color]) -> None:
        self.disabled_active_foreground = color

    @property
    def text_align_x(self) -> str:
        return str(self.__text_align_x.value)

    @text_align_x.setter
    def text_align_x(self, align: str) -> None:
        self.__text_align_x = Button.HorizontalAlign(align)

    @property
    def text_align_y(self) -> str:
        return str(self.__text_align_y.value)

    @text_align_y.setter
    def text_align_y(self, align: str) -> None:
        self.__text_align_y = Button.VerticalAlign(align)

    @property
    def text_offset(self) -> Tuple[float, float]:
        return self.__text_offset

    @text_offset.setter
    def text_offset(self, offset: Tuple[float, float]) -> None:
        self.__text_offset = offset[0], offset[1]

    @property
    def text_hover_offset(self) -> Tuple[float, float]:
        return self.__text_hover_offset

    @text_hover_offset.setter
    def text_hover_offset(self, offset: Tuple[float, float]) -> None:
        self.__text_hover_offset = offset[0], offset[1]

    @property
    def text_active_offset(self) -> Tuple[float, float]:
        return self.__text_active_offset

    @text_active_offset.setter
    def text_active_offset(self, offset: Tuple[float, float]) -> None:
        self.__text_active_offset = offset[0], offset[1]

    @property
    def border_radius(self) -> int:
        return self.__shape.border_radius

    @border_radius.setter
    def border_radius(self, radius: int) -> None:
        self.__shape.border_radius = radius

    @property
    def border_top_left_radius(self) -> int:
        return self.__shape.border_top_left_radius

    @border_top_left_radius.setter
    def border_top_left_radius(self, radius: int) -> None:
        self.__shape.border_top_left_radius = radius

    @property
    def border_top_right_radius(self) -> int:
        return self.__shape.border_top_right_radius

    @border_top_right_radius.setter
    def border_top_right_radius(self, radius: int) -> None:
        self.__shape.border_top_right_radius = radius

    @property
    def border_bottom_left_radius(self) -> int:
        return self.__shape.border_bottom_left_radius

    @border_bottom_left_radius.setter
    def border_bottom_left_radius(self, radius: int) -> None:
        self.__shape.border_bottom_left_radius = radius

    @property
    def border_bottom_right_radius(self) -> int:
        return self.__shape.border_bottom_right_radius

    @border_bottom_right_radius.setter
    def border_bottom_right_radius(self, radius: int) -> None:
        self.__shape.border_bottom_right_radius = radius
