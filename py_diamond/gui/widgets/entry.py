# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Entry module"""

from __future__ import annotations

__all__ = ["Entry"]


from string import printable as ASCII_PRINTABLE
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Sequence, TypeAlias
from weakref import WeakMethod

from ...graphics.color import BLACK, BLUE, TRANSPARENT, WHITE, Color
from ...graphics.drawable import Drawable
from ...graphics.shape import RectangleShape
from ...graphics.surface import Surface
from ...graphics.text import Text
from ...graphics.transformable import Transformable
from ...system.clock import Clock
from ...system.configuration import Configuration, ConfigurationTemplate, OptionAttribute, initializer
from ...system.theme import NoTheme, ThemedObjectMeta, ThemeType
from ...system.validation import valid_integer, valid_optional_float, valid_optional_integer
from ...window.cursor import SystemCursor
from ...window.event import KeyDownEvent, TextInputEvent
from ...window.keyboard import Key, Keyboard
from ..focus import BoundFocusMode
from .abc import AbstractWidget

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...graphics.font import Font
    from ...graphics.renderer import AbstractRenderer
    from ...window.clickable import Clickable
    from ...window.display import Window
    from ...window.scene import Scene

    _TupleFont: TypeAlias = tuple[str | None, int]
    _TextFont: TypeAlias = Font | _TupleFont


@Text.register_themed_subclass
class Entry(Drawable, Transformable, AbstractWidget, metaclass=ThemedObjectMeta):
    __theme_ignore__: ClassVar[Sequence[str]] = ("on_validate",)
    __theme_associations__: ClassVar[dict[type, dict[str, str]]] = {
        Text: {
            "color": "fg",
        },
    }

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "cursor",
        "interval",
        "bg",
        "fg",
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

    @config.section_property
    def font(self) -> Configuration[Font]:
        return self.__text.font

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
        master: AbstractWidget | Clickable | Scene | Window,
        *,
        on_validate: Callable[[], Any] | None = None,
        max_nb_chars: int = 10,
        width: float | None = None,
        font: _TextFont | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
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
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        take_focus: bool = True,
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
            hover_cursor=SystemCursor.IBEAM,
            take_focus=take_focus,
            focus_on_hover=focus_on_hover,
            **kwargs,
        )
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
        self.__fixed_width: float | None = width
        self.__cursor_width_offset: float = 15
        self.__cursor_height_offset: float = 10
        height: float
        entry_size: tuple[int, int] = _get_entry_size(self.__text.font.__self__, max_nb_chars or 10)
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

    def get_local_size(self) -> tuple[float, float]:
        return self.__shape.get_local_size()

    def get_size(self) -> tuple[float, float]:
        return self.__shape.get_size()

    def draw_onto(self, target: AbstractRenderer) -> None:
        shape: RectangleShape = self.__shape
        outline_shape: RectangleShape = self.__outline_shape
        text: Text = self.__text
        cursor: int = self.__cursor

        outline_shape.center = shape.center = self.center
        shape.draw_onto(target)

        text.midleft = (self.left + self.__cursor_width_offset, self.centery)
        text.draw_onto(target)

        show_cursor: bool
        if self.__edit():
            show_cursor = self.__show_cursor
            if self.__cursor_animation_clock.elapsed_time(self.interval):
                self.__show_cursor = show_cursor = not show_cursor
        else:
            self.__show_cursor = show_cursor = False
        if show_cursor:
            width: float = text.font.__self__.get_rect(text.message[:cursor]).width + 1
            height: float = self.height - self.__cursor_height_offset
            if not self.__insert_mode or self.cursor == len(text.message):
                cursor_start: tuple[float, float] = (text.left + width, text.centery - height // 2)
                cursor_end: tuple[float, float] = (text.left + width, text.centery + height // 2)
                target.draw_line(text.color, cursor_start, cursor_end, width=2)
            else:
                char_rect = text.font.__self__.get_rect(text.message[cursor])
                char_rect.left = int(text.left + width)
                char_rect.centery = int(text.centery)
                target.draw_rect(text.color, char_rect)

        outline_shape.draw_onto(target)

    def get(self) -> str:
        return self.__text.message

    def clear(self) -> None:
        self.__text.clear()

    def start_edit(self) -> None:
        Keyboard.IME.start_text_input()
        self.__start_edit = True
        self.__show_cursor = True
        self.__insert_mode = False

    def stop_edit(self) -> None:
        Keyboard.IME.stop_text_input()
        self.__start_edit = False
        self.__insert_mode = False

    def invoke(self) -> None:
        if self.focus.get_mode() == BoundFocusMode.MOUSE:
            self.start_edit()

    def _on_focus_set(self) -> None:
        self.start_edit()
        self.__update_shape_outline()

    def _on_focus_leave(self) -> None:
        self.stop_edit()
        self.__update_shape_outline()

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.__shape.get_rect().collidepoint(mouse_pos)

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        scale: tuple[float, float] = self.scale
        self.__outline_shape.scale = self.__shape.scale = self.__text.scale = scale
        self.__cursor_width_offset = 15 * scale[0]
        self.__cursor_height_offset = 10 * scale[1]

    def __edit(self) -> bool:
        if not self.__start_edit:
            return False
        if self.focus.get_mode() == BoundFocusMode.KEY:
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
        text: Text = self.__text
        match event:
            case KeyDownEvent(key=Key.K_RETURN | Key.K_KP_ENTER) if text.message:
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
                    text.message = text.message[: self.cursor - 1] + text.message[self.cursor :]
                    self.cursor -= 1
                return True
            case KeyDownEvent(key=Key.K_DELETE):
                text.message = text.message[: self.cursor] + text.message[self.cursor + 1 :]
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
                self.cursor = len(text.message)
                return True
            case TextInputEvent(text=entered_text):
                new_text: str
                if not self.__insert_mode:
                    new_text = text.message[: self.cursor] + entered_text + text.message[self.cursor :]
                else:
                    new_text = text.message[: self.cursor] + entered_text + text.message[self.cursor + len(entered_text) :]
                if (max_nb_char := self.__nb_chars) == 0 or len(new_text) <= max_nb_char:
                    text.message = new_text
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

    @config.getter_with_key("fg", use_key="color")
    @config.getter_with_key("shadow_x")
    @config.getter_with_key("shadow_y")
    @config.getter_with_key("shadow")
    @config.getter_with_key("shadow_color")
    def __get_text_option(self, option: str) -> Any:
        return self.__text.config.get(option)

    @config.setter_with_key("fg", use_key="color")
    @config.setter_with_key("shadow_x")
    @config.setter_with_key("shadow_y")
    @config.setter_with_key("shadow")
    @config.setter_with_key("shadow_color")
    def __set_text_option(self, option: str, value: Any) -> None:
        return self.__text.config.set(option, value)

    @config.getter_with_key("bg", use_key="color")
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

    @config.setter_with_key("bg", use_key="color")
    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> None:
        self.__shape.config.set(option, value)
        if option != "color":
            self.__outline_shape.config.set(option, value)

    # @config.on_update("font")
    @config.on_update("fixed_width")
    def __update_shape_using_font(self) -> None:
        max_nb_chars: int = self.__nb_chars
        fixed_width: float | None = self.__fixed_width
        entry_size: tuple[int, int] = _get_entry_size(self.__text.font.__self__, max_nb_chars or 10)
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


class _TextEntry(Text):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("max_width", parent=Text.config)

    max_width: OptionAttribute[int | None] = OptionAttribute()

    @initializer
    def __init__(
        self,
        message: str = "",
        *,
        font: _TextFont | None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        color: Color,
        shadow_x: float,
        shadow_y: float,
        shadow_color: Color,
        theme: ThemeType | None = None,
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
        # max_width: int | None = self.max_width
        text: Surface = super()._render()
        # if max_width is not None:
        #     return text.subsurface(0, 0, max_width, text.get_height()).copy()
        return text

    config.add_value_converter_on_set_static("max_width", valid_optional_integer(min_value=0))
