# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Keyboard management module"""

from __future__ import annotations

__all__ = ["Key", "KeyModifiers", "Keyboard"]


from enum import IntEnum, IntFlag, unique
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
    K_BACKSPACE = _pg_constants.K_BACKSPACE
    K_TAB = _pg_constants.K_TAB
    K_CLEAR = _pg_constants.K_CLEAR
    K_RETURN = _pg_constants.K_RETURN
    K_PAUSE = _pg_constants.K_PAUSE
    K_ESCAPE = _pg_constants.K_ESCAPE
    K_SPACE = _pg_constants.K_SPACE
    K_EXCLAIM = _pg_constants.K_EXCLAIM
    K_QUOTEDBL = _pg_constants.K_QUOTEDBL
    K_HASH = _pg_constants.K_HASH
    K_DOLLAR = _pg_constants.K_DOLLAR
    K_AMPERSAND = _pg_constants.K_AMPERSAND
    K_QUOTE = _pg_constants.K_QUOTE
    K_LEFTPAREN = _pg_constants.K_LEFTPAREN
    K_RIGHTPAREN = _pg_constants.K_RIGHTPAREN
    K_ASTERISK = _pg_constants.K_ASTERISK
    K_PLUS = _pg_constants.K_PLUS
    K_COMMA = _pg_constants.K_COMMA
    K_MINUS = _pg_constants.K_MINUS
    K_PERIOD = _pg_constants.K_PERIOD
    K_SLASH = _pg_constants.K_SLASH
    K_0 = _pg_constants.K_0
    K_1 = _pg_constants.K_1
    K_2 = _pg_constants.K_2
    K_3 = _pg_constants.K_3
    K_4 = _pg_constants.K_4
    K_5 = _pg_constants.K_5
    K_6 = _pg_constants.K_6
    K_7 = _pg_constants.K_7
    K_8 = _pg_constants.K_8
    K_9 = _pg_constants.K_9
    K_COLON = _pg_constants.K_COLON
    K_SEMICOLON = _pg_constants.K_SEMICOLON
    K_LESS = _pg_constants.K_LESS
    K_EQUALS = _pg_constants.K_EQUALS
    K_GREATER = _pg_constants.K_GREATER
    K_QUESTION = _pg_constants.K_QUESTION
    K_AT = _pg_constants.K_AT
    K_LEFTBRACKET = _pg_constants.K_LEFTBRACKET
    K_BACKSLASH = _pg_constants.K_BACKSLASH
    K_RIGHTBRACKET = _pg_constants.K_RIGHTBRACKET
    K_CARET = _pg_constants.K_CARET
    K_UNDERSCORE = _pg_constants.K_UNDERSCORE
    K_BACKQUOTE = _pg_constants.K_BACKQUOTE
    K_a = _pg_constants.K_a
    K_b = _pg_constants.K_b
    K_c = _pg_constants.K_c
    K_d = _pg_constants.K_d
    K_e = _pg_constants.K_e
    K_f = _pg_constants.K_f
    K_g = _pg_constants.K_g
    K_h = _pg_constants.K_h
    K_i = _pg_constants.K_i
    K_j = _pg_constants.K_j
    K_k = _pg_constants.K_k
    K_l = _pg_constants.K_l
    K_m = _pg_constants.K_m
    K_n = _pg_constants.K_n
    K_o = _pg_constants.K_o
    K_p = _pg_constants.K_p
    K_q = _pg_constants.K_q
    K_r = _pg_constants.K_r
    K_s = _pg_constants.K_s
    K_t = _pg_constants.K_t
    K_u = _pg_constants.K_u
    K_v = _pg_constants.K_v
    K_w = _pg_constants.K_w
    K_x = _pg_constants.K_x
    K_y = _pg_constants.K_y
    K_z = _pg_constants.K_z
    K_DELETE = _pg_constants.K_DELETE
    K_KP0 = _pg_constants.K_KP0
    K_KP1 = _pg_constants.K_KP1
    K_KP2 = _pg_constants.K_KP2
    K_KP3 = _pg_constants.K_KP3
    K_KP4 = _pg_constants.K_KP4
    K_KP5 = _pg_constants.K_KP5
    K_KP6 = _pg_constants.K_KP6
    K_KP7 = _pg_constants.K_KP7
    K_KP8 = _pg_constants.K_KP8
    K_KP9 = _pg_constants.K_KP9
    K_KP_PERIOD = _pg_constants.K_KP_PERIOD
    K_KP_DIVIDE = _pg_constants.K_KP_DIVIDE
    K_KP_MULTIPLY = _pg_constants.K_KP_MULTIPLY
    K_KP_MINUS = _pg_constants.K_KP_MINUS
    K_KP_PLUS = _pg_constants.K_KP_PLUS
    K_KP_ENTER = _pg_constants.K_KP_ENTER
    K_KP_EQUALS = _pg_constants.K_KP_EQUALS
    K_UP = _pg_constants.K_UP
    K_DOWN = _pg_constants.K_DOWN
    K_RIGHT = _pg_constants.K_RIGHT
    K_LEFT = _pg_constants.K_LEFT
    K_INSERT = _pg_constants.K_INSERT
    K_HOME = _pg_constants.K_HOME
    K_END = _pg_constants.K_END
    K_PAGEUP = _pg_constants.K_PAGEUP
    K_PAGEDOWN = _pg_constants.K_PAGEDOWN
    K_F1 = _pg_constants.K_F1
    K_F2 = _pg_constants.K_F2
    K_F3 = _pg_constants.K_F3
    K_F4 = _pg_constants.K_F4
    K_F5 = _pg_constants.K_F5
    K_F6 = _pg_constants.K_F6
    K_F7 = _pg_constants.K_F7
    K_F8 = _pg_constants.K_F8
    K_F9 = _pg_constants.K_F9
    K_F10 = _pg_constants.K_F10
    K_F11 = _pg_constants.K_F11
    K_F12 = _pg_constants.K_F12
    K_F13 = _pg_constants.K_F13
    K_F14 = _pg_constants.K_F14
    K_F15 = _pg_constants.K_F15
    K_NUMLOCK = _pg_constants.K_NUMLOCK
    K_CAPSLOCK = _pg_constants.K_CAPSLOCK
    K_SCROLLOCK = _pg_constants.K_SCROLLOCK
    K_RSHIFT = _pg_constants.K_RSHIFT
    K_LSHIFT = _pg_constants.K_LSHIFT
    K_RCTRL = _pg_constants.K_RCTRL
    K_LCTRL = _pg_constants.K_LCTRL
    K_RALT = _pg_constants.K_RALT
    K_LALT = _pg_constants.K_LALT
    K_RMETA = _pg_constants.K_RMETA
    K_LMETA = _pg_constants.K_LMETA
    K_LSUPER = _pg_constants.K_LSUPER
    K_RSUPER = _pg_constants.K_RSUPER
    K_MODE = _pg_constants.K_MODE
    K_HELP = _pg_constants.K_HELP
    K_PRINT = _pg_constants.K_PRINT
    K_SYSREQ = _pg_constants.K_SYSREQ
    K_BREAK = _pg_constants.K_BREAK
    K_MENU = _pg_constants.K_MENU
    K_POWER = _pg_constants.K_POWER
    K_EURO = _pg_constants.K_EURO

    @classmethod
    def from_name(cls, name: str) -> Key:
        return cls(_pg_key.key_code(name))

    @property
    def real_name(self) -> str:
        return _pg_key.name(self.value)


@unique
class KeyModifiers(IntFlag):
    KMOD_NONE = _pg_constants.KMOD_NONE
    KMOD_LSHIFT = _pg_constants.KMOD_LSHIFT
    KMOD_RSHIFT = _pg_constants.KMOD_RSHIFT
    KMOD_SHIFT = _pg_constants.KMOD_SHIFT
    KMOD_LCTRL = _pg_constants.KMOD_LCTRL
    KMOD_RCTRL = _pg_constants.KMOD_RCTRL
    KMOD_CTRL = _pg_constants.KMOD_CTRL
    KMOD_LALT = _pg_constants.KMOD_LALT
    KMOD_RALT = _pg_constants.KMOD_RALT
    KMOD_ALT = _pg_constants.KMOD_ALT
    KMOD_LMETA = _pg_constants.KMOD_LMETA
    KMOD_RMETA = _pg_constants.KMOD_RMETA
    KMOD_META = _pg_constants.KMOD_META
    KMOD_CAPS = _pg_constants.KMOD_CAPS
    KMOD_NUM = _pg_constants.KMOD_NUM
    KMOD_MODE = _pg_constants.KMOD_MODE


del _pg_constants
