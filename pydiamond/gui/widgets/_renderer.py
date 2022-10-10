# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Widget's Renderer view module"""

from __future__ import annotations

__all__ = ["WidgetRendererView"]

from typing import TYPE_CHECKING, Any, ContextManager, Iterable, Literal, Sequence, final, overload

from ...graphics.renderer import AbstractRenderer
from ...math.rect import Rect
from ...system.utils.typing import reflect_method_signature

if TYPE_CHECKING:
    from pygame._common import _CanBeRect, _ColorValue, _Coordinate  # pyright: reportMissingModuleSource=false

    from ...graphics.surface import Surface
    from .abc import AbstractWidget


@final
class WidgetRendererView(AbstractRenderer):
    __slots__ = ("__rect", "__target")

    def __init__(self, widget: AbstractWidget, target: AbstractRenderer) -> None:
        super().__init__()
        requested_clip = widget.get_clip()
        self.__rect: Rect = requested_clip.clip(widget.get_rect())
        self.__target: AbstractRenderer = target

    def __clip_rect(self, rect: _CanBeRect | None) -> Rect:
        if rect is None:
            return self.__rect.copy()
        if not isinstance(rect, Rect):
            rect = Rect(*rect)
        return rect.clip(self.__rect)

    def get_rect(self, **kwargs: float | Sequence[float]) -> Rect:
        return self.__target.get_rect(**kwargs)

    def get_size(self) -> tuple[float, float]:
        return self.__target.get_size()

    def get_width(self) -> float:
        return self.__target.get_width()

    def get_height(self) -> float:
        return self.__target.get_height()

    def fill(self, color: _ColorValue, rect: _CanBeRect | None = None) -> Rect:
        return self.__target.fill(color, rect=rect)

    def get_clip(self) -> Rect:
        return self.__target.get_clip()

    def using_clip(self, rect: _CanBeRect | None) -> ContextManager[None]:
        return self.__target.using_clip(self.__clip_rect(rect))

    @reflect_method_signature(AbstractRenderer.draw_surface)
    def draw_surface(self, *args: Any, **kwargs: Any) -> Rect:
        return self.__target.draw_surface(*args, **kwargs)

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[True] = ...,
    ) -> list[Rect]:
        ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: Literal[False],
    ) -> None:
        ...

    @overload
    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool,
    ) -> list[Rect] | None:
        ...

    def draw_many_surfaces(
        self,
        sequence: Iterable[
            tuple[Surface, _Coordinate | _CanBeRect]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None]
            | tuple[Surface, _Coordinate | _CanBeRect, _CanBeRect | None, int]
        ],
        doreturn: bool = True,
    ) -> list[Rect] | None:
        return self.__target.draw_many_surfaces(sequence, doreturn)

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
