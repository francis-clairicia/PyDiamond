# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""
Low-level drawing functions module

The goal is to implement anti-aliased shape drawing (WITH outline thickness).
The existing functions allow only a width of 1 for anti-aliased shapes, and this is not funny.

The goal is to implement pygame.gfxdraw (which uses SDL_gfx) if this is not deprecated in further pygame releases.
(or at least manipulate pygame.draw.aa* functions in order to create thick shapes)

Currently pygame.gfxdraw isn't working with 32-bits per-pixel alpha surfaces, used by *ALL* the PyDiamond system x')

Therefore, by default this module only exposes the pygame.draw functions.
"""

from __future__ import annotations

__all__ = [
    "HAS_GFXDRAW",
    "draw_arc",
    "draw_circle",
    "draw_ellipse",
    "draw_line",
    "draw_lines",
    "draw_polygon",
    "draw_rect",
]

HAS_GFXDRAW = False

from pygame.draw import (
    arc as draw_arc,
    circle as draw_circle,
    ellipse as draw_ellipse,
    line as draw_line,
    lines as draw_lines,
    polygon as draw_polygon,
    rect as draw_rect,
)
