# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""pygame-based game engine

PyDiamond engine is a game engine for Python game developers.
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
__contact__ = "clairicia.rcj.francis@gmail.com"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__credits__ = ["FrankySnow9"]
__deprecated__ = False
__email__ = "clairicia.rcj.francis@gmail.com"
__license__ = "GNU GPL v3.0"
__maintainer__ = "FrankySnow9"
__status__ = "Development"
__version__ = "1.0.0.dev1"

import os
import sys

############ Environment initialization ############
if sys.version_info < (3, 10):
    raise ImportError(
        "This framework must be run with python >= 3.10 (actual={}.{}.{})".format(*sys.version_info[0:3]),
        name=__name__,
        path=__file__,
    )

if os.environ.get("PYDIAMOND_IMPORT_WARNINGS", "1") not in ("0", "1"):
    raise ValueError(f"Invalid value for 'PYDIAMOND_IMPORT_WARNINGS', got {os.environ['PYDIAMOND_IMPORT_WARNINGS']!r}")

############ Package initialization ############
#### Apply various patch that must be run before importing the main modules
from ._patch import PatchContext, collector

collector.start_record()

collector.run_patches(PatchContext.BEFORE_ALL)

if any(name == "pygame" or name.startswith("pygame.") for name in list(sys.modules)):
    if os.environ.get("PYDIAMOND_IMPORT_WARNINGS", "1") == "1":
        import warnings as _warnings

        from .warnings import PyDiamondImportWarning

        warn_msg = "'pygame' module already imported, this can cause unwanted behavior. Consider importing pydiamond first."
        _warnings.warn(warn_msg, category=PyDiamondImportWarning)

        del _warnings, warn_msg, PyDiamondImportWarning

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

from .version import version_info as version_info

collector.run_patches(PatchContext.PATCH_SUBMODULES)

collector.run_patches(PatchContext.AFTER_ALL)

__patches__ = collector.stop_record()

############ Cleanup ############
del os, sys, pygame, collector, PatchContext
