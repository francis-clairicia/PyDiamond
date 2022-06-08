# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's math module"""

from __future__ import annotations

__all__ = ["Vector2", "angle_interpolation", "linear_interpolation"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .interpolation import angle_interpolation, linear_interpolation
from .vector2 import Vector2
