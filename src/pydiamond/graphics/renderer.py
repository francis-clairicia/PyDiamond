# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""AbstractRenderer module"""

from __future__ import annotations

__all__ = ["AbstractRenderer", "RendererView"]

from abc import abstractmethod
from collections.abc import Iterable, Sequence
from enum import IntEnum, auto, unique
from itertools import starmap
from typing import TYPE_CHECKING, Any, ContextManager, Literal, TypeAlias, overload

import pygame.constants as _pg_constants

from ..math.rect import Rect
from ..system.object import Object
from ..system.utils.abc import concreteclass
from ..system.utils.itertools import consume
from ..system.utils.typing import reflect_method_signature

if TYPE_CHECKING:
    from pygame._common import ColorValue, Coordinate, RectValue, _CanBeRect

    from .font import _TextFont
    from .surface import Surface


RendererAnchor: TypeAlias = Literal[
    "topleft",
    "topright",
    "bottomleft",
    "bottomright",
    "midleft",
    "midright",
    "midtop",
    "midbottom",
    "center",
]


@unique
class BlendMode(IntEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        constant_name = f"BLEND_{name}"
        return getattr(_pg_constants, constant_name)  # noqa: F821

    NONE = 0
    RGB_ADD = auto()
    RGB_SUB = auto()
    RGB_MULT = auto()
    RGB_MIN = auto()
    RGB_MAX = auto()
    RGBA_ADD = auto()
    RGBA_SUB = auto()
    RGBA_MULT = auto()
    RGBA_MIN = auto()
    RGBA_MAX = auto()
    PREMULTIPLIED = auto()
    ALPHA_SDL2 = auto()


class AbstractRenderer(Object):
    __slots__ = ()

    @abstractmethod
    def get_rect(self, **kwargs: Any) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @abstractmethod
    def get_width(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def get_height(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def fill(self, color: ColorValue, rect: _CanBeRect | None = ...) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def get_clip(self) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def using_clip(self, rect: _CanBeRect | None) -> ContextManager[None]:
        raise NotImplementedError

    @abstractmethod
    def to_surface(self, surface: Surface | None = ..., area: _CanBeRect | None = ...) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def draw_surface(
        self,
        surface: Surface,
        dest: Coordinate | _CanBeRect,
        area: _CanBeRect | None = ...,
        special_flags: int = ...,
        anchor: RendererAnchor = ...,
    ) -> Rect:
        raise NotImplementedError

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[True] = ...,
    ) -> list[Rect]: ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[False],
    ) -> None: ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool,
    ) -> list[Rect] | None: ...

    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool = True,
    ) -> list[Rect] | None:
        draw = self.draw_surface
        if doreturn:
            return list(starmap(draw, sequence))
        consume(starmap(draw, sequence))
        return None

    @abstractmethod
    def draw_text(
        self,
        text: str,
        font: _TextFont,
        dest: Coordinate | _CanBeRect,
        fgcolor: ColorValue,
        bgcolor: ColorValue | None = ...,
        style: int = ...,
        rotation: int = ...,
        size: float = ...,
        anchor: RendererAnchor = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_rect(
        self,
        color: ColorValue,
        rect: RectValue,
        width: int = ...,
        border_radius: int = ...,
        border_top_left_radius: int = ...,
        border_top_right_radius: int = ...,
        border_bottom_left_radius: int = ...,
        border_bottom_right_radius: int = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_polygon(
        self,
        color: ColorValue,
        points: Sequence[Coordinate],
        width: int = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_circle(
        self,
        color: ColorValue,
        center: Coordinate,
        radius: float,
        width: int = ...,
        draw_top_right: bool = ...,
        draw_top_left: bool = ...,
        draw_bottom_left: bool = ...,
        draw_bottom_right: bool = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_ellipse(self, color: ColorValue, rect: RectValue, width: int = ...) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_arc(
        self,
        color: ColorValue,
        rect: RectValue,
        start_angle: float,
        stop_angle: float,
        width: int = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_line(
        self,
        color: ColorValue,
        start_pos: Coordinate,
        end_pos: Coordinate,
        width: int = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_lines(
        self,
        color: ColorValue,
        closed: bool,
        points: Sequence[Coordinate],
        width: int = ...,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_aaline(
        self,
        color: ColorValue,
        start_pos: Coordinate,
        end_pos: Coordinate,
    ) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def draw_aalines(
        self,
        color: ColorValue,
        closed: bool,
        points: Sequence[Coordinate],
    ) -> Rect:
        raise NotImplementedError


@concreteclass
class RendererView(AbstractRenderer):
    __slots__ = ("__target",)

    def __init__(self, target: AbstractRenderer) -> None:
        super().__init__()
        self.__target: AbstractRenderer = target

    def get_rect(self, **kwargs: Any) -> Rect:
        return self.__target.get_rect(**kwargs)

    def get_size(self) -> tuple[float, float]:
        return self.__target.get_size()

    def get_width(self) -> float:
        return self.__target.get_width()

    def get_height(self) -> float:
        return self.__target.get_height()

    def fill(self, color: ColorValue, rect: _CanBeRect | None = None) -> Rect:
        return self.__target.fill(color, rect=rect)

    def get_clip(self) -> Rect:
        return self.__target.get_clip()

    def using_clip(self, rect: _CanBeRect | None) -> ContextManager[None]:
        return self.__target.using_clip(rect)

    @reflect_method_signature(AbstractRenderer.to_surface)
    def to_surface(self, *args: Any, **kwargs: Any) -> Surface:
        return self.__target.to_surface(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_surface)
    def draw_surface(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_surface(*args, **kwargs)

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[True] = ...,
    ) -> list[Rect]: ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[False],
    ) -> None: ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool,
    ) -> list[Rect] | None: ...

    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, Coordinate | _CanBeRect]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool = True,
    ) -> list[Rect] | None:
        return self.__target.draw_many_surfaces(sequence, doreturn)

    @reflect_method_signature(AbstractRenderer.draw_text)
    def draw_text(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_text(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_rect)
    def draw_rect(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_rect(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_polygon)
    def draw_polygon(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_polygon(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_circle)
    def draw_circle(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_circle(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_ellipse)
    def draw_ellipse(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_ellipse(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_arc)
    def draw_arc(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_arc(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_line)
    def draw_line(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_line(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_lines)
    def draw_lines(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_lines(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_aaline)
    def draw_aaline(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_aaline(*args, **kwargs)

    @reflect_method_signature(AbstractRenderer.draw_aalines)
    def draw_aalines(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_aalines(*args, **kwargs)


del _pg_constants
