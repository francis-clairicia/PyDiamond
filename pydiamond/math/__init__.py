# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's math module"""

from __future__ import annotations

__all__ = [
    "ImmutableRect",
    "Rect",
    "Vector2",
    "angle_interpolation",
    "compute_edges_from_rect",
    "compute_rect_from_edges",
    "compute_size_from_edges",
    "do_intersect",
    "get_edges_center",
    "is_inside_polygon",
    "linear_interpolation",
    "normalize_points",
    "on_segment",
    "orientation",
    "rotate_points",
]


############ Package initialization ############
from .area import *
from .interpolation import *
from .intersection import *
from .rect import *
from .vector2 import *
