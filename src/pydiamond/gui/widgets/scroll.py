# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ScrollBar and ScrollingContainer module"""

from __future__ import annotations

__all__ = ["AbstractScrollableWidget", "ScrollBar", "ScrollingContainer"]

from enum import auto, unique
from functools import reduce
from itertools import takewhile
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Literal, Protocol, Sequence
from weakref import WeakMethod

from ...graphics.color import BLACK, GRAY, TRANSPARENT, WHITE, Color
from ...graphics.renderer import AbstractRenderer
from ...graphics.shape import RectangleShape
from ...graphics.transformable import Transformable
from ...math.rect import Rect
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.theme import ThemedObjectMeta, ThemeType
from ...system.utils.enum import AutoLowerNameEnum
from ...window.event import MouseButtonDownEvent, MouseButtonUpEvent, MouseMotionEvent, MouseWheelEvent
from ..tools.view import AbstractScrollableView
from .abc import AbstractWidget, Widget, WidgetsManager

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...window.cursor import Cursor


class _ScrollBarCommand(Protocol):
    def __call__(self, action: Literal["moveto"], fraction: float, /) -> None:
        ...

    # TODO: Add this command (arrow buttons)
    # @overload
    # def __call__(self, action: Literal["scroll"], offset: Literal[-1, 1], what: Literal["units", "pages"], /) -> None:
    #     ...


class ScrollBar(Widget, Transformable, metaclass=ThemedObjectMeta):
    __theme_ignore__: ClassVar[Sequence[str]] = ("orient",)

    @unique
    class Orient(AutoLowerNameEnum):
        HORIZONTAL = auto()
        VERTICAL = auto()

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "command",
        "local_width",
        "local_height",
        "local_size",
        "cursor_color",
        "color",
        "outline",
        "outline_color",
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
        "orient",
        parent=Widget.config,
    )

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()
    cursor_color: OptionAttribute[Color] = OptionAttribute()
    color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()
    orient: OptionAttribute[str] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        width: float,
        height: float,
        command: _ScrollBarCommand | WeakMethod[_ScrollBarCommand] | None = None,
        *,
        orient: str = "horizontal",
        color: Color = WHITE,
        cursor_color: Color = GRAY,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        take_focus: bool = False,
        focus_on_hover: bool | None = None,
        outline: int = 0,
        outline_color: Color = BLACK,
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
            take_focus=take_focus,
            focus_on_hover=focus_on_hover,
            **kwargs,
        )
        self.__bg_shape: RectangleShape = RectangleShape(
            width=width,
            height=height,
            color=color,
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
        self.__start: float = 0
        self.__end: float = 1
        self.__cursor_click: float
        self.__cursor_shape: RectangleShape = RectangleShape(
            width=0,
            height=0,
            color=cursor_color,
            outline=0,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )

        self.__command: _ScrollBarCommand | None

        self.set_command(command)

        self.orient = orient
        self.set_active_only_on_hover(False)

    def get_local_size(self) -> tuple[float, float]:
        return self.__outline_shape.get_local_size()

    def get_size(self) -> tuple[float, float]:
        return self.__outline_shape.get_size()

    def draw_onto(self, target: AbstractRenderer) -> None:
        bg_shape: RectangleShape = self.__bg_shape
        cursor_shape: RectangleShape = self.__cursor_shape
        outline_shape: RectangleShape = self.__outline_shape
        outline: int = outline_shape.outline

        bg_shape.draw_onto(target)

        cursor_start: float = self.__start
        if self.orient == ScrollBar.Orient.HORIZONTAL:
            cursor_shape.midleft = (
                max(bg_shape.left + bg_shape.width * cursor_start, bg_shape.left + (outline / 2)),
                bg_shape.centery,
            )
        else:
            cursor_shape.midtop = (
                bg_shape.centerx,
                max(bg_shape.top + bg_shape.height * cursor_start, bg_shape.top + (outline / 2)),
            )

        cursor_shape.draw_onto(target)
        outline_shape.draw_onto(target)

    def invoke(self) -> None:
        pass

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        cursor_rect: Rect = self.__get_cursor_shape_rect()
        if not cursor_rect.collidepoint(event.pos):
            cursor_rect.center = event.pos
            self.__set_cursor_bounds(cursor_rect)
            self.__cursor_click = 0.5
        elif self.orient == ScrollBar.Orient.HORIZONTAL:
            self.__cursor_click = (event.pos[0] - cursor_rect.left) / cursor_rect.width
        else:
            self.__cursor_click = (event.pos[1] - cursor_rect.top) / cursor_rect.height
        return super()._on_click_down(event)

    def _on_click_up(self, event: MouseButtonUpEvent) -> None:
        del self.__cursor_click
        return super()._on_click_up(event)

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        rect: Rect = self.get_rect()

        def in_bounds() -> bool:
            if self.orient == ScrollBar.Orient.HORIZONTAL:
                return rect.left <= event.pos[0] <= rect.right
            return rect.top <= event.pos[1] <= rect.bottom

        if self.active and in_bounds():
            cursor_rect: Rect = self.__get_cursor_shape_rect()
            cursor_click: float = self.__cursor_click
            if self.orient == ScrollBar.Orient.HORIZONTAL:
                cursor_rect.left = int(event.pos[0] - cursor_click * cursor_rect.width)
            else:
                cursor_rect.top = int(event.pos[1] - cursor_click * cursor_rect.height)
            self.__set_cursor_bounds(cursor_rect)
        return super()._on_mouse_motion(event)

    def _on_move(self) -> None:
        self.__bg_shape.center = self.__outline_shape.center = self.center
        return super()._on_move()

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        self.__outline_shape.scale = self.__bg_shape.scale = self.__cursor_shape.scale = self.scale

    def __get_cursor_shape_rect(self) -> Rect:
        cursor_shape: RectangleShape = self.__cursor_shape
        cursor_rect: Rect = cursor_shape.get_rect()

        cursor_start: float = self.__start
        if self.orient == ScrollBar.Orient.HORIZONTAL:
            cursor_rect.midleft = int(self.left + self.width * cursor_start), int(self.centery)
        else:
            cursor_rect.midtop = int(self.centerx), int(self.top + self.height * cursor_start)
        return cursor_rect

    def __set_cursor_bounds(self, cursor_rect: Rect) -> None:
        offset: float = self.__end - self.__start
        if self.orient == ScrollBar.Orient.HORIZONTAL:
            left: int = int(self.left)
            width: int = int(self.width)
            if width == 0:
                return
            if cursor_rect.left < left:
                self.__start = 0
            else:
                self.__start = (cursor_rect.left - left) / width
        else:
            top: int = int(self.top)
            height: int = int(self.height)
            if height == 0:
                return
            if cursor_rect.top < top:
                self.__start = 0
            else:
                self.__start = (cursor_rect.top - top) / height
        if (end := self.__start + offset) > 1:
            end = 1
            self.__start = 1 - offset
        self.__end = end
        command = self.__command
        if command is not None:
            command("moveto", self.fraction)

    def get(self) -> tuple[float, float]:
        return (self.__start, self.__end)

    def set(self, start: float, end: float) -> None:
        start = float(start)
        end = float(end)
        if not (0 <= start <= 1) or not (0 <= end <= 1) or start > end:
            raise ValueError(f"Invalid bounds: {(start, end)}")
        min_offset = 0.02
        if end - start < min_offset:
            end = start + min_offset
            if end > 1:
                end = 1
                start = 1 - min_offset
        self.__start = start
        self.__end = end
        self.__update_all_shapes()

    @property
    def fraction(self) -> float:
        start = self.__start
        end = self.__end
        try:
            value = start / (start + 1 - end)
        except ZeroDivisionError:
            return 0
        return max(0, min(value, 1))

    config.add_enum_converter("orient", Orient, return_value_on_get=True)

    @config.getter_with_key("cursor_color", use_key="color")
    def __get_cursor_shape_options(self, option: str) -> Any:
        return self.__cursor_shape.config.get(option)

    @config.setter_with_key("cursor_color", use_key="color")
    def __set_cursor_shape_options(self, option: str, value: Any) -> Any:
        return self.__cursor_shape.config.set(option, value)

    @config.getter_with_key("outline")
    @config.getter_with_key("outline_color")
    def __get_outline_options(self, option: str) -> Any:
        return self.__outline_shape.config.get(option)

    @config.setter_with_key("outline")
    @config.setter_with_key("outline_color")
    def __set_outline_options(self, option: str, value: Any) -> None:
        self.__outline_shape.config.set(option, value)

    @config.getter_with_key("local_width")
    @config.getter_with_key("local_height")
    @config.getter_with_key("local_size")
    @config.getter_with_key("color")
    @config.getter_with_key("border_radius")
    @config.getter_with_key("border_top_left_radius")
    @config.getter_with_key("border_top_right_radius")
    @config.getter_with_key("border_bottom_left_radius")
    @config.getter_with_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__bg_shape.config.get(option)

    @config.setter_with_key("local_width")
    @config.setter_with_key("local_height")
    @config.setter_with_key("local_size")
    @config.setter_with_key("color")
    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> Any:
        return self.__bg_shape.config.set(option, value)

    @config.on_update_value_with_key("border_radius")
    @config.on_update_value_with_key("border_top_left_radius")
    @config.on_update_value_with_key("border_top_right_radius")
    @config.on_update_value_with_key("border_bottom_left_radius")
    @config.on_update_value_with_key("border_bottom_right_radius")
    def __update_cursor_shape_option(self, option: str, value: Any) -> None:
        self.__cursor_shape.config.set(option, value)
        self.__outline_shape.config.set(option, value)

    @config.on_update("orient")
    @config.on_update("local_width")
    @config.on_update("local_height")
    @config.on_update("local_size")
    def __update_all_shapes(self) -> None:
        outline_shape: RectangleShape = self.__outline_shape
        outline_shape.local_size = self.local_size
        width, height = self.local_size
        orient: str = self.orient
        cursor_shape: RectangleShape = self.__cursor_shape
        cursor_size_percent: float = self.__end - self.__start
        if orient == ScrollBar.Orient.HORIZONTAL:
            cursor_shape.local_size = (width * cursor_size_percent, height)
        else:
            cursor_shape.local_size = (width, height * cursor_size_percent)

    @config.getter("command")
    def get_command(self) -> _ScrollBarCommand | None:
        return self.__command

    @config.setter("command")
    def set_command(self, command: _ScrollBarCommand | WeakMethod[_ScrollBarCommand] | None) -> None:
        if isinstance(command, WeakMethod):
            _weak_command = command

            def command_wrapper(action: Literal["moveto"], fraction: float, /) -> None:
                command = _weak_command()
                if command is None:
                    return None
                return command(action, fraction)

            command = command_wrapper

        self.__command = command
        if command is not None:
            command("moveto", self.fraction)


class AbstractScrollableWidget(AbstractWidget, AbstractScrollableView):
    if TYPE_CHECKING:

        def __init__(
            self,
            master: AbstractWidget | WidgetsManager,
            *,
            xscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = ...,
            yscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = ...,
            wheel_xscroll_increment: int = ...,
            wheel_yscroll_increment: int = ...,
            **kwargs: Any,
        ) -> None:
            ...

    def _setup_mouse_wheel(
        self,
        handle_mouse_wheel_event: Callable[[AbstractScrollableView, MouseWheelEvent], bool],
        handle_mouse_position: Callable[[AbstractScrollableView, tuple[float, float]], None],
    ) -> None:
        self.event.bind(MouseWheelEvent, handle_mouse_wheel_event)
        self.event.bind_mouse_position(handle_mouse_position)

    def get_clip(self) -> Rect:
        return self.get_view_rect()

    def _update_widget(self) -> None:
        super()._update_widget()
        self.update_view(force=False)


class ScrollingContainer(AbstractScrollableWidget):
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        width: int,
        height: int,
        *,
        xscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = None,
        yscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = None,
        wheel_xscroll_increment: int = 10,
        wheel_yscroll_increment: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            # AbstractWidget
            master=master,
            # AbstractScrollableView
            xscrollcommand=xscrollcommand,
            yscrollcommand=yscrollcommand,
            wheel_xscroll_increment=wheel_xscroll_increment,
            wheel_yscroll_increment=wheel_yscroll_increment,
            # Other
            **kwargs,
        )

        self.__size: tuple[int, int] = int(width), int(height)

    def _is_mouse_hovering_child(self, widget: AbstractWidget, mouse_pos: tuple[float, float]) -> bool:
        return not any(
            child.get_visible_rect().collidepoint(mouse_pos)
            for child in takewhile(lambda child: child is not widget, reversed(self.children))
        )

    def get_view_rect(self) -> Rect:
        return Rect(self.topleft, self.__size)

    def get_whole_rect(self) -> Rect:
        children_rects = [child.get_rect() for child in self.iter_children()]
        if not children_rects:
            return Rect(self.topleft, (0, 0))
        return reduce(Rect.union, children_rects)

    def get_size(self) -> tuple[int, int]:
        return self.__size

    def set_size(self, size: tuple[int, int]) -> None:
        width, height = size
        self.__size = int(width), int(height)
        self.update_view(force=True)

    def draw_onto(self, target: AbstractRenderer) -> None:
        for child in self.iter_children():
            child.draw_onto(target)

    def _move_view(self, dx: int, dy: int) -> None:
        for child in self.iter_children():
            child.move(dx, dy)
