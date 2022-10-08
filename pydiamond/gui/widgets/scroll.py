# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ScrollBar and ScrollingContainer module"""

from __future__ import annotations

__all__ = ["ScrollBar", "ScrollingContainer"]


from enum import auto, unique
from functools import reduce
from itertools import takewhile
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Protocol, Sequence, final
from weakref import WeakMethod

from typing_extensions import assert_never

from ...graphics.color import BLACK, GRAY, TRANSPARENT, WHITE, Color
from ...graphics.renderer import AbstractRenderer
from ...graphics.shape import RectangleShape
from ...graphics.transformable import Transformable
from ...math.rect import Rect
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.enum import AutoLowerNameEnum
from ...system.theme import ThemedObjectMeta, ThemeType
from ...system.validation import valid_integer
from ...window.event import MouseButtonDownEvent, MouseButtonUpEvent, MouseMotionEvent, MouseWheelEvent
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
        take_focus: bool = True,
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
            return start / (start + 1 - end)
        except ZeroDivisionError:
            return 0

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


class ScrollingContainer(AbstractWidget):
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "xscrollincrement",
        "yscrollincrement",
    )

    xscrollincrement: OptionAttribute[int] = OptionAttribute()
    yscrollincrement: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        width: int,
        height: int,
        *,
        xscrollincrement: int = 20,
        yscrollincrement: int = 20,
        **kwargs: Any,
    ) -> None:
        super().__init__(master=master, **kwargs)

        self.__view_size: tuple[int, int] = int(width), int(height)
        self.__x_scroll: ScrollBar | None = None
        self.__y_scroll: ScrollBar | None = None
        self.__known_area_rect: Rect = Rect(0, 0, 0, 0)
        self.__mouse_pos: tuple[float, float] = (0, 0)

        self.xscrollincrement = xscrollincrement
        self.yscrollincrement = yscrollincrement

        def get_mouse_position(self: ScrollingContainer, mouse_pos: tuple[float, float]) -> None:
            self.__mouse_pos = mouse_pos

        self.event.bind(MouseWheelEvent, WeakMethod(self.__handle_wheel_event))
        self.event.bind_mouse_position(get_mouse_position)

    def _is_mouse_hovering_child(self, widget: AbstractWidget, mouse_pos: tuple[float, float]) -> bool:
        return not any(
            child.get_visible_rect().collidepoint(mouse_pos)
            for child in takewhile(lambda child: child is not widget, reversed(self.children))
        )

    @final
    def get_size(self) -> tuple[int, int]:
        return self.__view_size

    def set_size(self, size: tuple[int, int]) -> None:
        width, height = size
        self.__view_size = int(width), int(height)
        self.__update_scrollbars(force=True)

    def draw_onto(self, target: AbstractRenderer) -> None:
        self.__update_scrollbars(force=False)
        for child in self.iter_children():
            child.draw_onto(target)

    def bind_xview(self, scrollbar: ScrollBar | None) -> None:
        if scrollbar is not None:
            self.__x_scroll = scrollbar
            scrollbar.set_command(WeakMethod(self.xview))
        else:
            if self.__x_scroll is not None:
                self.__x_scroll.set_command(None)
            self.__x_scroll = None

    def xview(self, action: Literal["moveto"], *args: Any) -> None:
        match action:
            case "moveto":
                return self.xview_moveto(*args)
            case _:
                assert_never(action)

    def xview_moveto(self, fraction: float) -> None:
        if not (0 <= fraction <= 1):
            raise ValueError("Must be between 0 and 1")
        self.__set_view_rect_from_fraction(fraction, "x")

    def bind_yview(self, scrollbar: ScrollBar | None) -> None:
        if scrollbar is not None:
            self.__y_scroll = scrollbar
            scrollbar.set_command(WeakMethod(self.yview))
        else:
            if self.__y_scroll is not None:
                self.__y_scroll.set_command(None)
            self.__y_scroll = None

    def yview(self, action: Literal["moveto"], *args: Any) -> None:
        match action:
            case "moveto":
                return self.yview_moveto(*args)
            case _:
                assert_never(action)

    def yview_moveto(self, fraction: float) -> None:
        if not (0 <= fraction <= 1):
            raise ValueError("Must be between 0 and 1")
        self.__set_view_rect_from_fraction(fraction, "y")

    @final
    def _get_whole_relative_area(self) -> Rect:
        return reduce(Rect.union, (child.get_relative_rect() for child in self.iter_children()), Rect((0, 0), self.get_size()))

    @final
    def _get_whole_area(self) -> Rect:
        return reduce(Rect.union, (child.get_rect() for child in self.iter_children()), Rect(self.topleft, self.get_size()))

    @final
    def _get_children_relative_area(self) -> Rect | None:
        children: list[AbstractWidget] = list(self.iter_children())
        if not children:
            return None
        return reduce(Rect.union, (child.get_relative_rect() for child in children))

    @final
    def _get_children_area(self) -> Rect | None:
        children: list[AbstractWidget] = list(self.iter_children())
        if not children:
            return None
        return reduce(Rect.union, (child.get_rect() for child in children))

    def __set_view_rect_from_fraction(self, fraction: float, side: Literal["x", "y"]) -> None:
        match side:
            case "x":
                rect_size = "width"
            case "y":
                rect_size = "height"
            case _:
                assert_never(side)

        view_rect, children_area = self.__get_view_rects()
        if children_area is None or view_rect.width <= 0 or view_rect.height <= 0 or view_rect.contains(children_area):
            self.__update_scrollbars(force=True)
            return

        whole_area = view_rect.union(children_area)

        start: float = fraction * (1 - (getattr(view_rect, rect_size) / getattr(whole_area, rect_size)))
        projection_view_rect = view_rect.copy()
        setattr(projection_view_rect, side, start * getattr(whole_area, rect_size))

        dx = view_rect.x - projection_view_rect.x
        dy = view_rect.y - projection_view_rect.y

        for child in self.iter_children():
            child.move(dx, dy)

        self.__update_scrollbars(force=True)

    def __handle_wheel_event(self, event: MouseWheelEvent) -> bool:
        if not self.is_mouse_hovering(self.__mouse_pos):
            return False

        view_rect, children_area = self.__get_view_rects()
        if view_rect.width <= 0 or view_rect.height <= 0:
            return False
        if children_area is None or view_rect.contains(children_area):
            return True

        dx: int = int(event.x * self.xscrollincrement)
        dy: int = int(event.y * self.yscrollincrement)

        if (dx, dy) != (0, 0):
            whole_area = view_rect.union(children_area)
            projection_view_rect = view_rect.move(-dx, -dy)
            projection_view_rect.clamp_ip(whole_area)
            dx = view_rect.x - projection_view_rect.x
            dy = view_rect.y - projection_view_rect.y

            for child in self.iter_children():
                child.move(dx, dy)

            self.__update_scrollbars(force=True)

        return True

    def __get_view_rects(self) -> tuple[Rect, Rect | None]:
        children_area: Rect | None = self._get_children_relative_area()
        view_rect = Rect((0, 0), self.get_size())

        if children_area is not None:
            view_rect.x = -children_area.x
            view_rect.y = -children_area.y
            children_area.x = 0
            children_area.y = 0

        return view_rect, children_area

    def __update_scrollbars(self, *, force: bool) -> None:
        view_rect, children_area = self.__get_view_rects()
        known_area_rect = children_area.copy() if children_area is not None else Rect(0, 0, 0, 0)
        if not force and known_area_rect == self.__known_area_rect:
            return

        self.__known_area_rect = known_area_rect
        x_scroll: ScrollBar | None = self.__x_scroll
        y_scroll: ScrollBar | None = self.__y_scroll

        if children_area is None or view_rect.width <= 0 or view_rect.height <= 0 or view_rect.contains(children_area):
            if x_scroll is not None:
                x_scroll.set(0, 1)
            if y_scroll is not None:
                y_scroll.set(0, 1)
            return

        def fraction(start: float, end: float) -> float:
            try:
                return max(0, min(start / (start + 1 - end), 1))
            except ZeroDivisionError:
                return 0

        whole_area = view_rect.union(children_area)
        x_start = view_rect.left / whole_area.width
        x_end = view_rect.right / whole_area.width
        if not (0 <= x_start <= 1) or not (0 <= x_end <= 1):
            return self.__set_view_rect_from_fraction(fraction(x_start, x_end), "x")
        if x_scroll is not None:
            x_scroll.set(x_start, x_end)
        y_start = view_rect.top / whole_area.height
        y_end = view_rect.bottom / whole_area.height
        if not (0 <= y_start <= 1) or not (0 <= y_end <= 1):
            return self.__set_view_rect_from_fraction(fraction(y_start, y_end), "y")
        if y_scroll is not None:
            y_scroll.set(y_start, y_end)

    config.add_value_converter_on_set_static("xscrollincrement", valid_integer(min_value=0))
    config.add_value_converter_on_set_static("yscrollincrement", valid_integer(min_value=0))
