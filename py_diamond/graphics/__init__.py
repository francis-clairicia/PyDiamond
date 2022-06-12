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

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import copyreg
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

############ Surface pickling register ############
copyreg.pickle(
    pygame.surface.Surface,
    lambda s, serializer=pygame.image.tostring, deserializer=pygame.image.fromstring: (  # type: ignore[misc]
        deserializer,
        (serializer(s, "ARGB"), s.get_size(), "ARGB"),
    ),
)

############ Cleanup ############
del os, typing, pygame, copyreg


############ Package initialization ############
from .animation import AnimationInterpolator, AnimationInterpolatorPool, BaseAnimation, MoveAnimation, TransformAnimation
from .button import Button, ButtonMeta, ImageButton
from .checkbox import BooleanCheckBox, CheckBox, CheckBoxMeta
from .color import (
    BLACK,
    BLUE,
    BLUE_DARK,
    BLUE_LIGHT,
    COLOR_DICT,
    CYAN,
    GRAY,
    GRAY_DARK,
    GRAY_LIGHT,
    GREEN,
    GREEN_DARK,
    GREEN_LIGHT,
    MAGENTA,
    ORANGE,
    PURPLE,
    RED,
    RED_DARK,
    RED_LIGHT,
    TRANSPARENT,
    WHITE,
    YELLOW,
    Color,
    ImmutableColor,
)
from .drawable import (
    BaseDrawableGroup,
    BaseLayeredDrawableGroup,
    Drawable,
    DrawableGroup,
    DrawableMeta,
    LayeredDrawableGroup,
    MDrawable,
    MDrawableMeta,
    SupportsDrawableGroups,
    SupportsDrawing,
    TDrawable,
    TDrawableMeta,
)
from .entry import Entry, EntryMeta
from .font import Font, SysFont
from .form import Form, FormMeta
from .gradients import (
    GradientShape,
    HorizontalGradientShape,
    HorizontalMultiColorShape,
    MultiColorShape,
    RadialGradientShape,
    SquaredGradientShape,
    VerticalGradientShape,
    VerticalMultiColorShape,
)
from .grid import Grid, GridElement
from .image import Image
from .movable import Movable, MovableMeta, MovableProxy
from .progress import ProgressBar, ProgressBarMeta
from .rect import ImmutableRect, Rect
from .renderer import AbstractRenderer
from .scale import ScaleBar
from .scroll import ScrollArea, ScrollAreaElement, ScrollBar, ScrollBarMeta
from .shape import (
    AbstractCircleShape,
    AbstractCrossShape,
    AbstractRectangleShape,
    AbstractShape,
    CircleShape,
    DiagonalCrossShape,
    OutlinedShape,
    PlusCrossShape,
    PolygonShape,
    RectangleShape,
    ShapeMeta,
    SingleColorShape,
)
from .sprite import AnimatedSprite, LayeredSpriteGroup, Mask, Sprite, SpriteGroup
from .surface import Surface, SurfaceRenderer, create_surface, load_image, save_image
from .text import Text, TextImage, TextMeta
from .theme import (
    ClassWithThemeNamespace,
    ClassWithThemeNamespaceMeta,
    NoTheme,
    ThemedObject,
    ThemedObjectMeta,
    ThemeNamespace,
    ThemeType,
    abstract_theme_class,
    closed_namespace,
    force_apply_theme_decorator,
    no_theme_decorator,
    set_default_theme_namespace,
)
from .transformable import Transformable, TransformableMeta, TransformableProxy
