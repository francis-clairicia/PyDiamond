# -*- coding: Utf-8 -*

import os
import typing
import copyreg

import pygame

if pygame.version.vernum < (2, 1):
    raise pygame.error(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.0'")

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
