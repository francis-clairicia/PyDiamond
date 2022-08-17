# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's resource module"""

from __future__ import annotations

__all__ = [
    "AbstractResourceLoader",
    "FontLoader",
    "ImageLoader",
    "MusicLoader",
    "ResourceManager",
    "ResourceManagerMeta",
    "SoundLoader",
]


############ Package initialization ############
from .loader import *
from .manager import *
