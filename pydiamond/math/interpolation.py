# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Interpolation utils module"""

from __future__ import annotations

__all__ = ["angle_interpolation", "linear_interpolation"]


def angle_interpolation(start: float, end: float, alpha: float) -> float:
    if start == end:
        return start
    assert 0 <= alpha <= 1, "Invalid 'alpha' value range"
    shortest_angle = ((end - start) + 180) % 360 - 180
    return (start + shortest_angle * alpha) % 360


def linear_interpolation(start: float, end: float, alpha: float) -> float:
    if start == end:
        return start
    assert 0 <= alpha <= 1, "Invalid 'alpha' value range"
    return start * (1.0 - alpha) + end * alpha
