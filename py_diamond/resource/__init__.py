# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's resource module"""

__all__ = [
    "FontLoader",
    "ImageLoader",
    "MusicLoader",
    "ResourceLoader",
    "ResourceManager",
    "ResourceManagerMeta",
    "SoundLoader",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .loader import FontLoader, ImageLoader, MusicLoader, ResourceLoader, SoundLoader
from .manager import ResourceManager, ResourceManagerMeta
