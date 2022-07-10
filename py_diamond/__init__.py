# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pygame-based game engine

PyDiamond engine is a game engine intended to game developers in Python language.
The framework uses the popular pygame library (https://github.com/pygame/pygame/).

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 3 of the License, or (at your option) any later
version.
This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
You should have received a copy of the GNU General Public License along with
this program. If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import annotations

__all__ = []  # type: list[str]

__author__ = "FrankySnow9"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__credits__ = ["FrankySnow9"]
__license__ = "GNU GPL v3.0"
__maintainer__ = "FrankySnow9"
__email__ = "clairicia.rcj.francis@gmail.com"

from .version import version_info

__version__ = str(version_info)

match version_info.releaselevel:
    case "final" if not version_info.suffix:
        __status__ = "Production"
    case _:
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

############ Package initialization ############
#### Apply various patch that must be run before importing the main modules
from ._patch import PatchContext, collector

collector.start_record()

collector.run_patches(PatchContext.BEFORE_ALL)

if any(name == "pygame" or name.startswith("pygame.") for name in list(sys.modules)):
    import warnings

    warn_msg = "'pygame' module already imported, this can cause unwanted behavior. Consider importing py_diamond first."
    warnings.warn(warn_msg)

    del warnings, warn_msg

else:
    # No need to run patch that must be done specifically before importing pygame if it was already imported

    collector.run_patches(PatchContext.BEFORE_IMPORTING_PYGAME)

try:
    import pygame
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "'pygame' package must be installed in order to use the PyDiamond engine",
        name=exc.name,
        path=exc.path,
    ) from exc

collector.run_patches(PatchContext.AFTER_IMPORTING_PYGAME)

collector.run_patches(PatchContext.BEFORE_IMPORTING_SUBMODULES)

import py_diamond.audio
import py_diamond.environ
import py_diamond.graphics
import py_diamond.math
import py_diamond.network
import py_diamond.resource
import py_diamond.system
import py_diamond.window

collector.run_patches(PatchContext.AFTER_IMPORTING_SUBMODULES)

collector.run_patches(PatchContext.AFTER_ALL)

__patches__ = collector.stop_record()

############ Cleanup ############
del os, sys, py_diamond, pygame, collector, PatchContext
