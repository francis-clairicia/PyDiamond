# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's math module"""

from __future__ import annotations

__all__ = ["Vector2", "angle_interpolation", "linear_interpolation"]


############ Package initialization ############
from .interpolation import angle_interpolation, linear_interpolation
from .vector2 import Vector2
