# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
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
    "COLOR_DICT",
    "COMPILED_SURFACE_EXTENSION",
    "CYAN",
    "CheckBox",
    "CircleShape",
    "Color",
    "CrossShape",
    "DiagonalCrossShape",
    "Drawable",
    "DrawableGroup",
    "Entry",
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
    "LayeredGroup",
    "LayeredSpriteGroup",
    "MAGENTA",
    "MDrawable",
    "MetaButton",
    "MetaCheckBox",
    "MetaDrawable",
    "MetaEntry",
    "MetaMDrawable",
    "MetaMovable",
    "MetaScrollBar",
    "MetaShape",
    "MetaTDrawable",
    "MetaText",
    "MetaThemedObject",
    "MetaThemedShape",
    "MetaTransformable",
    "Movable",
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
    "Renderer",
    "ScaleBar",
    "ScrollArea",
    "ScrollBar",
    "SingleColorShape",
    "Sprite",
    "SpriteGroup",
    "SquaredGradientShape",
    "Surface",
    "SurfaceRenderer",
    "SysFont",
    "TDrawable",
    "TRANSPARENT",
    "Text",
    "TextImage",
    "ThemeNamespace",
    "ThemeType",
    "ThemedObject",
    "TransformAnimation",
    "Transformable",
    "VerticalGradientShape",
    "VerticalMultiColorShape",
    "WHITE",
    "YELLOW",
    "abstract_theme_class",
    "create_surface",
    "load_image",
    "save_image",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import copyreg
import os
import typing

import pygame

if pygame.version.vernum < (2, 1):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'")

############ Surface pickling register ############
copyreg.pickle(
    pygame.surface.Surface,
    lambda s, serializer=pygame.image.tostring, deserializer=pygame.image.fromstring: (  # type: ignore
        deserializer,
        (serializer(s, "ARGB"), s.get_size(), "ARGB"),
    ),
)

############ Cleanup ############
del os, typing, pygame, copyreg


############ Package initialization ############
from .button import Button, ImageButton, MetaButton
from .checkbox import BooleanCheckBox, CheckBox, MetaCheckBox
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
from .drawable import Drawable, DrawableGroup, LayeredGroup, MDrawable, MetaDrawable, MetaMDrawable, MetaTDrawable, TDrawable
from .entry import Entry, MetaEntry
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
from .movable import MetaMovable, Movable
from .progress import ProgressBar
from .rect import ImmutableRect, Rect
from .renderer import Renderer, SurfaceRenderer
from .scale import ScaleBar
from .scroll import MetaScrollBar, ScrollArea, ScrollBar
from .shape import (
    AbstractCircleShape,
    AbstractRectangleShape,
    AbstractShape,
    CircleShape,
    CrossShape,
    DiagonalCrossShape,
    MetaShape,
    MetaThemedShape,
    OutlinedShape,
    PlusCrossShape,
    PolygonShape,
    RectangleShape,
    SingleColorShape,
)
from .sprite import AnimatedSprite, LayeredSpriteGroup, Sprite, SpriteGroup
from .surface import COMPILED_SURFACE_EXTENSION, Surface, create_surface, load_image, save_image
from .text import MetaText, Text, TextImage
from .theme import MetaThemedObject, NoTheme, ThemedObject, ThemeNamespace, ThemeType, abstract_theme_class
from .transformable import MetaTransformable, Transformable

# Put it here to avoid circular import with 'window' module
from .animation import TransformAnimation  # isort:skip
