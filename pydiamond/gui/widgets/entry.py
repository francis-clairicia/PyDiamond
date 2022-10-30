# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Entry module"""

from __future__ import annotations

__all__ = ["Entry"]

from string import printable as ASCII_PRINTABLE
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Literal, Sequence
from weakref import WeakMethod

from ...graphics.color import BLACK, BLUE, TRANSPARENT, WHITE, Color
from ...graphics.font import Font, FontFactory
from ...graphics.shape import RectangleShape
from ...system.clock import Clock
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.theme import ThemedObjectMeta, ThemeType
from ...system.validation import valid_integer, valid_optional_float
from ...window.cursor import Cursor, SystemCursor
from ...window.event import KeyDownEvent, MouseButtonDownEvent, TextInputEvent
from ...window.keyboard import Key, Keyboard
from ..scene import FocusMode
from .abc import AbstractWidget, Widget, WidgetsManager

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...graphics.font import _TextFont
    from ...graphics.renderer import AbstractRenderer


class Entry(Widget, metaclass=ThemedObjectMeta):
    __theme_ignore__: ClassVar[Sequence[str]] = ("on_validate",)

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "cursor",
        "interval",
        "background_color",
        "foreground_color",
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
        parent=Widget.config,
    )
    config.set_alias("background_color", "bg")
    config.set_alias("foreground_color", "fg")

    cursor: OptionAttribute[int] = OptionAttribute()
    interval: OptionAttribute[int] = OptionAttribute()
    bg: OptionAttribute[Color] = OptionAttribute()
    fg: OptionAttribute[Color] = OptionAttribute()

    shadow_x: OptionAttribute[float] = OptionAttribute()
    shadow_y: OptionAttribute[float] = OptionAttribute()
    shadow: OptionAttribute[tuple[float, float]] = OptionAttribute()
    shadow_color: OptionAttribute[Color] = OptionAttribute()

    fixed_width: OptionAttribute[float | None] = OptionAttribute()
    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()

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
        master: AbstractWidget | WidgetsManager,
        *,
        on_validate: Callable[[], Any] | None = None,
        max_nb_chars: int = 10,
        width: float | None = None,
        font: _TextFont | None = None,
        bg: Color = WHITE,
        fg: Color = BLACK,
        outline: int = 2,
        outline_color: Color = BLACK,
        interval: int = 500,
        state: str = "normal",
        highlight_color: Color = BLUE,
        highlight_thickness: int = 2,
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = SystemCursor.IBEAM,
        disabled_cursor: Cursor | None = None,
        take_focus: bool | Literal["never"] = True,
        focus_on_hover: bool | None = None,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ):
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
        self.fg = fg
        self.__text: str = ""
        self.__font: Font = FontFactory.create_font(font)
        max_nb_chars = max(int(max_nb_chars), 0)
        width = max(float(width), 0) if width is not None else None
        self.__on_validate: Callable[[], None] = on_validate if callable(on_validate) else lambda: None
        self.__nb_chars: int = max_nb_chars
        self.__fixed_width: float | None = width
        self.__cursor_width_offset: float = 15
        self.__cursor_height_offset: float = 10
        height: float
        entry_size: tuple[int, int] = _get_entry_size(self.__font, max_nb_chars or 10)
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
        )
        self.outline = outline
        self.outline_color = outline_color
        self.highlight_color = highlight_color
        self.highlight_thickness = highlight_thickness
        self.interval = interval

        self.__cursor: int = 0
        self.__show_cursor: bool = False
        self.__start_edit: bool = False
        self.__insert_mode: bool = False
        self.__cursor_animation_clock = Clock()

        self.event.bind(KeyDownEvent, WeakMethod(self.__key_press))
        self.event.bind(TextInputEvent, WeakMethod(self.__key_press))

    def get_size(self) -> tuple[float, float]:
        return self.__shape.get_size()

    def draw_onto(self, target: AbstractRenderer) -> None:
        shape: RectangleShape = self.__shape
        outline_shape: RectangleShape = self.__outline_shape
        font: Font = self.__font
        text: str = self.__text
        cursor: int = self.__cursor

        outline_shape.center = shape.center = self.center
        shape.draw_onto(target)

        text_rect = font.get_rect(text, midleft=(self.left + self.__cursor_width_offset, self.centery))
        target.draw_text(text, font, text_rect, fgcolor=self.fg)

        show_cursor: bool
        if self.__edit():
            show_cursor = self.__show_cursor
            if self.__cursor_animation_clock.elapsed_time(self.interval):
                self.__show_cursor = show_cursor = not show_cursor
        else:
            self.__show_cursor = show_cursor = False
        if show_cursor:
            width: float = font.get_rect(text[:cursor]).width + 1
            height: float = self.height - self.__cursor_height_offset
            if not self.__insert_mode or self.cursor == len(text):
                cursor_start: tuple[float, float] = (text_rect.left + width, text_rect.centery - height // 2)
                cursor_end: tuple[float, float] = (text_rect.left + width, text_rect.centery + height // 2)
                target.draw_line(self.fg, cursor_start, cursor_end, width=2)
            else:
                char_rect = font.get_rect(text[cursor])
                char_rect.left = int(text_rect.left + width)
                char_rect.centery = int(text_rect.centery)
                target.draw_rect(self.fg, char_rect)

        outline_shape.draw_onto(target)

    def get(self) -> str:
        return self.__text

    def clear(self) -> None:
        self.__text = ""

    def start_edit(self) -> None:
        Keyboard.IME.start_text_input()
        self.__start_edit = True
        self.__show_cursor = True

    def stop_edit(self) -> None:
        Keyboard.IME.stop_text_input()
        self.__start_edit = False

    def invoke(self) -> None:
        if self.focus.get_mode() in {FocusMode.MOUSE, FocusMode.NONE}:
            self.start_edit()

    def _on_click_out(self, event: MouseButtonDownEvent) -> None:
        super()._on_click_out(event)
        if self.focus.get_mode() == FocusMode.NONE:
            self.stop_edit()

    def _on_focus_set(self) -> None:
        self.start_edit()
        self.__update_shape_outline()

    def _on_focus_leave(self) -> None:
        self.stop_edit()
        self.__update_shape_outline()

    def __edit(self) -> bool:
        if not self.__start_edit:
            return False
        if self.focus.get_mode() == FocusMode.KEY:
            if self.focus.has():
                Keyboard.IME.start_text_input()
            else:
                Keyboard.IME.stop_text_input()
        return Keyboard.IME.text_input_enabled()

    def __key_press(self, event: KeyDownEvent | TextInputEvent) -> bool:
        if not self.__edit():
            return False
        self.__show_cursor = True
        self.__cursor_animation_clock.restart()
        text: str = self.__text
        match event:
            case KeyDownEvent(key=Key.K_RETURN | Key.K_KP_ENTER) if text:
                self.__on_validate()
                return True
            case KeyDownEvent(key=Key.K_INSERT):
                self.__insert_mode = not self.__insert_mode
                return True
            case KeyDownEvent(key=Key.K_ESCAPE):
                self.stop_edit()
                return True
            case KeyDownEvent(key=Key.K_BACKSPACE):
                if self.cursor > 0:
                    self.__text = text[: self.cursor - 1] + text[self.cursor :]
                    self.cursor -= 1
                return True
            case KeyDownEvent(key=Key.K_DELETE):
                self.__text = text[: self.cursor] + text[self.cursor + 1 :]
                return True
            case KeyDownEvent(key=Key.K_LEFT):
                self.cursor -= 1
                return True
            case KeyDownEvent(key=Key.K_RIGHT):
                self.cursor += 1
                return True
            case KeyDownEvent(key=Key.K_HOME):
                self.cursor = 0
                return True
            case KeyDownEvent(key=Key.K_END):
                self.cursor = len(text)
                return True
            case TextInputEvent(text=entered_text):
                new_text: str
                if not self.__insert_mode:
                    new_text = text[: self.cursor] + entered_text + text[self.cursor :]
                else:
                    new_text = text[: self.cursor] + entered_text + text[self.cursor + len(entered_text) :]
                if (max_nb_char := self.__nb_chars) == 0 or len(new_text) <= max_nb_char:
                    self.__text = new_text
                    self.cursor += len(entered_text)
                return True
        return False

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
        shape.config.update(outline=outline, outline_color=outline_color)

    @config.add_value_converter_on_set("cursor")
    def __cursor_validator(self, cursor: Any) -> int:
        return valid_integer(value=cursor, min_value=0, max_value=len(self.get()))

    config.add_value_converter_on_set_static("interval", valid_integer(min_value=0))
    config.add_value_converter_on_set_static("fixed_width", valid_optional_float(min_value=0))

    @config.getter_with_key("background_color", use_key="color")
    @config.getter_with_key("local_width", readonly=True)
    @config.getter_with_key("local_height", readonly=True)
    @config.getter_with_key("local_size", readonly=True)
    @config.getter_with_key("border_radius")
    @config.getter_with_key("border_top_left_radius")
    @config.getter_with_key("border_top_right_radius")
    @config.getter_with_key("border_bottom_left_radius")
    @config.getter_with_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_with_key("background_color", use_key="color")
    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> None:
        self.__shape.config.set(option, value)
        if option != "color":
            self.__outline_shape.config.set(option, value)

    @config.on_update("fixed_width")
    def __update_shape_using_font(self) -> None:
        max_nb_chars: int = self.__nb_chars
        fixed_width: float | None = self.__fixed_width
        entry_size: tuple[int, int] = _get_entry_size(self.__font, max_nb_chars or 10)
        width: float
        if fixed_width is not None:
            width = fixed_width
        else:
            width = entry_size[0] + self.__cursor_width_offset
        height: float = entry_size[1] + self.__cursor_height_offset
        self.__outline_shape.local_size = self.__shape.local_size = (width, height)

    config.add_value_converter_on_set_static("outline", valid_integer(min_value=0))
    config.add_value_validator_static("outline_color", Color)
    config.add_value_validator_static("highlight_color", Color)
    config.add_value_converter_on_set_static("highlight_thickness", valid_integer(min_value=0))

    config.on_update("outline", __update_shape_outline)
    config.on_update("outline_color", __update_shape_outline)
    config.on_update("highlight_color", __update_shape_outline)
    config.on_update("highlight_thickness", __update_shape_outline)


def _get_entry_size(font: Font, nb_chars: int) -> tuple[int, int]:
    return font.get_rect(max(ASCII_PRINTABLE, key=lambda char: font.get_rect(char).size) * nb_chars).size
