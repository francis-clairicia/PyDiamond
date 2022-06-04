# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond engine is a game engine intended to game developers in Python language.
The framework uses the popular pygame library (https://github.com/pygame/pygame/).
"""

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__credits__ = ["Francis Clairicia-Rose-Claire-Josephine"]
__license__ = "GNU GPL v3.0"
__version__ = "1.0.0"
__maintainer__ = "Francis Clairicia-Rose-Claire-Josephine"
__email__ = "clairicia.rcj.francis@gmail.com"
__status__ = "Development"

import os
import sys

############ Environment initialization ############
if sys.version_info < (3, 10):
    raise ImportError(
        "This framework must be run with python >= 3.10 (actual={}.{}.{})".format(*sys.version_info[0:3]),
        name=__name__,
        path=__file__,
    )


os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # Must be set before importing pygame
os.environ.setdefault("SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")  # Must be set before importing pygame

os.environ["PYGAME_FREETYPE"] = "1"  # Must be set before importing pygame (Force modification)

############ Package initialization ############
#### Apply various patch that must be run before importing the main modules
from py_diamond._patch import PatchContext, collector

collector.run_patches(PatchContext.BEFORE_ALL)
####

import py_diamond.environ

py_diamond.environ.check_booleans(
    only=[
        "PYGAME_HIDE_SUPPORT_PROMPT",
        "PYGAME_FREETYPE",
        "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
    ]
)

if any(name == "pygame" or name.startswith("pygame.") for name in list(sys.modules)):
    import warnings

    warn_msg = "'pygame' module already imported, this can cause unwanted behaviour. Consider importing py_diamond first."
    warnings.warn(warn_msg, ImportWarning)

    del warnings, warn_msg

collector.run_patches(PatchContext.BEFORE_IMPORTING_PYGAME)

try:
    import pygame
except ImportError as exc:
    raise ImportError(
        "'pygame' package must be installed in order to use the PyDiamond engine",
        name=exc.name,
        path=exc.path,
    ) from exc

collector.run_patches(PatchContext.AFTER_IMPORTING_PYGAME)

collector.run_patches(PatchContext.BEFORE_IMPORTING_SUBMODULES)

import py_diamond.audio
import py_diamond.graphics
import py_diamond.math
import py_diamond.network
import py_diamond.resource
import py_diamond.system
import py_diamond.window

collector.run_patches(PatchContext.AFTER_IMPORTING_SUBMODULES)

py_diamond.environ.check_booleans(
    exclude=[
        "PYGAME_HIDE_SUPPORT_PROMPT",
        "PYGAME_FREETYPE",
        "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
    ]
)

collector.run_patches(PatchContext.AFTER_ALL)

############ Cleanup ############
del os, sys, py_diamond, pygame, collector, PatchContext
