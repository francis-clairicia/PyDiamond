# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Callable, Dict, Literal, Optional, Tuple, TypedDict, Union
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

_ClickableCallback = Callable[[], None]
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
        callback: Optional[_ClickableCallback] = None,
        state: str = "normal",
        # size=None,
        # x_size=None,
        # y_size=None,
        x_add_size: float = 20,
        y_add_size: float = 20,
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
            callback=callback,
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
        self.__x_add_size: float = max(float(x_add_size), 0)
        self.__y_add_size: float = max(float(y_add_size), 0)
        self.__shape: RectangleShape = RectangleShape(
            width=self.__text.width + self.__x_add_size,
            height=self.__text.height + self.__y_add_size,
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
        self.__bg: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {"normal": bg, "hover": hover_bg, "active": active_bg},
            Clickable.State.DISABLED: {"normal": disabled_bg, "hover": disabled_hover_bg, "active": disabled_active_bg},
        }
        self.__fg: Dict[Clickable.State, _ButtonColor] = {
            Clickable.State.NORMAL: {"normal": fg, "hover": hover_fg, "active": active_fg},
            Clickable.State.DISABLED: {"normal": disabled_fg, "hover": disabled_hover_fg, "active": disabled_active_fg},
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
            callback=self.callback,
            state=self.state,
            x_add_size=self.__x_add_size,
            y_add_size=self.__y_add_size,
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

    def __update_size(self) -> None:
        center = self.center
        self.__shape.local_size = (self.__text.width + self.__x_add_size, self.__text.height + self.__y_add_size)
        self.center = center

    @property
    def text(self) -> str:
        return self.__text.message

    @text.setter
    def text(self, string: str) -> None:
        self.__text.message = string
        self.__update_size()
