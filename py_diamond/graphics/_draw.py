# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""
Low-level drawing functions module

The goal is to implement anti-aliased shape drawing (WITH outline thickness).
The existing functions allow only a width of 1 for anti-aliased shapes, and this is not funny.

The goal is to implement pygame.gfxdraw (which uses SDL_gfx) if this is not deprecated in further pygame releases.
(or at least manipulate pygame.draw.aa* functions in order to create thick shapes)

Currently pygame.gfxdraw isn't working with 32-bits per-pixel alpha surfaces, used by *ALL* the PyDiamond system x')

Therefore, by default this module only exposes the pygame.draw functions.
"""

from __future__ import annotations

__all__ = [
    "HAS_GFXDRAW",
    "draw_arc",
    "draw_circle",
    "draw_ellipse",
    "draw_line",
    "draw_lines",
    "draw_polygon",
    "draw_rect",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os
from typing import TYPE_CHECKING, Sequence

if TYPE_CHECKING:
    from pygame._common import _ColorValue, _Coordinate  # pyright: reportMissingModuleSource=false


try:
    import pygame.gfxdraw

    del pygame

    if __name__ != "__main__" and os.environ.get("PYDIAMOND_GFXDRAW", "0") != "1":
        raise ImportError
except ImportError:
    HAS_GFXDRAW = False

    from pygame.draw import circle as draw_circle, line as draw_line, lines as draw_lines, polygon as draw_polygon

else:
    HAS_GFXDRAW = True

    from collections import deque
    from itertools import chain, pairwise
    from math import atan2, cos, sin
    from typing import NamedTuple

    from pygame.gfxdraw import (
        aacircle as __gfx_draw_circle_outline,
        aapolygon as __gfx_draw_polygon_outline,
        filled_circle as __gfx_draw_filled_circle,
        filled_polygon as __gfx_draw_filled_polygon,
        line as __gfx_draw_line,
    )

    try:
        from ..math.vector2 import Vector2
        from ..system.utils.functools import lru_cache
        from .rect import Rect
    except ImportError:
        from functools import lru_cache  # type: ignore[no-redef]

        from pygame import Rect, Vector2

    if TYPE_CHECKING:
        from .surface import Surface

    class _LineEdges(NamedTuple):
        upper_left: tuple[float, float]
        upper_right: tuple[float, float]
        bottom_right: tuple[float, float]
        bottom_left: tuple[float, float]

    @lru_cache(maxsize=128)
    def __compute_line_edges(
        X0: tuple[float, float],
        X1: tuple[float, float],
        thickness: float,
    ) -> _LineEdges:
        center_L1 = (X0[0] + X1[0]) / 2, (X0[1] + X1[1]) / 2
        length = (Vector2(X1) - Vector2(X0)).length()
        angle = atan2(X0[1] - X1[1], X0[0] - X1[0])

        UL = (
            center_L1[0] + (length / 2.0) * cos(angle) - (thickness / 2.0) * sin(angle),
            center_L1[1] + (thickness / 2.0) * cos(angle) + (length / 2.0) * sin(angle),
        )
        UR = (
            center_L1[0] - (length / 2.0) * cos(angle) - (thickness / 2.0) * sin(angle),
            center_L1[1] + (thickness / 2.0) * cos(angle) - (length / 2.0) * sin(angle),
        )
        BL = (
            center_L1[0] + (length / 2.0) * cos(angle) + (thickness / 2.0) * sin(angle),
            center_L1[1] - (thickness / 2.0) * cos(angle) + (length / 2.0) * sin(angle),
        )
        BR = (
            center_L1[0] - (length / 2.0) * cos(angle) + (thickness / 2.0) * sin(angle),
            center_L1[1] - (thickness / 2.0) * cos(angle) - (length / 2.0) * sin(angle),
        )
        return _LineEdges(UL, UR, BR, BL)

    @lru_cache(maxsize=4096)
    def __intersection(
        a1: tuple[float, float],
        a2: tuple[float, float],
        b1: tuple[float, float],
        b2: tuple[float, float],
    ) -> tuple[float, float] | None:
        try:
            slope_a: float | None
            slope_a = (a2[1] - a1[1]) / (a2[0] - a1[0])
            intercept_a: float = (a1[1]) - slope_a * (a1[0])
        except ZeroDivisionError:
            slope_a = None
            intercept_a = 0
        try:
            slope_b: float | None
            slope_b = (b2[1] - b1[1]) / (b2[0] - b1[0])
            intercept_b: float = (b1[1]) - slope_b * (b1[0])
        except ZeroDivisionError:
            slope_b = None
            intercept_b = 0

        if slope_a is slope_b or slope_a == slope_b:  # Parallel lines
            return None

        slope_x: float
        intercept_x: float
        x: float
        if slope_a is not None and slope_b is not None:
            x = (intercept_b - intercept_a) / (slope_a - slope_b)
            slope_x = slope_a
            intercept_x = intercept_a
        elif slope_b is not None:
            x = a1[0]
            slope_x = slope_b
            intercept_x = intercept_b
        elif slope_a is not None:
            x = b1[0]
            slope_x = slope_a
            intercept_x = intercept_a
        else:
            return None

        y: float = slope_x * x + intercept_x
        return x, y

    def draw_line(
        surface: Surface,
        color: _ColorValue,
        start_pos: _Coordinate,
        end_pos: _Coordinate,
        width: int = 1,
    ) -> Rect:
        width = int(width)
        if width < 2:
            start_pos = int(start_pos[0]), int(start_pos[1])
            end_pos = int(end_pos[0]), int(end_pos[1])
            if width == 1:
                __gfx_draw_line(surface, *start_pos, *end_pos, color)
            left: float = min(start_pos[0], end_pos[0])
            top: float = min(start_pos[1], end_pos[1])
            return Rect(
                left,
                top,
                max(start_pos[0], end_pos[0]) - left + 1,
                max(start_pos[1], end_pos[1]) - top + 1,
            )

        start_pos = start_pos[0], start_pos[1]
        end_pos = end_pos[0], end_pos[1]
        edges = __compute_line_edges(start_pos, end_pos, width)

        __gfx_draw_polygon_outline(surface, edges, color)
        __gfx_draw_filled_polygon(surface, edges, color)

        left = min(pos[0] for pos in edges)
        top = min(pos[1] for pos in edges)
        return Rect(
            left,
            top,
            max(pos[0] for pos in edges) - left + 2,
            max(pos[1] for pos in edges) - top + 2,
        )

    def draw_lines(
        surface: Surface,
        color: _ColorValue,
        closed: bool,
        points: Sequence[_Coordinate],
        width: int = 1,
    ) -> Rect:
        if len(points) < 2:
            raise ValueError("Must have 2 points minimum")
        final_rect: Rect | None = None
        for start_pos, end_pos in pairwise(points):
            line_rect = draw_line(surface, color, start_pos, end_pos, width=width)
            if final_rect is None:
                final_rect = line_rect
            else:
                final_rect.union_ip(line_rect)
        assert final_rect is not None
        if closed and len(points) > 2:
            line_rect = draw_line(surface, color, points[-1], points[0], width=width)
            final_rect.union_ip(line_rect)
        return final_rect

    # There is issues with growing points and computing the missing edges (with a large width)
    def draw_polygon(
        surface: Surface,
        color: _ColorValue,
        points: Sequence[_Coordinate],
        width: int = 0,
    ) -> Rect:
        if len(points) < 3:
            raise ValueError("Must have 3 points minimum")
        if width < 2:
            __gfx_draw_polygon_outline(surface, points, color)
            if width < 1:
                __gfx_draw_filled_polygon(surface, points, color)
            left: float = min(pos[0] for pos in points)
            top: float = min(pos[1] for pos in points)
            return Rect(
                left,
                top,
                max(pos[0] for pos in points) - left + 1,
                max(pos[1] for pos in points) - top + 2,
            )
        vertices_list: deque[_LineEdges] = deque(
            __compute_line_edges((start_pos[0], start_pos[1]), (end_pos[0], end_pos[1]), width)
            for start_pos, end_pos in pairwise(chain(points, [points[0]]))
        )
        for vertices in vertices_list:
            __gfx_draw_polygon_outline(surface, vertices, color)
            __gfx_draw_filled_polygon(surface, vertices, color)
        if width > 2:
            points_edge_polygons: deque[Sequence[tuple[float, float]]] = deque()
            for v1, v2 in pairwise(chain(vertices_list, [vertices_list[0]])):
                p = (
                    __intersection(v1.upper_left, v1.upper_right, v2.upper_left, v2.upper_right),
                    __intersection(v1.bottom_left, v1.bottom_right, v2.upper_left, v2.upper_right),
                    __intersection(v1.bottom_left, v1.bottom_right, v2.bottom_left, v2.bottom_right),
                    __intersection(v1.upper_left, v1.upper_right, v2.bottom_left, v2.bottom_right),
                )
                if any(point is None for point in p):
                    continue
                points_edge_polygons.append(p)  # type: ignore[arg-type]
            for points in points_edge_polygons:
                __gfx_draw_polygon_outline(surface, points, color)
                __gfx_draw_filled_polygon(surface, points, color)
        else:
            points_edge_polygons = vertices_list  # type: ignore[assignment]
        left = min((pos[0] for edges in points_edge_polygons for pos in edges), default=0)
        top = min((pos[1] for edges in points_edge_polygons for pos in edges), default=0)
        return Rect(
            left,
            top,
            max((pos[0] for edges in points_edge_polygons for pos in edges), default=0) - left + 1,
            max((pos[1] for edges in points_edge_polygons for pos in edges), default=0) - top + 2,
        )

    from pygame.draw import circle as __default_draw_circle

    def draw_circle(
        surface: Surface,
        color: _ColorValue,
        center: _Coordinate,
        radius: float,
        width: int = 0,
        draw_top_right: bool | None = None,
        draw_top_left: bool | None = None,
        draw_bottom_left: bool | None = None,
        draw_bottom_right: bool | None = None,
    ) -> Rect:
        if not all(draw is None or draw for draw in (draw_top_left, draw_top_right, draw_bottom_left, draw_bottom_right)):
            # TODO: Handle it with gfxdraw
            return __default_draw_circle(
                surface=surface,
                color=color,
                center=center,
                radius=radius,
                width=width,
                draw_top_right=draw_top_right,
                draw_top_left=draw_top_left,
                draw_bottom_left=draw_bottom_left,
                draw_bottom_right=draw_bottom_right,
            )
        width = int(width)
        x, y = int(center[0]), int(center[1])
        radius = int(radius)
        __gfx_draw_circle_outline(surface, x, y, radius, color)
        if width < 1:
            __gfx_draw_filled_circle(surface, x, y, radius, color)
        elif width > 1:
            center = Vector2(x + (width % 2), y + (width % 2))
            radius_vector = Vector2(radius - round(width / 2), 0)
            points = deque(center + radius_vector.rotate(-i) for i in range(0, 360))
            __gfx_draw_circle_outline(surface, x, y, radius - width, color)
            return draw_lines(surface, color, True, points, width=width)
        rect = Rect((0, 0), (radius * 2 + 1, radius * 2 + 1))
        rect.center = x, y
        return rect


from pygame.draw import arc as draw_arc, ellipse as draw_ellipse, rect as draw_rect  # TODO: Implement with pygame.gfxdraw

# Check if all functions are available
try:
    draw_arc
    draw_ellipse
    draw_rect
    draw_line
    draw_lines
    draw_polygon
    draw_circle
except NameError:
    raise ImportError("Missing functions to implement from pygame.draw and pygame.gfxdraw", name=__name__, path=__file__)


if __name__ == "__main__":
    # Main used only for test, it will disappear some day

    import os.path
    import sys

    sys.path[0] = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

    from py_diamond.graphics.shape import DiagonalCrossShape

    import pygame as pg
    from pygame import Surface, gfxdraw

    def main() -> None:
        pg.init()

        screen = pg.display.set_mode((1366, 768), depth=32)

        # gfxdraw.arc(screen, 320, 240, 101, 0, 45, pg.Color("red"))
        # gfxdraw.pie(screen, 320, 240, 101, 0, 45, pg.Color("red"))

        # draw_polygon(screen, pg.Color("green"), [(40, 40), (200, 400), (600, 100)], width=20)
        # rect = draw_polygon(screen, pg.Color("green"), [(40, 40), (200, 400), (600, 100)], width=40)
        # rect = draw_polygon(screen, pg.Color("green"), [(40, 40), (200, 400), (600, 100)], width=2)
        # rect = draw_polygon(screen, pg.Color("green"), [(40, 40), (200, 400), (600, 100)], width=3)
        # gfxdraw.rectangle(screen, rect, pg.Color("yellow"))
        # draw_polygon(screen, pg.Color("green"), [(40, 40), (200, 400), (600, 100)], width=10)

        points = DiagonalCrossShape.get_cross_points((300, 300), 40)
        # points = PlusCrossShape.get_cross_points((300, 300), 40)

        for p in points:
            p.x += 100
            p.y += 100

        draw_polygon(screen, pg.Color("green"), points)
        rect = draw_polygon(screen, pg.Color("yellow"), points, width=10)
        draw_polygon(screen, pg.Color("red"), points, width=3)
        gfxdraw.rectangle(screen, rect, pg.Color("blue"))

        # rect = draw_circle(screen, pg.Color(255, 0, 0, 127), (320, 240), 101)
        # rect = draw_circle(screen, pg.Color(0, 127, 0, 127), (320, 240), 101)
        # rect = draw_circle(screen, pg.Color("yellow"), (320, 240), 101, width=20)
        # rect = draw_circle(screen, pg.Color("yellow"), (320, 240), 101, width=30)
        # draw_aacircle(screen, 320, 240, 101, pg.Color("blue"), width=1)
        # rect = draw_line(screen, pg.Color("yellow"), (100, 100), (500, 300), width=20)

        # gfxdraw.rectangle(screen, rect, pg.Color("blue"))

        screen.blit(screen, (0, 0))
        pg.display.flip()

        while True:
            if pg.event.wait().type == pg.QUIT:
                break

        pg.quit()

    main()
