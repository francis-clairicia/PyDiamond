# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Keyboard management module"""

from __future__ import annotations

__all__ = ["Key", "KeyModifiers", "Keyboard"]

from enum import IntEnum, IntFlag, auto, unique
from typing import ClassVar, Sequence, final, overload

import pygame.constants as _pg_constants
import pygame.key as _pg_key

from ..system.namespace import ClassNamespace

_KEY_REPEAT: tuple[int, int] = (0, 0)


@final
class Keyboard(ClassNamespace, frozen=True):
    _KEY_STATES: Sequence[bool] = []

    @staticmethod
    def is_pressed(key: Key) -> bool:
        key = Key(key)
        try:
            return bool(Keyboard._KEY_STATES[key.value])
        except IndexError:
            return False

    @staticmethod
    def get_repeat() -> tuple[int, int]:
        return _pg_key.get_repeat()

    @overload
    @staticmethod
    def set_repeat(delay: None) -> tuple[int, int]:
        ...

    @overload
    @staticmethod
    def set_repeat(delay: int, interval: int = 0) -> tuple[int, int]:
        ...

    @staticmethod
    def set_repeat(delay: int | None, interval: int = 0) -> tuple[int, int]:
        global _KEY_REPEAT
        former_params: tuple[int, int]
        if not Keyboard.IME.text_input_enabled():
            former_params = _pg_key.get_repeat()
            if delay is None:
                _pg_key.set_repeat()
            else:
                _pg_key.set_repeat(delay, interval)
        else:
            former_params = _KEY_REPEAT
            if delay is None:
                _KEY_REPEAT = (0, 0)
            else:
                _KEY_REPEAT = (delay, interval)
        return former_params

    class IME(ClassNamespace):
        __start: ClassVar[bool] = False

        @classmethod
        def text_input_enabled(cls) -> bool:
            return cls.__start

        @classmethod
        def start_text_input(cls) -> None:
            global _KEY_REPEAT
            if not cls.__start:
                _pg_key.start_text_input()
                _KEY_REPEAT = _pg_key.get_repeat()
                _pg_key.set_repeat(500, 50)
                cls.__start = True

        @classmethod
        def stop_text_input(cls) -> None:
            global _KEY_REPEAT
            if cls.__start:
                _pg_key.stop_text_input()
                _pg_key.set_repeat(*_KEY_REPEAT)
                _KEY_REPEAT = (0, 0)
                cls.__start = False


class Key(IntEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        return getattr(_pg_constants, name)  # noqa: F821

    K_BACKSPACE = auto()
    K_TAB = auto()
    K_CLEAR = auto()
    K_RETURN = auto()
    K_PAUSE = auto()
    K_ESCAPE = auto()
    K_SPACE = auto()
    K_EXCLAIM = auto()
    K_QUOTEDBL = auto()
    K_HASH = auto()
    K_DOLLAR = auto()
    K_AMPERSAND = auto()
    K_QUOTE = auto()
    K_LEFTPAREN = auto()
    K_RIGHTPAREN = auto()
    K_ASTERISK = auto()
    K_PLUS = auto()
    K_COMMA = auto()
    K_MINUS = auto()
    K_PERIOD = auto()
    K_SLASH = auto()
    K_0 = auto()
    K_1 = auto()
    K_2 = auto()
    K_3 = auto()
    K_4 = auto()
    K_5 = auto()
    K_6 = auto()
    K_7 = auto()
    K_8 = auto()
    K_9 = auto()
    K_COLON = auto()
    K_SEMICOLON = auto()
    K_LESS = auto()
    K_EQUALS = auto()
    K_GREATER = auto()
    K_QUESTION = auto()
    K_AT = auto()
    K_LEFTBRACKET = auto()
    K_BACKSLASH = auto()
    K_RIGHTBRACKET = auto()
    K_CARET = auto()
    K_UNDERSCORE = auto()
    K_BACKQUOTE = auto()
    K_a = auto()
    K_b = auto()
    K_c = auto()
    K_d = auto()
    K_e = auto()
    K_f = auto()
    K_g = auto()
    K_h = auto()
    K_i = auto()
    K_j = auto()
    K_k = auto()
    K_l = auto()
    K_m = auto()
    K_n = auto()
    K_o = auto()
    K_p = auto()
    K_q = auto()
    K_r = auto()
    K_s = auto()
    K_t = auto()
    K_u = auto()
    K_v = auto()
    K_w = auto()
    K_x = auto()
    K_y = auto()
    K_z = auto()
    K_DELETE = auto()
    K_KP0 = auto()
    K_KP1 = auto()
    K_KP2 = auto()
    K_KP3 = auto()
    K_KP4 = auto()
    K_KP5 = auto()
    K_KP6 = auto()
    K_KP7 = auto()
    K_KP8 = auto()
    K_KP9 = auto()
    K_KP_PERIOD = auto()
    K_KP_DIVIDE = auto()
    K_KP_MULTIPLY = auto()
    K_KP_MINUS = auto()
    K_KP_PLUS = auto()
    K_KP_ENTER = auto()
    K_KP_EQUALS = auto()
    K_UP = auto()
    K_DOWN = auto()
    K_RIGHT = auto()
    K_LEFT = auto()
    K_INSERT = auto()
    K_HOME = auto()
    K_END = auto()
    K_PAGEUP = auto()
    K_PAGEDOWN = auto()
    K_F1 = auto()
    K_F2 = auto()
    K_F3 = auto()
    K_F4 = auto()
    K_F5 = auto()
    K_F6 = auto()
    K_F7 = auto()
    K_F8 = auto()
    K_F9 = auto()
    K_F10 = auto()
    K_F11 = auto()
    K_F12 = auto()
    K_F13 = auto()
    K_F14 = auto()
    K_F15 = auto()
    K_NUMLOCK = auto()
    K_CAPSLOCK = auto()
    K_SCROLLOCK = auto()
    K_RSHIFT = auto()
    K_LSHIFT = auto()
    K_RCTRL = auto()
    K_LCTRL = auto()
    K_RALT = auto()
    K_LALT = auto()
    K_RMETA = auto()
    K_LMETA = auto()
    K_LSUPER = auto()
    K_RSUPER = auto()
    K_MODE = auto()
    K_HELP = auto()
    K_PRINT = auto()
    K_SYSREQ = auto()
    K_BREAK = auto()
    K_MENU = auto()
    K_POWER = auto()
    K_EURO = auto()

    @classmethod
    def from_pygame_name(cls, name: str) -> Key:
        return cls(_pg_key.key_code(name))

    @property
    def real_name(self) -> str:
        return _pg_key.name(self.value)


@unique
class KeyModifiers(IntFlag):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        return getattr(_pg_constants, name)  # noqa: F821

    KMOD_NONE = auto()
    KMOD_LSHIFT = auto()
    KMOD_RSHIFT = auto()
    KMOD_SHIFT = auto()
    KMOD_LCTRL = auto()
    KMOD_RCTRL = auto()
    KMOD_CTRL = auto()
    KMOD_LALT = auto()
    KMOD_RALT = auto()
    KMOD_ALT = auto()
    KMOD_LMETA = auto()
    KMOD_RMETA = auto()
    KMOD_META = auto()
    KMOD_CAPS = auto()
    KMOD_NUM = auto()
    KMOD_MODE = auto()


del _pg_constants
