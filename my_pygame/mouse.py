# -*- coding: Utf-8 -*

from typing import Tuple, cast
from enum import IntEnum
from operator import truth

import pygame.mouse

_MouseButtonState = Tuple[bool, bool, bool]

_MOUSE_BUTTON_STATE: _MouseButtonState = (False, False, False)


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
        _MOUSE_BUTTON_STATE = cast(_MouseButtonState, pygame.mouse.get_pressed(3))

    @staticmethod
    def is_pressed(button: int) -> bool:
        return truth(_MOUSE_BUTTON_STATE[button])

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
        LEFT = 1
        RIGHT = 2
        MIDDLE = 3

    LEFT = Button.LEFT
    RIGHT = Button.RIGHT
    MIDDLE = Button.MIDDLE
