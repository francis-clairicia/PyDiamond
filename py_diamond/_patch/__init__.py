# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch system module

This module is intended for internal use, you would not have to use it.
"""

from __future__ import annotations

__all__ = ["PatchContext", "collector"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from ._base import PatchContext
from ._collector import PatchCollector as collector
