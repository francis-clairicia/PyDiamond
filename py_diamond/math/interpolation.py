# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Interpolation utils module"""

__all__ = ["angle_interpolation", "linear_interpolation"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


def angle_interpolation(start: float, end: float, alpha: float) -> float:
    if start == end:
        return start
    if not (0 <= alpha <= 1):
        raise ValueError("Invalid 'alpha' value range")
    shortest_angle = ((end - start) + 180) % 360 - 180
    return (start + shortest_angle * alpha) % 360


def linear_interpolation(start: float, end: float, alpha: float) -> float:
    if start == end:
        return start
    if not (0 <= alpha <= 1):
        raise ValueError("Invalid 'alpha' value range")
    return start * (1.0 - alpha) + end * alpha
