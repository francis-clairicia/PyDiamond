# -*- coding: Utf-8 -*-
# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Interpolation utils module

Source from:
- https://www.geeksforgeeks.org/check-if-two-given-line-segments-intersect/
- https://www.geeksforgeeks.org/how-to-check-if-a-given-point-lies-inside-a-polygon/
"""

from __future__ import annotations

__all__ = ["do_intersect", "is_inside_polygon", "on_segment", "orientation"]

import sys
from typing import Literal, Sequence, TypeAlias

from .vector2 import Vector2

_FPoint: TypeAlias = tuple[float, float]


def on_segment(p: _FPoint | Vector2, q: _FPoint | Vector2, r: _FPoint | Vector2) -> bool:
    """
    Given three collinear points p, q, r,
    the function checks if point q lies
    on line segment 'pr'
    """

    return (q[0] <= max(p[0], r[0])) and (q[0] >= min(p[0], r[0])) and (q[1] <= max(p[1], r[1])) and (q[1] >= min(p[1], r[1]))


def orientation(p: _FPoint | Vector2, q: _FPoint | Vector2, r: _FPoint | Vector2) -> Literal[0, 1, 2]:
    """
    To find orientation of ordered triplet (p, q, r).
    The function returns following values
    0 --> p, q and r are collinear
    1 --> Clockwise
    2 --> Counterclockwise
    """

    val = ((q[1] - p[1]) * (r[0] - q[0])) - ((q[0] - p[0]) * (r[1] - q[1]))

    if val == 0:
        return 0
    if val > 0:
        return 1
    return 2


def do_intersect(p1: _FPoint | Vector2, q1: _FPoint | Vector2, p2: _FPoint | Vector2, q2: _FPoint | Vector2) -> bool:

    # Find the four orientations needed for
    # general and special cases
    o1 = orientation(p1, q1, p2)
    o2 = orientation(p1, q1, q2)
    o3 = orientation(p2, q2, p1)
    o4 = orientation(p2, q2, q1)

    # General case
    if (o1 != o2) and (o3 != o4):
        return True

    # Special Cases
    # p1, q1 and p2 are collinear and
    # p2 lies on segment p1q1
    if (o1 == 0) and (on_segment(p1, p2, q1)):
        return True

    # p1, q1 and p2 are collinear and
    # q2 lies on segment p1q1
    if (o2 == 0) and (on_segment(p1, q2, q1)):
        return True

    # p2, q2 and p1 are collinear and
    # p1 lies on segment p2q2
    if (o3 == 0) and (on_segment(p2, p1, q2)):
        return True

    # p2, q2 and q1 are collinear and
    # q1 lies on segment p2q2
    if (o4 == 0) and (on_segment(p2, q1, q2)):
        return True

    return False


def is_inside_polygon(points: Sequence[_FPoint] | Sequence[Vector2], p: _FPoint | Vector2) -> bool:
    """
    Returns true if the point p lies
    inside the polygon[] with n vertices
    """

    n = len(points)

    # There must be at least 3 vertices
    # in polygon
    if n < 3:
        return False

    # Create a point for line segment
    # from p to infinite
    extreme: _FPoint = (sys.maxsize - 1, p[1])

    # To count number of points in polygon
    # whose y-coordinate is equal to
    # y-coordinate of the point
    decrease: int = 0
    count: int = 0
    i: int = 0

    while True:
        next: int = (i + 1) % n

        if points[i][1] == p[1]:
            decrease += 1

        # Check if the line segment from 'p' to
        # 'extreme' intersects with the line
        # segment from 'polygon[i]' to 'polygon[next]'
        if do_intersect(points[i], points[next], p, extreme):

            # If the point 'p' is collinear with line
            # segment 'i-next', then check if it lies
            # on segment. If it lies, return true, otherwise false
            if orientation(points[i], p, points[next]) == 0:
                return on_segment(points[i], p, points[next])

            count += 1

        i = next

        if i == 0:
            break

    # Reduce the count by decrease amount
    # as these points would have been added twice
    count -= decrease

    # Return true if count is odd, false otherwise
    return count % 2 == 1
