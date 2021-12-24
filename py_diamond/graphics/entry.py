# -*- coding: Utf-8 -*

__all__ = ["Entry", "MetaEntry"]

from string import printable as ASCII_PRINTABLE
from typing import Any, Optional, Tuple, Union

from ..audio.sound import Sound
from ..system.configuration import Configuration, OptionAttribute, initializer
from ..system.utils import valid_integer, valid_optional_float, valid_optional_integer
from ..window.clickable import Clickable
from ..window.clock import Clock
from ..window.cursor import SystemCursor
from ..window.display import Window
from ..window.event import Event, KeyDownEvent, TextInputEvent
from ..window.keyboard import Keyboard
from ..window.scene import Scene
from .color import BLACK, WHITE, Color  # , GRAY
from .drawable import MetaTDrawable, TDrawable
from .font import Font
from .renderer import Renderer
from .shape import RectangleShape
from .surface import Surface
from .text import Text, _TextFont
from .theme import MetaThemedObject, NoTheme, ThemeType


class MetaEntry(MetaTDrawable, MetaThemedObject):
    pass


@Text.register
@RectangleShape.register
class Entry(TDrawable, Clickable, metaclass=MetaEntry):
    @initializer
    def __init__(
        self,
        /,
        master: Union[Scene, Window],
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
        # highlight_color=GRAY,
        # highlight_thickness=2,
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
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            theme=NoTheme,
        )
        Clickable.__init__(
            self,
            master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=SystemCursor.CURSOR_IBEAM,
        )
        self.interval = interval

        self.__cursor: int = 0
        self.__show_cursor: bool = False
        self.__cursor_animated: bool = False
        self.__cursor_animation_clock = Clock()

        key_press_event = self.__key_press
        master.event.bind_event(Event.Type.KEYDOWN, key_press_event)
        master.event.bind_event(Event.Type.TEXTINPUT, key_press_event)

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__shape.get_local_size()

    def draw_onto(self, /, target: Renderer) -> None:
        shape: RectangleShape = self.__shape
        text: Text = self.__text
        cursor: int = self.__cursor

        shape.center = self.center
        shape.draw_onto(target)

        text.midleft = (self.left + self.__cursor_width_offset, self.centery)
        text.draw_onto(target)

        show_cursor: bool = self.__show_cursor
        if self.__edit() and self.__cursor_animated:
            if self.__cursor_animation_clock.elapsed_time(self.interval):
                self.__show_cursor = show_cursor = not show_cursor
        else:
            self.__show_cursor = show_cursor = False
        if not show_cursor:
            return

        width: float = text.font.size(text.message[:cursor])[0] + 1
        height: float = self.height - self.__cursor_height_offset
        cursor_start: Tuple[float, float] = (text.left + width, text.centery - height // 2)
        cursor_end: Tuple[float, float] = (text.left + width, text.centery + height // 2)
        target.draw_line(text.color, cursor_start, cursor_end, width=2)

    def get(self, /) -> str:
        return self.__text.message

    def clear(self, /) -> None:
        self.__text.message = str()

    def start_edit(self, /) -> None:
        Keyboard.IME.start_text_input()
        self.__cursor_animated = True
        self.__show_cursor = True

    def stop_edit(self, /) -> None:
        Keyboard.IME.stop_text_input()
        self.__cursor_animated = False

    def invoke(self, /) -> None:
        self.start_edit()

    def _mouse_in_hitbox(self, /, mouse_pos: Tuple[float, float]) -> bool:
        return self.__shape.rect.collidepoint(mouse_pos)

    def _apply_both_rotation_and_scale(self, /) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self, /) -> None:
        raise NotImplementedError

    def _apply_only_scale(self, /) -> None:
        scale: float = self.scale
        self.__shape.scale = self.__text.scale = scale
        self.__cursor_width_offset = 15 * scale
        self.__cursor_height_offset = 10 * scale

    def __edit(self, /) -> bool:
        return Keyboard.IME.text_input_enabled()

    def __key_press(self, /, event: Union[KeyDownEvent, TextInputEvent]) -> bool:
        if not self.__edit() or not isinstance(event, (KeyDownEvent, TextInputEvent)):
            return False
        self.__show_cursor = True
        self.__cursor_animation_clock.restart()
        text: Text = self.__text
        cursor: int = self.__cursor
        max_nb_char: int = self.__nb_chars
        if isinstance(event, KeyDownEvent):
            if event.key == Keyboard.Key.ESCAPE:
                self.stop_edit()
                return True
            if event.key == Keyboard.Key.BACKSPACE:
                if cursor > 0:
                    text.message = text.message[: cursor - 1] + text.message[cursor:]
                    self.cursor = cursor - 1
                return True
            if event.key == Keyboard.Key.DELETE:
                text.message = text.message[:cursor] + text.message[cursor + 1 :]
                return True
            if event.key == Keyboard.Key.LEFT:
                self.cursor = cursor - 1
                return True
            if event.key == Keyboard.Key.RIGHT:
                self.cursor = cursor + 1
                return True
            if event.key == Keyboard.Key.HOME:
                self.cursor = 0
                return True
            if event.key == Keyboard.Key.END:
                self.cursor = len(text.message)
                return True
            return False

        entered_text: str = event.text
        new_text: str = text.message[:cursor] + entered_text + text.message[cursor:]
        if max_nb_char == 0 or len(new_text) <= max_nb_char:
            text.message = new_text
            self.cursor = cursor + len(entered_text)
        return True

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
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
    )

    @config.value_converter("cursor")
    def __cursor_validator(self, /, cursor: Any) -> int:
        return valid_integer(value=cursor, min_value=0, max_value=len(self.get()))

    config.value_converter_static("interval", valid_integer(min_value=0))
    config.value_converter_static("fixed_width", valid_optional_float(min_value=0))

    @config.getter_key("fg", use_key="color")
    @config.getter_key("font")
    @config.getter_key("shadow_x")
    @config.getter_key("shadow_y")
    @config.getter_key("shadow")
    @config.getter_key("shadow_color")
    def __get_text_option(self, /, option: str) -> Any:
        return self.__text.config.get(option)

    @config.setter_key("fg", use_key="color")
    @config.setter_key("font")
    @config.setter_key("shadow_x")
    @config.setter_key("shadow_y")
    @config.setter_key("shadow")
    @config.setter_key("shadow_color")
    def __set_text_option(self, /, option: str, value: Any) -> None:
        return self.__text.config.set(option, value)

    @config.getter_key("bg", use_key="color")
    @config.getter_key("local_width")
    @config.getter_key("local_height")
    @config.getter_key("local_size")
    @config.getter_key("outline")
    @config.getter_key("outline_color")
    @config.getter_key("border_radius")
    @config.getter_key("border_top_left_radius")
    @config.getter_key("border_top_right_radius")
    @config.getter_key("border_bottom_left_radius")
    @config.getter_key("border_bottom_right_radius")
    def __get_shape_option(self, /, option: str) -> Any:
        return self.__shape.config.get(option)

    @config.setter_key("bg", use_key="color")
    @config.setter_key("outline")
    @config.setter_key("outline_color")
    @config.setter_key("border_radius")
    @config.setter_key("border_top_left_radius")
    @config.setter_key("border_top_right_radius")
    @config.setter_key("border_bottom_left_radius")
    @config.setter_key("border_bottom_right_radius")
    def __set_shape_option(self, /, option: str, value: Any) -> None:
        return self.__shape.config.set(option, value)

    config.readonly("local_width", "local_height", "local_size")

    @config.on_update("font")
    @config.on_update("fixed_width")
    def __update_shape_using_font(self, /) -> None:
        max_nb_chars: int = self.__nb_chars
        fixed_width: Optional[float] = self.__fixed_width
        entry_size: Tuple[int, int] = _get_entry_size(self.__text.font, max_nb_chars or 10)
        width: float
        if fixed_width is not None:
            width = fixed_width
        else:
            width = entry_size[0] + self.__cursor_width_offset
        height: float = entry_size[1] + self.__cursor_height_offset
        self.__shape.local_size = (width, height)

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

    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()


def _get_entry_size(font: Font, nb_chars: int) -> Tuple[int, int]:
    return font.size(max(ASCII_PRINTABLE, key=lambda char: font.size(char)) * nb_chars)


class _TextEntry(Text):
    @initializer
    def __init__(
        self,
        /,
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

    def _render(self, /) -> Surface:
        # max_width: Optional[int] = self.max_width
        text: Surface = super()._render()
        # if max_width is not None:
        #     return text.subsurface(0, 0, max_width, text.get_height()).copy()
        return text

    config = Configuration("max_width", parent=Text.config)

    config.value_converter_static("max_width", valid_optional_integer(min_value=0))

    max_width: OptionAttribute[Optional[int]] = OptionAttribute()
