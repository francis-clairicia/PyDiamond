# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's graphics module"""

from __future__ import annotations

__all__ = [
    "AbstractCircleShape",
    "AbstractCrossShape",
    "AbstractRectangleShape",
    "AbstractRenderer",
    "AbstractShape",
    "AnimatedSprite",
    "AnimationInterpolator",
    "AnimationInterpolatorPool",
    "BLACK",
    "BLUE",
    "BLUE_DARK",
    "BLUE_LIGHT",
    "BaseAnimation",
    "BaseDrawableGroup",
    "BaseLayeredDrawableGroup",
    "BooleanCheckBox",
    "Button",
    "ButtonMeta",
    "COLOR_DICT",
    "CYAN",
    "CheckBox",
    "CheckBoxMeta",
    "CircleShape",
    "ClassWithThemeNamespace",
    "ClassWithThemeNamespaceMeta",
    "Color",
    "DiagonalCrossShape",
    "Drawable",
    "DrawableGroup",
    "DrawableMeta",
    "Entry",
    "EntryMeta",
    "Font",
    "Form",
    "FormMeta",
    "GRAY",
    "GRAY_DARK",
    "GRAY_LIGHT",
    "GREEN",
    "GREEN_DARK",
    "GREEN_LIGHT",
    "GradientShape",
    "Grid",
    "GridElement",
    "HorizontalGradientShape",
    "HorizontalMultiColorShape",
    "Image",
    "ImageButton",
    "ImmutableColor",
    "ImmutableRect",
    "LayeredDrawableGroup",
    "LayeredSpriteGroup",
    "MAGENTA",
    "MDrawable",
    "MDrawableMeta",
    "Mask",
    "Movable",
    "MovableMeta",
    "MovableProxy",
    "MovableProxyMeta",
    "MoveAnimation",
    "MultiColorShape",
    "NoTheme",
    "ORANGE",
    "OutlinedShape",
    "PURPLE",
    "PlusCrossShape",
    "PolygonShape",
    "ProgressBar",
    "ProgressBarMeta",
    "RED",
    "RED_DARK",
    "RED_LIGHT",
    "RadialGradientShape",
    "Rect",
    "RectangleShape",
    "ScaleBar",
    "ScrollArea",
    "ScrollAreaElement",
    "ScrollBar",
    "ScrollBarMeta",
    "ShapeMeta",
    "SingleColorShape",
    "Sprite",
    "SpriteGroup",
    "SquaredGradientShape",
    "SupportsDrawableGroups",
    "SupportsDrawing",
    "Surface",
    "SurfaceRenderer",
    "SysFont",
    "TDrawable",
    "TDrawableMeta",
    "TRANSPARENT",
    "Text",
    "TextImage",
    "TextMeta",
    "ThemeNamespace",
    "ThemeType",
    "ThemedObject",
    "ThemedObjectMeta",
    "TransformAnimation",
    "Transformable",
    "TransformableMeta",
    "TransformableProxy",
    "TransformableProxyMeta",
    "VerticalGradientShape",
    "VerticalMultiColorShape",
    "WHITE",
    "YELLOW",
    "abstract_theme_class",
    "closed_namespace",
    "create_surface",
    "force_apply_theme_decorator",
    "load_image",
    "no_theme_decorator",
    "save_image",
    "set_default_theme_namespace",
]

import os
import typing

import pygame

############ pygame graphics initialization ############
if pygame.version.vernum < (2, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'", name=__name__, path=__file__)

SDL_IMAGE_VERSION = typing.cast(tuple[int, int, int], pygame.image.get_sdl_image_version())

if SDL_IMAGE_VERSION is None:
    raise ImportError("SDL_image library is not loaded", name=__name__, path=__file__)

if SDL_IMAGE_VERSION < (2, 0, 0):
    raise ImportError(
        "Your SDL_image version is too old: '{0}.{1}.{2}' < '2.0.0'".format(*SDL_IMAGE_VERSION),
        name=__name__,
        path=__file__,
    )

pygame.transform.set_smoothscale_backend(
    os.environ.setdefault("PYGAME_SMOOTHSCALE_BACKEND", pygame.transform.get_smoothscale_backend())
)

############ Cleanup ############
del os, typing, pygame


############ Package initialization ############
from .animation import *
from .button import *
from .checkbox import *
from .color import *
from .drawable import *
from .entry import *
from .font import *
from .form import *
from .gradients import *
from .grid import *
from .image import *
from .movable import *
from .progress import *
from .rect import *
from .renderer import *
from .scale import *
from .scroll import *
from .shape import *
from .sprite import *
from .surface import *
from .text import *
from .theme import *
from .transformable import *
