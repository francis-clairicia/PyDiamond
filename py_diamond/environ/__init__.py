# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment module"""

from __future__ import annotations

__all__ = [
    "get_executable_path",
    "get_main_script_path",
    "is_frozen_executable",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from .executable import get_executable_path, get_main_script_path, is_frozen_executable
