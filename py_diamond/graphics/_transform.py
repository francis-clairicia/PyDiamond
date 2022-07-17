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

from pygame.transform import rotozoom as _rotozoom, scale as _scale, smoothscale as _smoothscale

if TYPE_CHECKING:
    from pygame.surface import Surface


# TODO (pygame 2.1.3): pygame.transform.scale_by() :)
def scale_by(
    surface: Surface,
    factor: float | tuple[float, float],
    *,
    smooth: bool = False,
) -> Surface:
    factor_x: float
    factor_y: float
    try:
        factor_x, factor_y = factor  # type: ignore[misc]
    except TypeError:  # Single number
        return _rotozoom(surface, 0, factor)  # type: ignore[arg-type]
    if factor_x == factor_y:
        return _rotozoom(surface, 0, factor_x)
    w, h = surface.get_size()
    scale = _scale if not smooth else _smoothscale
    return scale(surface, (w * factor_x, h * factor_y))


def rotozoom2(
    surface: Surface,
    angle: float,
    scale: float | tuple[float, float],
    *,
    smooth: bool = False,
) -> Surface:
    scale_x: float
    scale_y: float
    try:
        scale_x, scale_y = scale  # type: ignore[misc]
    except TypeError:  # Single number
        return _rotozoom(surface, angle, scale)  # type: ignore[arg-type]
    if scale_x == scale_y:
        return _rotozoom(surface, angle, scale_x)
    w, h = surface.get_size()
    scale_func = _scale if not smooth else _smoothscale
    surface = scale_func(surface, (w * scale_x, h * scale_y))
    return _rotozoom(surface, angle, 1)
