# -*- coding: Utf-8 -*

from __future__ import annotations

__all__ = ["Mouse"]

from typing import Tuple
from enum import IntEnum
from operator import truth

import pygame.mouse
from pygame.constants import BUTTON_LEFT, BUTTON_MIDDLE, BUTTON_RIGHT, BUTTON_WHEELDOWN, BUTTON_WHEELUP

_MOUSE_BUTTON_STATE: Tuple[bool, bool, bool] = (False, False, False)


class Mouse:
    @staticmethod
    def get_pos() -> Tuple[int, int]:
        return pygame.mouse.get_pos()

    @staticmethod
    def set_pos(x: int, y: int) -> None:
        pygame.mouse.set_pos(x, y)

    @staticmethod
    def update() -> None:
        global _MOUSE_BUTTON_STATE
        button_states = pygame.mouse.get_pressed(3)
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
        pygame.mouse.set_visible(bool(status))

    @staticmethod
    def is_visible() -> bool:
        return pygame.mouse.get_visible()

    class Button(IntEnum):
        LEFT = BUTTON_LEFT
        RIGHT = BUTTON_RIGHT
        MIDDLE = BUTTON_MIDDLE

    class Wheel(IntEnum):
        UP = BUTTON_WHEELUP
        DOWN = BUTTON_WHEELDOWN
