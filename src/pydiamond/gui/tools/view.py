# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""View utility module"""

from __future__ import annotations

__all__ = ["AbstractScrollableView"]

from abc import abstractmethod
from typing import Any, Callable, Literal, final, overload
from weakref import WeakMethod

from typing_extensions import assert_never

from ...math.rect import Rect
from ...system.object import Object
from ...window.event import MouseWheelEvent


class AbstractScrollableView(Object):
    def __init__(
        self,
        *,
        xscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = None,
        yscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = None,
        wheel_xscroll_increment: int = 10,
        wheel_yscroll_increment: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.__xscrollcommand: Callable[[float, float], None] | None
        self.__yscrollcommand: Callable[[float, float], None] | None
        self.set_xscrollcommand(xscrollcommand)
        self.set_yscrollcommand(yscrollcommand)
        self.__wheel_xscroll_increment: int
        self.__wheel_yscroll_increment: int
        self.set_wheel_xscroll_increment(wheel_xscroll_increment)
        self.set_wheel_yscroll_increment(wheel_yscroll_increment)
        self.__known_area_rect: Rect = Rect(0, 0, 0, 0)
        self.__known_widget_size: tuple[int, int] = (-1, -1)
        self.__mouse_pos: tuple[float, float] | None = None

        def get_mouse_position(self: AbstractScrollableView, mouse_pos: tuple[float, float]) -> None:
            self.__mouse_pos = mouse_pos

        def handle_wheel_event(self: AbstractScrollableView, event: MouseWheelEvent) -> bool:
            return self.__handle_wheel_event(event)

        self._setup_mouse_wheel(handle_wheel_event, get_mouse_position)

    @abstractmethod
    def _setup_mouse_wheel(
        self,
        handle_mouse_wheel_event: Callable[[AbstractScrollableView, MouseWheelEvent], bool],
        handle_mouse_position: Callable[[AbstractScrollableView, tuple[float, float]], None],
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_view_rect(self) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def get_whole_rect(self) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def is_mouse_hovering(self, mouse_pos: tuple[float, float]) -> bool:
        raise NotImplementedError

    @final
    def get_view_relative_rect(self) -> Rect:
        default_rect: Rect = self.get_whole_rect()
        view_rect: Rect = self.get_view_rect()
        return view_rect.move(-default_rect.x, -default_rect.y)

    @final
    def get_whole_relative_rect(self) -> Rect:
        return Rect((0, 0), self.get_whole_rect().size)

    def set_xscrollcommand(
        self,
        xscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None,
    ) -> None:
        if xscrollcommand is None:
            self.__xscrollcommand = None
            return

        if isinstance(xscrollcommand, WeakMethod):
            _weak_command = xscrollcommand

            def command_wrapper(start: float, end: float, /) -> None:
                xscrollcommand = _weak_command()
                if xscrollcommand is None:
                    return None
                return xscrollcommand(start, end)

            xscrollcommand = command_wrapper

        self.__xscrollcommand = xscrollcommand

    @overload
    def xview(self, action: Literal["moveto"], fraction: float, /) -> None:
        ...

    @overload
    def xview(self, action: str, /, *args: Any) -> None:
        ...

    def xview(self, action: str, /, *args: Any) -> None:
        match action:
            case "moveto":
                return self.xview_moveto(*args)
            case _:
                raise ValueError(f"Invalid action name: {action}")

    def xview_moveto(self, fraction: float) -> None:
        if not (0 <= fraction <= 1):
            raise ValueError("Must be between 0 and 1")
        self.__set_view_rect_from_fraction(fraction, "x")

    def xview_scroll(self, offset: int) -> None:
        self.__move_view_rect(offset, 0)

    def set_yscrollcommand(
        self,
        yscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None,
    ) -> None:
        if yscrollcommand is None:
            self.__yscrollcommand = None
            return

        if isinstance(yscrollcommand, WeakMethod):
            _weak_command = yscrollcommand

            def command_wrapper(start: float, end: float, /) -> None:
                yscrollcommand = _weak_command()
                if yscrollcommand is None:
                    return None
                return yscrollcommand(start, end)

            yscrollcommand = command_wrapper

        self.__yscrollcommand = yscrollcommand

    @overload
    def yview(self, action: Literal["moveto"], fraction: float, /) -> None:
        ...

    @overload
    def yview(self, action: str, /, *args: Any) -> None:
        ...

    def yview(self, action: str, /, *args: Any) -> None:
        match action:
            case "moveto":
                return self.yview_moveto(*args)
            case _:
                raise ValueError(f"Invalid action name: {action}")

    def yview_moveto(self, fraction: float) -> None:
        if not (0 <= fraction <= 1):
            raise ValueError("Must be between 0 and 1")
        self.__set_view_rect_from_fraction(fraction, "y")

    def yview_scroll(self, offset: int) -> None:
        self.__move_view_rect(0, offset)

    @final
    def get_wheel_xscroll_increment(self) -> int:
        return self.__wheel_xscroll_increment

    @final
    def get_wheel_yscroll_increment(self) -> int:
        return self.__wheel_yscroll_increment

    def set_wheel_xscroll_increment(self, value: int) -> None:
        self.__wheel_xscroll_increment = max(int(value), 0)

    def set_wheel_yscroll_increment(self, value: int) -> None:
        self.__wheel_yscroll_increment = max(int(value), 0)

    @abstractmethod
    def _move_view(self, dx: int, dy: int) -> None:
        raise NotImplementedError

    def __move_view_rect(self, dx: int, dy: int) -> bool:
        dx = int(dx)
        dy = int(dy)
        if (dx, dy) == (0, 0):
            return True
        view_rect, default_rect = self.__get_view_rects()
        if view_rect.width <= 0 or view_rect.height <= 0:
            return False
        if default_rect is None or view_rect.contains(default_rect):
            return True

        whole_area = view_rect.union(default_rect)
        projection_view_rect = view_rect.move(dx, dy)
        projection_view_rect.clamp_ip(whole_area)
        dx = view_rect.x - projection_view_rect.x
        dy = view_rect.y - projection_view_rect.y

        self._move_view(dx, dy)
        self.update_view(force=True)
        return True

    def __set_view_rect_from_fraction(self, fraction: float, side: Literal["x", "y"]) -> None:
        match side:
            case "x":
                rect_size = "width"
            case "y":
                rect_size = "height"
            case _:
                assert_never(side)

        view_rect, default_rect = self.__get_view_rects()
        if (
            default_rect.width <= 0
            or default_rect.height <= 0
            or view_rect.width <= 0
            or view_rect.height <= 0
            or view_rect.contains(default_rect)
        ):
            self.update_view(force=True)
            return

        whole_area = view_rect.union(default_rect)

        start: float = fraction * (1 - (getattr(view_rect, rect_size) / getattr(whole_area, rect_size)))
        projection_view_rect = view_rect.copy()
        setattr(projection_view_rect, side, start * getattr(whole_area, rect_size))

        dx = view_rect.x - projection_view_rect.x
        dy = view_rect.y - projection_view_rect.y

        self._move_view(dx, dy)
        self.update_view(force=True)

    def __handle_wheel_event(self, event: MouseWheelEvent) -> bool:
        mouse_pos: tuple[float, float] | None = self.__mouse_pos
        try:
            if mouse_pos is None or not self.is_mouse_hovering(mouse_pos):
                return False
        finally:
            self.__mouse_pos = None

        dx: int = int(event.x_offset(self.__wheel_xscroll_increment))
        dy: int = int(event.y_offset(self.__wheel_yscroll_increment))

        return self.__move_view_rect(dx, dy)

    def __get_view_rects(self) -> tuple[Rect, Rect]:
        default_rect: Rect = self.get_whole_rect()
        view_rect: Rect = self.get_view_rect()
        return view_rect.move(-default_rect.x, -default_rect.y), Rect((0, 0), default_rect.size)

    def update_view(self, *, force: bool = False) -> None:
        view_rect, default_rect = self.__get_view_rects()
        known_area_rect = default_rect.copy()
        if not force and known_area_rect == self.__known_area_rect and view_rect.size == self.__known_widget_size:
            return

        self.__known_widget_size = view_rect.size
        self.__known_area_rect = known_area_rect
        xscrollcommand: Callable[[float, float], None] | None = self.__xscrollcommand
        yscrollcommand: Callable[[float, float], None] | None = self.__yscrollcommand

        if (
            default_rect.width <= 0
            or default_rect.height <= 0
            or view_rect.width <= 0
            or view_rect.height <= 0
            or view_rect.contains(default_rect)
        ):
            if xscrollcommand is not None:
                xscrollcommand(0, 1)
            if yscrollcommand is not None:
                yscrollcommand(0, 1)
            return

        def fraction(start: float, end: float) -> float:
            try:
                return max(0, min(start / (start + 1 - end), 1))
            except ZeroDivisionError:
                return 0

        whole_area = view_rect.union(default_rect)
        x_start = view_rect.left / whole_area.width
        x_end = view_rect.right / whole_area.width
        if not (0 <= x_start <= 1) or not (0 <= x_end <= 1):
            return self.__set_view_rect_from_fraction(fraction(x_start, x_end), "x")
        if xscrollcommand is not None:
            xscrollcommand(x_start, x_end)
        y_start = view_rect.top / whole_area.height
        y_end = view_rect.bottom / whole_area.height
        if not (0 <= y_start <= 1) or not (0 <= y_end <= 1):
            return self.__set_view_rect_from_fraction(fraction(y_start, y_end), "y")
        if yscrollcommand is not None:
            yscrollcommand(y_start, y_end)
