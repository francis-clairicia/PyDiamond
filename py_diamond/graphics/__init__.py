# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's graphics module"""

__all__ = [
    "AbstractCircleShape",
    "AbstractRectangleShape",
    "AbstractShape",
    "AnimatedSprite",
    "BLACK",
    "BLUE",
    "BLUE_DARK",
    "BLUE_LIGHT",
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
    "CrossShape",
    "DiagonalCrossShape",
    "Drawable",
    "DrawableGroup",
    "DrawableMeta",
    "Entry",
    "EntryMeta",
    "Font",
    "Form",
    "GRAY",
    "GRAY_DARK",
    "GRAY_LIGHT",
    "GREEN",
    "GREEN_DARK",
    "GREEN_LIGHT",
    "GradientShape",
    "Grid",
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
    "MultiColorShape",
    "NoTheme",
    "ORANGE",
    "OutlinedShape",
    "PURPLE",
    "PlusCrossShape",
    "PolygonShape",
    "ProgressBar",
    "RED",
    "RED_DARK",
    "RED_LIGHT",
    "RadialGradientShape",
    "Rect",
    "RectangleShape",
    "AbstractRenderer",
    "ScaleBar",
    "ScrollArea",
    "ScrollBar",
    "ScrollBarMeta",
    "ShapeMeta",
    "SingleColorShape",
    "Sprite",
    "SpriteGroup",
    "SquaredGradientShape",
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
    "ThemedShapeMeta",
    "TransformAnimation",
    "Transformable",
    "TransformableMeta",
    "VerticalGradientShape",
    "VerticalMultiColorShape",
    "WHITE",
    "YELLOW",
    "abstract_theme_class",
    "apply_theme_decorator",
    "closed_namespace",
    "create_surface",
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

if pygame.version.vernum < (2, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'")

if (pygame.image.get_sdl_image_version() or (0, 0)) < (2, 0, 0):
    raise ImportError(
        "Your SDL_image version is too old: '{0}.{1}.{2}' < '2.0.0'".format(*(pygame.image.get_sdl_image_version() or (0, 0, 0)))
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
from .animation import TransformAnimation
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
    Drawable,
    DrawableGroup,
    DrawableMeta,
    LayeredDrawableGroup,
    MDrawable,
    MDrawableMeta,
    TDrawable,
    TDrawableMeta,
)
from .entry import Entry, EntryMeta
from .font import Font, SysFont
from .form import Form
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
from .grid import Grid
from .image import Image
from .movable import Movable, MovableMeta
from .progress import ProgressBar
from .rect import ImmutableRect, Rect
from .renderer import AbstractRenderer, SurfaceRenderer
from .scale import ScaleBar
from .scroll import ScrollArea, ScrollBar, ScrollBarMeta
from .shape import (
    AbstractCircleShape,
    AbstractRectangleShape,
    AbstractShape,
    CircleShape,
    CrossShape,
    DiagonalCrossShape,
    OutlinedShape,
    PlusCrossShape,
    PolygonShape,
    RectangleShape,
    ShapeMeta,
    SingleColorShape,
    ThemedShapeMeta,
)
from .sprite import AnimatedSprite, LayeredSpriteGroup, Mask, Sprite, SpriteGroup
from .surface import Surface, create_surface, load_image, save_image
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
    apply_theme_decorator,
    closed_namespace,
    no_theme_decorator,
    set_default_theme_namespace,
)
from .transformable import Transformable, TransformableMeta
