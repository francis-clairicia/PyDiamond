# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""
Low-level image transformation functions module
"""

from __future__ import annotations

__all__ = ["rotozoom2", "scale_by"]

from typing import TYPE_CHECKING

from pygame.transform import rotozoom as _rotozoom, scale_by as _scale, smoothscale_by as _smoothscale

if TYPE_CHECKING:
    from pygame.surface import Surface


def scale_by(
    surface: Surface,
    factor: tuple[float, float],
    *,
    smooth: bool = False,
) -> Surface:
    factor_x, factor_y = factor
    if factor_x == factor_y:
        return _rotozoom(surface, 0, factor_x)
    scale = _scale if not smooth else _smoothscale
    return scale(surface, (factor_x, factor_y))


def rotozoom2(
    surface: Surface,
    angle: float,
    scale: tuple[float, float],
    *,
    smooth: bool = False,
) -> Surface:
    scale_x, scale_y = scale
    if scale_x == scale_y:
        return _rotozoom(surface, angle, scale_x)
    scale_func = _scale if not smooth else _smoothscale
    surface = scale_func(surface, (scale_x, scale_y))
    return _rotozoom(surface, angle, 1)
