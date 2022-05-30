# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Mouse management module"""

from __future__ import annotations

__all__ = ["Mouse"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import IntEnum

import pygame.constants as _pg_constants
import pygame.mouse as _pg_mouse

from ..system.namespace import ClassNamespace


class Mouse(ClassNamespace, frozen=True):
    __MOUSE_BUTTON_STATE: tuple[bool, bool, bool] = (False, False, False)

    @staticmethod
    def get_pos() -> tuple[int, int]:
        return _pg_mouse.get_pos()

    @staticmethod
    def set_pos(x: int, y: int) -> None:
        _pg_mouse.set_pos(x, y)

    @staticmethod
    def _update() -> None:
        button_states = _pg_mouse.get_pressed(3)
        button_states = (bool(button_states[0]), bool(button_states[1]), bool(button_states[2]))
        type.__setattr__(Mouse, "_Mouse__MOUSE_BUTTON_STATE", button_states)

    @staticmethod
    def is_pressed(button: Button) -> bool:
        button = Mouse.Button(button)
        return Mouse.__MOUSE_BUTTON_STATE[button.value]

    @staticmethod
    def show_cursor() -> None:
        Mouse.set_visible(True)

    @staticmethod
    def hide_cursor() -> None:
        Mouse.set_visible(False)

    @staticmethod
    def toggle_cursor() -> None:
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
