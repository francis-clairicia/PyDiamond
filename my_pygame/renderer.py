# -*- coding: Utf-8 -*

from abc import abstractmethod
from typing import Any, List, Optional, Protocol, Sequence, Tuple, Union, overload, runtime_checkable

from pygame.draw import (
    rect as _draw_rect,
    polygon as _draw_polygon,
    circle as _draw_circle,
    ellipse as _draw_ellipse,
    arc as _draw_arc,
    line as _draw_line,
    lines as _draw_multiple_lines,
    aaline as _draw_antialiased_line,
    aalines as _draw_multiple_antialiased_lines,
)

from pygame.color import Color
from pygame.rect import Rect
from pygame.surface import Surface
from pygame.math import Vector2

from .surface import create_surface


_Coordinate = Union[Tuple[float, float], Sequence[float], Vector2]
_ColorValue = Union[Color, str, Tuple[int, int, int], List[int], int, Tuple[int, int, int, int]]
_ColorInput = Union[Color, str, List[int], Tuple[int, int, int], Tuple[int, int, int, int]]
_CanBeRect = Union[
    Rect,
    Tuple[int, int, int, int],
    List[int],
    Tuple[_Coordinate, _Coordinate],
    List[_Coordinate],
]


class _HasRectAttribute(Protocol):
    rect: _CanBeRect


_RectValue = Union[_CanBeRect, _HasRectAttribute]


@runtime_checkable
class Renderer(Protocol):
    @abstractmethod
    def get_rect(self, /, **kwargs: Union[float, Sequence[float]]) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def get_size(self, /) -> Tuple[float, float]:
        raise NotImplementedError

    @abstractmethod
    def fill(self, /, color: _ColorInput) -> None:
        raise NotImplementedError

    @overload
    def draw(self, obj: Surface, dest: Tuple[float, float], /, *, area: Optional[Rect] = None, special_flags: int = 0) -> Rect:
        ...

    @overload
    def draw(self, obj: Surface, dest: Rect, /, *, area: Optional[Rect] = None, special_flags: int = 0) -> Rect:
        ...

    @abstractmethod
    def draw(self, obj: Surface, /, *args: Any, **kwargs: Any) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_rect(
        self,
        /,
        color: _ColorValue,
        rect: _RectValue,
        width: int = 0,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_polygon(
        self,
        /,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_circle(
        self,
        /,
        color: _ColorValue,
        center: _Coordinate,
        radius: float,
        width: int = 0,
        draw_top_right: Optional[bool] = None,
        draw_top_left: Optional[bool] = None,
        draw_bottom_left: Optional[bool] = None,
        draw_bottom_right: Optional[bool] = None,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_ellipse(self, /, color: _ColorValue, rect: _RectValue, width: int = 0) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_arc(
        self,
        /,
        color: _ColorValue,
        rect: _RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_line(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_lines(
        self,
        /,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def aaline(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        blend: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def aalines(
        self,
        /,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        blend: int = 1,
    ) -> Rect:
        raise NotImplementedError


class SurfaceRenderer(Renderer):
    @overload
    def __init__(self, size: Tuple[float, float], /, *, convert_alpha: bool = True) -> None:
        ...

    @overload
    def __init__(self, target: Surface, /) -> None:
        ...

    def __init__(self, arg: Union[Surface, Tuple[float, float]], /, *, convert_alpha: bool = True) -> None:
        self.__target: Surface = arg if isinstance(arg, Surface) else create_surface(arg, convert_alpha=convert_alpha)

    def get_rect(self, /, **kwargs: Union[float, Sequence[float]]) -> Rect:
        target: Surface = self.__target
        return target.get_rect(**kwargs)

    def get_size(self, /) -> Tuple[float, float]:
        target: Surface = self.__target
        return target.get_size()

    def fill(self, /, color: _ColorInput) -> None:
        target: Surface = self.__target
        target.fill(color)

    @overload
    def draw(self, obj: Surface, dest: Tuple[float, float], /, *, area: Optional[Rect] = None, special_flags: int = 0) -> Rect:
        ...

    @overload
    def draw(self, obj: Surface, dest: Rect, /, *, area: Optional[Rect] = None, special_flags: int = 0) -> Rect:
        ...

    def draw(self, obj: Surface, /, *args: Any, **kwargs: Any) -> Rect:
        target: Surface = self.__target
        return target.blit(obj, *args, **kwargs)

    def draw_rect(
        self,
        /,
        color: _ColorValue,
        rect: _RectValue,
        width: int = 0,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_rect(
            surface=target,
            color=color,
            rect=rect,
            width=width,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )

    def draw_polygon(
        self,
        /,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_polygon(surface=target, color=color, points=points, width=width)

    def draw_circle(
        self,
        /,
        color: _ColorValue,
        center: _Coordinate,
        radius: float,
        width: int = 0,
        draw_top_right: Optional[bool] = None,
        draw_top_left: Optional[bool] = None,
        draw_bottom_left: Optional[bool] = None,
        draw_bottom_right: Optional[bool] = None,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_circle(
            surface=target,
            color=color,
            center=center,
            radius=radius,
            width=width,
            draw_top_left=draw_top_left,
            draw_top_right=draw_top_right,
            draw_bottom_left=draw_bottom_left,
            draw_bottom_right=draw_bottom_right,
        )

    def draw_ellipse(self, /, color: _ColorValue, rect: _RectValue, width: int = 0) -> Rect:
        target: Surface = self.__target
        return _draw_ellipse(surface=target, color=color, rect=rect, width=width)

    def draw_arc(
        self,
        /,
        color: _ColorValue,
        rect: _RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_arc(surface=target, color=color, rect=rect, start_angle=start_angle, stop_angle=stop_angle, width=width)

    def draw_line(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_line(surface=target, color=color, start_pos=start_pos, end_pos=end_pos, width=width)

    def draw_lines(
        self,
        /,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_multiple_lines(surface=target, color=color, closed=closed, points=points, width=width)

    def aaline(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        blend: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_antialiased_line(surface=target, color=color, start_pos=start_pos, end_pos=end_pos, blend=blend)

    def aalines(
        self,
        /,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        blend: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        return _draw_multiple_antialiased_lines(surface=target, color=color, closed=closed, points=points, blend=blend)

    @property
    def surface(self, /) -> Surface:
        return self.__target
