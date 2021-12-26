# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's graphics module"""

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
copyreg.pickle(
    pygame.Surface,
    lambda s, serializer=pygame.image.tostring, deserializer=pygame.image.fromstring: (  # type: ignore
        deserializer,
        (serializer(s, "ARGB"), s.get_size(), "ARGB"),
    ),
)

############ Cleanup ############
del os, typing, pygame, copyreg
