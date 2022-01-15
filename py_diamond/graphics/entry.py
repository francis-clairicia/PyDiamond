# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Entry module"""

from __future__ import annotations

__all__ = ["Entry", "MetaEntry"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from functools import cached_property
from string import printable as ASCII_PRINTABLE
from typing import TYPE_CHECKING, Any, Callable, Optional, Tuple, TypeAlias

from ..system.configuration import Configuration, OptionAttribute, initializer
from ..system.utils import valid_integer, valid_optional_float, valid_optional_integer
from ..window.clock import Clock
from ..window.cursor import SystemCursor
from ..window.event import KeyDownEvent, TextInputEvent
from ..window.gui import BoundFocus
from ..window.keyboard import Keyboard
from ..window.pressable import Pressable
from .color import BLACK, BLUE, TRANSPARENT, WHITE, Color
from .drawable import MetaTDrawable, TDrawable
from .shape import RectangleShape
from .surface import Surface
from .text import Text
from .theme import MetaThemedObject, NoTheme, ThemeType

if TYPE_CHECKING:
    from ..audio.sound import Sound
    from ..window.display import Window
    from ..window.scene import Scene
    from .font import Font
    from .renderer import Renderer

    _TextFont: TypeAlias = Font | Tuple[Optional[str], int]


class MetaEntry(MetaTDrawable, MetaThemedObject):
    pass


@Text.register_themed_subclass
@RectangleShape.register_themed_subclass
class Entry(TDrawable, Pressable, metaclass=MetaEntry):
    config: Configuration = Configuration(
        "cursor",
        "interval",
        "bg",
        "fg",
        "font",
        "shadow_x",
        "shadow_y",
        "shadow",
        "shadow_color",
        "fixed_width",
        "local_width",
        "local_height",
        "local_size",
        "outline",
        "outline_color",
        "highlight_color",
        "highlight_thickness",
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
    )

    cursor: OptionAttribute[int] = OptionAttribute()
    interval: OptionAttribute[int] = OptionAttribute()
    bg: OptionAttribute[Color] = OptionAttribute()
    fg: OptionAttribute[Color] = OptionAttribute()

    font: OptionAttribute[Font] = OptionAttribute()
    shadow_x: OptionAttribute[float] = OptionAttribute()
    shadow_y: OptionAttribute[float] = OptionAttribute()
    shadow: OptionAttribute[Tuple[float, float]] = OptionAttribute()
    shadow_color: OptionAttribute[Color] = OptionAttribute()

    fixed_width: OptionAttribute[Optional[float]] = OptionAttribute()
    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[Tuple[float, float]] = OptionAttribute()

    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    highlight_color: OptionAttribute[Color] = OptionAttribute()
    highlight_thickness: OptionAttribute[int] = OptionAttribute()

    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: Scene | Window,
        on_validate: Optional[Callable[[], Any]] = None,
        *,
        max_nb_chars: int = 10,
        width: Optional[float] = None,
        font: Optional[_TextFont] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        bg: Color = WHITE,
        fg: Color = BLACK,
        outline: int = 2,
        outline_color: Color = BLACK,
        interval: int = 500,
        state: str = "normal",
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        hover_sound: Optional[Sound] = None,
        click_sound: Optional[Sound] = None,
        disabled_sound: Optional[Sound] = None,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: Optional[ThemeType] = None,
    ):
        TDrawable.__init__(self)
        self.__text: _TextEntry = _TextEntry(
            font=font,
            bold=bold,
            italic=italic,
            underline=underline,
            color=fg,
            shadow_x=shadow_x,
            shadow_y=shadow_y,
            shadow_color=shadow_color,
            theme=NoTheme,
        )
        max_nb_chars = max(int(max_nb_chars), 0)
        width = max(float(width), 0) if width is not None else None
        self.__on_validate: Callable[[], None] = on_validate if callable(on_validate) else lambda: None
        self.__nb_chars: int = max_nb_chars
        self.__fixed_width: Optional[float] = width
        self.__cursor_width_offset: float = 15
        self.__cursor_height_offset: float = 10
        height: float
        entry_size: Tuple[int, int] = _get_entry_size(self.__text.font, max_nb_chars or 10)
        if width is None:
            width = entry_size[0] + self.__cursor_width_offset
        height = entry_size[1] + self.__cursor_height_offset
        self.__shape: RectangleShape = RectangleShape(
            width=width,
            height=height,
            color=bg,
            outline=0,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=NoTheme,
        )
        self.__outline_shape: RectangleShape = RectangleShape(
            width=width,
            height=height,
            color=TRANSPARENT,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=NoTheme,
        )
        self.outline = outline
        self.outline_color = outline_color
        self.highlight_color = highlight_color
        self.highlight_thickness = highlight_thickness
        Pressable.__init__(
            self,
            master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=SystemCursor.IBEAM,
        )
        self.interval = interval

        self.__cursor: int = 0
        self.__show_cursor: bool = False
        self.__start_edit: bool = False
        self.__cursor_animation_clock = Clock()

        key_press_event = self.__key_press
        master.event.bind_event(KeyDownEvent, key_press_event)
        master.event.bind_event(TextInputEvent, key_press_event)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def draw_onto(self, target: Renderer) -> None:
        shape: RectangleShape = self.__shape
        outline_shape: RectangleShape = self.__outline_shape
        text: Text = self.__text
        cursor: int = self.__cursor

        outline_shape.center = shape.center = self.center
        shape.draw_onto(target)

        text.midleft = (self.left + self.__cursor_width_offset, self.centery)
        text.draw_onto(target)

        show_cursor: bool = self.__show_cursor
        if self.__edit():
            if self.__cursor_animation_clock.elapsed_time(self.interval):
                self.__show_cursor = show_cursor = not show_cursor
        else:
            self.__show_cursor = show_cursor = False
        if show_cursor:
            width: float = text.font.size(text.message[:cursor])[0] + 1
            height: float = self.height - self.__cursor_height_offset
            cursor_start: Tuple[float, float] = (text.left + width, text.centery - height // 2)
            cursor_end: Tuple[float, float] = (text.left + width, text.centery + height // 2)
            target.draw_line(text.color, cursor_start, cursor_end, width=2)

        outline_shape.draw_onto(target)

    def get(self) -> str:
        return self.__text.message

    def clear(self) -> None:
        self.__text.message = str()

    def start_edit(self) -> None:
        Keyboard.IME.start_text_input()
        self.__start_edit = True
        self.__show_cursor = True

    def stop_edit(self) -> None:
        Keyboard.IME.stop_text_input()
        self.__start_edit = False

    def invoke(self) -> None:
        if self.focus.get_mode() == BoundFocus.Mode.MOUSE:
            self.start_edit()
        else:
            on_validate: Callable[[], None] = self.__on_validate
            on_validate()

    def _on_focus_set(self) -> None:
        self.start_edit()
        self.__update_shape_outline()

    def _on_focus_leave(self) -> None:
        self.stop_edit()
        self.__update_shape_outline()

    def _mouse_in_hitbox(self, mouse_pos: Tuple[float, float]) -> bool:
        return self.__shape.rect.collidepoint(mouse_pos)

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        scale: float = self.scale
        self.__outline_shape.scale = self.__shape.scale = self.__text.scale = scale
        self.__cursor_width_offset = 15 * scale
        self.__cursor_height_offset = 10 * scale

    def __edit(self) -> bool:
        if not self.__start_edit:
            return False
        if self.focus.get_mode() == BoundFocus.Mode.KEY:
            if self.focus.has():
                Keyboard.IME.start_text_input()
            else:
                Keyboard.IME.stop_text_input()
        return Keyboard.IME.text_input_enabled()

    def __key_press(self, event: KeyDownEvent | TextInputEvent) -> bool:
        if not self.__edit() or not isinstance(event, (KeyDownEvent, TextInputEvent)):
            return False
        self.__show_cursor = True
        self.__cursor_animation_clock.restart()
        text: Text = self.__text
        max_nb_char: int = self.__nb_chars
        if isinstance(event, KeyDownEvent):
            if event.key == Keyboard.Key.ESCAPE:
                self.stop_edit()
                return True
            if event.key == Keyboard.Key.BACKSPACE:
                if self.cursor > 0:
                    text.message = text.message[: self.cursor - 1] + text.message[self.cursor :]
                    self.cursor -= 1
                return True
            if event.key == Keyboard.Key.DELETE:
                text.message = text.message[: self.cursor] + text.message[self.cursor + 1 :]
                return True
            if event.key == Keyboard.Key.LEFT:
                self.cursor -= 1
                return True
            if event.key == Keyboard.Key.RIGHT:
                self.cursor += 1
                return True
            if event.key == Keyboard.Key.HOME:
                self.cursor = 0
                return True
            if event.key == Keyboard.Key.END:
                self.cursor = len(text.message)
                return True
            return False

        entered_text: str = event.text
        new_text: str = text.message[: self.cursor] + entered_text + text.message[self.cursor :]
        if max_nb_char == 0 or len(new_text) <= max_nb_char:
            text.message = new_text
            self.cursor += len(entered_text)
        return True

    def __update_shape_outline(self) -> None:
        shape: RectangleShape = self.__outline_shape
        outline: int
        outline_color: Color
        if self.focus.has():
            outline_color = self.highlight_color
            outline = max(self.highlight_thickness, self.outline)
        else:
            outline_color = self.outline_color
            outline = self.outline
        shape.config(outline=outline, outline_color=outline_color)

    @config.value_converter("cursor")
    def __cursor_validator(self, cursor: Any) -> int:
        return valid_integer(value=cursor, min_value=0, max_value=len(self.get()))

    config.value_converter_static("interval", valid_integer(min_value=0))
    config.value_converter_static("fixed_width", valid_optional_float(min_value=0))

    @config.getter_key("fg", use_key="color")
    @config.getter_key("font")
    @config.getter_key("shadow_x")
    @config.getter_key("shadow_y")
    @config.getter_key("shadow")
    @config.getter_key("shadow_color")
    def __get_text_option(self, option: str) -> Any:
        return self.__text.config.get(option)

    @config.setter_key("fg", use_key="color")
    @config.setter_key("font")
    @config.setter_key("shadow_x")
    @config.setter_key("shadow_y")
    @config.setter_key("shadow")
    @config.setter_key("shadow_color")
    def __set_text_option(self, option: str, value: Any) -> None:
        return self.__text.config.set(option, value)

    @config.getter_key("bg", use_key="color")
    @config.getter_key("local_width")
    @config.getter_key("local_height")
    @config.getter_key("local_size")
    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_key("bg", use_key="color")
    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> None:
        self.__shape.config.set(option, value)
        if option != "color":
            self.__outline_shape.config.set(option, value)

    config.readonly("local_width", "local_height", "local_size")

    @config.on_update("font")
    @config.on_update("fixed_width")
    def __update_shape_using_font(self) -> None:
        max_nb_chars: int = self.__nb_chars
        fixed_width: Optional[float] = self.__fixed_width
        entry_size: Tuple[int, int] = _get_entry_size(self.__text.font, max_nb_chars or 10)
        width: float
        if fixed_width is not None:
            width = fixed_width
        else:
            width = entry_size[0] + self.__cursor_width_offset
        height: float = entry_size[1] + self.__cursor_height_offset
        self.__outline_shape.local_size = self.__shape.local_size = (width, height)

    config.value_converter_static("outline", valid_integer(min_value=0))
    config.value_validator_static("outline_color", Color)
    config.value_validator_static("highlight_color", Color)
    config.value_converter_static("highlight_thickness", valid_integer(min_value=0))

    config.on_update("outline", __update_shape_outline)
    config.on_update("outline_color", __update_shape_outline)
    config.on_update("highlight_color", __update_shape_outline)
    config.on_update("highlight_thickness", __update_shape_outline)

    @cached_property
    def focus(self) -> BoundFocus:
        return BoundFocus(self, self.scene)


def _get_entry_size(font: Font, nb_chars: int) -> Tuple[int, int]:
    return font.size(max(ASCII_PRINTABLE, key=lambda char: font.size(char)) * nb_chars)


class _TextEntry(Text):
    @initializer
    def __init__(
        self,
        message: str = "",
        *,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        color: Color,
        shadow_x: float,
        shadow_y: float,
        shadow_color: Color,
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(
            message=message,
            font=font,
            bold=bold,
            italic=italic,
            underline=underline,
            color=color,
            shadow_x=shadow_x,
            shadow_y=shadow_y,
            shadow_color=shadow_color,
            theme=theme,
        )
        self.max_width = None

    def _render(self) -> Surface:
        # max_width: Optional[int] = self.max_width
        text: Surface = super()._render()
        # if max_width is not None:
        #     return text.subsurface(0, 0, max_width, text.get_height()).copy()
        return text

    config = Configuration("max_width", parent=Text.config)

    config.value_converter_static("max_width", valid_optional_integer(min_value=0))

    max_width: OptionAttribute[Optional[int]] = OptionAttribute()
