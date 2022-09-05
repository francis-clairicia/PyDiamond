# -*- coding: Utf-8 -*-


from __future__ import annotations

__all__ = ["compute_rect_from_edges", "compute_size_from_edges"]

from typing import TYPE_CHECKING, Sequence, TypeAlias

if TYPE_CHECKING:
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
