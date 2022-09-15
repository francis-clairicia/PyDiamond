# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Mouse management module"""

from __future__ import annotations

__all__ = ["Mouse", "MouseButton"]


from enum import IntEnum
from typing import final

import pygame.constants as _pg_constants
import pygame.mouse as _pg_mouse

from ..system.namespace import ClassNamespace


@final
class Mouse(ClassNamespace, frozen=True):
    _MOUSE_BUTTON_STATE: tuple[bool, bool, bool] | tuple[()] = ()

    @staticmethod
    def get_pos() -> tuple[int, int]:
        return _pg_mouse.get_pos()

    @staticmethod
    def set_pos(x: int, y: int) -> None:
        _pg_mouse.set_pos(x, y)

    @staticmethod
    def is_pressed(button: MouseButton) -> bool:
        button = MouseButton(button)
        try:
            return bool(Mouse._MOUSE_BUTTON_STATE[button.value - 1])
        except IndexError:
            return False

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


class MouseButton(IntEnum):
    LEFT = _pg_constants.BUTTON_LEFT
    RIGHT = _pg_constants.BUTTON_RIGHT
    MIDDLE = _pg_constants.BUTTON_MIDDLE


del _pg_constants
