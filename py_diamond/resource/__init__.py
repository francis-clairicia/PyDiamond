# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's resource module"""

__all__ = [
    "AbstractResourceLoader",
    "FontLoader",
    "ImageLoader",
    "MusicLoader",
    "ResourceManager",
    "ResourceManagerMeta",
    "SoundLoader",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .loader import AbstractResourceLoader, FontLoader, ImageLoader, MusicLoader, SoundLoader
from .manager import ResourceManager, ResourceManagerMeta
