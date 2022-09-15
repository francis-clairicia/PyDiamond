# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's math module"""

from __future__ import annotations

__all__ = [
    "Vector2",
    "angle_interpolation",
    "compute_rect_from_edges",
    "compute_size_from_edges",
    "linear_interpolation",
]


############ Package initialization ############
from .area import *
from .interpolation import *
from .vector2 import *
