# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Mouse management module"""

from __future__ import annotations

__all__ = ["Mouse"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import IntEnum
from operator import truth
from typing import Tuple

import pygame.constants as _pg_constants
import pygame.mouse as _pg_mouse

from ..system.namespace import MetaClassNamespace

_MOUSE_BUTTON_STATE: Tuple[bool, bool, bool] = (False, False, False)


class Mouse(metaclass=MetaClassNamespace, frozen=True):
    @staticmethod
    def get_pos() -> Tuple[int, int]:
        return _pg_mouse.get_pos()

    @staticmethod
    def set_pos(x: int, y: int) -> None:
        _pg_mouse.set_pos(x, y)

    @staticmethod
    def update() -> None:
        global _MOUSE_BUTTON_STATE
        button_states = _pg_mouse.get_pressed(3)
        _MOUSE_BUTTON_STATE = (truth(button_states[0]), truth(button_states[1]), truth(button_states[2]))

    @staticmethod
    def is_pressed(button: Button) -> bool:
        return _MOUSE_BUTTON_STATE[button]

    @staticmethod
    def show_cursor() -> None:
        Mouse.set_visible(True)

    @staticmethod
    def hide_cursor() -> None:
        Mouse.set_visible(False)

    @staticmethod
    def toogle_cursor() -> None:
        Mouse.set_visible(not Mouse.is_visible())

    @staticmethod
    def set_visible(status: bool) -> None:
        _pg_mouse.set_visible(bool(status))

    @staticmethod
    def is_visible() -> bool:
        return _pg_mouse.get_visible()

    class Button(IntEnum):
        LEFT = _pg_constants.BUTTON_LEFT
        RIGHT = _pg_constants.BUTTON_RIGHT
        MIDDLE = _pg_constants.BUTTON_MIDDLE


del _pg_constants
