# -*- coding: Utf-8 -*

__all__ = ["Renderer", "SurfaceRenderer"]

from abc import ABCMeta, abstractmethod
from enum import IntEnum, unique
from typing import Any, List, Optional, Protocol, Sequence, Tuple, Union, overload

from pygame.constants import (
    BLEND_ALPHA_SDL2,
    BLEND_PREMULTIPLIED,
    BLEND_RGB_ADD,
    BLEND_RGB_MAX,
    BLEND_RGB_MIN,
    BLEND_RGB_MULT,
    BLEND_RGB_SUB,
    BLEND_RGBA_ADD,
    BLEND_RGBA_MAX,
    BLEND_RGBA_MIN,
    BLEND_RGBA_MULT,
    BLEND_RGBA_SUB,
)
from pygame.draw import (
    aaline as _draw_antialiased_line,
    aalines as _draw_multiple_antialiased_lines,
    arc as _draw_arc,
    circle as _draw_circle,
    ellipse as _draw_ellipse,
    line as _draw_line,
    lines as _draw_multiple_lines,
    polygon as _draw_polygon,
    rect as _draw_rect,
)
from pygame.rect import Rect as _PgRect

from ..math import Vector2
from .color import Color
from .rect import Rect, pg_rect_convert
from .surface import Surface, create_surface

_Coordinate = Union[Tuple[float, float], Sequence[float], Vector2]
_ColorValue = Union[Color, str, Tuple[int, int, int], List[int], int, Tuple[int, int, int, int]]
_ColorInput = Union[Color, str, List[int], Tuple[int, int, int], Tuple[int, int, int, int]]
_CanBeRect = Union[
    _PgRect,
    Tuple[int, int, int, int],
    List[int],
    Tuple[_Coordinate, _Coordinate],
    List[_Coordinate],
]


class _HasRectAttribute(Protocol):
    rect: _CanBeRect


_RectValue = Union[_CanBeRect, _HasRectAttribute]


@unique
class BlendMode(IntEnum):
    NONE = 0
    ADD = BLEND_RGB_ADD
    SUB = BLEND_RGB_SUB
    MULT = BLEND_RGB_MULT
    MIN = BLEND_RGB_MIN
    MAX = BLEND_RGB_MAX
    RGBA_ADD = BLEND_RGBA_ADD
    RGBA_SUB = BLEND_RGBA_SUB
    RGBA_MULT = BLEND_RGBA_MULT
    RGBA_MIN = BLEND_RGBA_MIN
    RGBA_MAX = BLEND_RGBA_MAX
    PREMULTIPLIED = BLEND_PREMULTIPLIED
    ALPHA_SDL2 = BLEND_ALPHA_SDL2


class Renderer(metaclass=ABCMeta):
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
    def draw(
        self,
        obj: Surface,
        dest: Tuple[float, float],
        /,
        *,
        area: Optional[_PgRect] = None,
        special_flags: BlendMode = BlendMode.NONE,
    ) -> Rect:
        ...

    @overload
    def draw(
        self, obj: Surface, dest: _PgRect, /, *, area: Optional[_PgRect] = None, special_flags: BlendMode = BlendMode.NONE
    ) -> Rect:
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
    def draw_aaline(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        blend: int = 1,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_aalines(
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
        return pg_rect_convert(target.get_rect(**kwargs))

    def get_size(self, /) -> Tuple[float, float]:
        target: Surface = self.__target
        return target.get_size()

    def fill(self, /, color: _ColorInput) -> None:
        target: Surface = self.__target
        target.fill(color)

    @overload
    def draw(
        self,
        obj: Surface,
        dest: Tuple[float, float],
        /,
        *,
        area: Optional[_PgRect] = None,
        special_flags: BlendMode = BlendMode.NONE,
    ) -> Rect:
        ...

    @overload
    def draw(
        self, obj: Surface, dest: _PgRect, /, *, area: Optional[_PgRect] = None, special_flags: BlendMode = BlendMode.NONE
    ) -> Rect:
        ...

    def draw(self, obj: Surface, /, *args: Any, **kwargs: Any) -> Rect:
        target: Surface = self.__target
        return pg_rect_convert(target.blit(obj, *args, **kwargs))

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
        output_rect: _PgRect = _draw_rect(
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
        return pg_rect_convert(output_rect)

    def draw_polygon(
        self,
        /,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: _PgRect = _draw_polygon(surface=target, color=color, points=points, width=width)
        return pg_rect_convert(output_rect)

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
        output_rect: _PgRect = _draw_circle(
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
        return pg_rect_convert(output_rect)

    def draw_ellipse(self, /, color: _ColorValue, rect: _RectValue, width: int = 0) -> Rect:
        target: Surface = self.__target
        output_rect: _PgRect = _draw_ellipse(surface=target, color=color, rect=rect, width=width)
        return pg_rect_convert(output_rect)

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
        output_rect: _PgRect = _draw_arc(
            surface=target, color=color, rect=rect, start_angle=start_angle, stop_angle=stop_angle, width=width
        )
        return pg_rect_convert(output_rect)

    def draw_line(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: _PgRect = _draw_line(surface=target, color=color, start_pos=start_pos, end_pos=end_pos, width=width)
        return pg_rect_convert(output_rect)

    def draw_lines(
        self,
        /,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: _PgRect = _draw_multiple_lines(surface=target, color=color, closed=closed, points=points, width=width)
        return pg_rect_convert(output_rect)

    def draw_aaline(
        self,
        /,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        blend: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: _PgRect = _draw_antialiased_line(
            surface=target, color=color, start_pos=start_pos, end_pos=end_pos, blend=blend
        )
        return pg_rect_convert(output_rect)

    def draw_aalines(
        self,
        /,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        blend: int = 1,
    ) -> Rect:
        target: Surface = self.__target
        output_rect: _PgRect = _draw_multiple_antialiased_lines(
            surface=target, color=color, closed=closed, points=points, blend=blend
        )
        return pg_rect_convert(output_rect)

    @property
    def surface(self, /) -> Surface:
        return self.__target
