# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Rect module"""

from __future__ import annotations

__all__ = ["ImmutableRect", "Rect"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from dataclasses import dataclass
from typing import TYPE_CHECKING

from pygame.rect import Rect


@dataclass(init=False, repr=False, eq=False, frozen=True)
class ImmutableRect(Rect):
    if not TYPE_CHECKING:

        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, **kwargs)

    @staticmethod
    def convert(pygame_rect: Rect) -> ImmutableRect:
        return ImmutableRect(pygame_rect.topleft, pygame_rect.size)
