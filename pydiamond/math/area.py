# -*- coding: Utf-8 -*-


from __future__ import annotations

__all__ = ["compute_edges_from_rect", "compute_rect_from_edges", "compute_size_from_edges", "normalize_points"]

from typing import Sequence, TypeAlias

from .rect import Rect
from .vector2 import Vector2

_FPoint: TypeAlias = tuple[float, float]


def compute_rect_from_edges(edges: Sequence[_FPoint] | Sequence[Vector2]) -> tuple[float, float, float, float]:
    # TODO: FRect
    if not edges:
        return 0, 0, 0, 0
    if len(edges) < 2:
        point = edges[0]
        return point[0], point[1], 1, 1

    left = right = edges[0][0]
    top = bottom = edges[0][1]

    for point in edges:
        left = point[0] if point[0] < left else left
        right = point[0] if point[0] > right else right
        top = point[1] if point[1] < top else top
        bottom = point[1] if point[1] > bottom else bottom

    return left, top, right - left + 1, bottom - top + 1


def compute_size_from_edges(edges: Sequence[_FPoint] | Sequence[Vector2]) -> tuple[float, float]:
    _, _, w, h = compute_rect_from_edges(edges)

    return w, h


def compute_edges_from_rect(
    rect: Rect,
    angle: float = 0,
    *,
    normalize: bool = False,
) -> tuple[()] | tuple[Vector2, Vector2, Vector2, Vector2]:
    if rect.width <= 0 or rect.height <= 0:
        return ()

    left: float = rect.left
    right: float = rect.right - 1
    top: float = rect.top
    bottom: float = rect.bottom - 1

    center = Vector2((left + right) / 2, (top + bottom) / 2)

    topleft = (left, top)
    topright = (right, top)
    bottomleft = (left, bottom)
    bottomright = (right, bottom)

    points = rotate_points((topleft, topright, bottomright, bottomleft), angle, center)
    if normalize:
        normalize_points(points)

    return points  # type: ignore[return-value]


def normalize_points(points: Sequence[Vector2]) -> tuple[float, float]:
    if not points:
        return 0, 0
    left, top, width, height = compute_rect_from_edges(points)
    for p in points:
        p.x -= left
        p.y -= top
    return width, height


def rotate_points(
    points: Sequence[_FPoint] | Sequence[Vector2],
    angle: float,
    pivot: _FPoint | Vector2 | None = None,
) -> Sequence[Vector2]:
    if not points:
        return ()
    if pivot is None:
        left, top, width, height = compute_rect_from_edges(points)
        pivot = Vector2((left + width - 1) / 2, (top + height - 1) / 2)
    else:
        pivot = Vector2(pivot)
    return tuple(pivot + (Vector2(point) - pivot).rotate(-angle) for point in points)
