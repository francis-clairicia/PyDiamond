# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Keyboard management module"""

from __future__ import annotations

__all__ = ["Keyboard"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import IntEnum, IntFlag, unique
from operator import truth
from typing import ClassVar, Sequence, overload

import pygame.constants as _pg_constants
import pygame.key as _pg_key

from ..system.namespace import ClassNamespaceMeta

_KEY_STATES: Sequence[bool] = []
_KEY_REPEAT: tuple[int, int] = (0, 0)


class Keyboard(metaclass=ClassNamespaceMeta, frozen=True):
    @staticmethod
    def update() -> None:
        global _KEY_STATES
        _KEY_STATES = _pg_key.get_pressed()

    @overload
    @staticmethod
    def get(key: Key) -> str:
        ...

    @overload
    @staticmethod
    def get(key: str) -> Key:
        ...

    @staticmethod
    def get(key: str | Key) -> str | Key:
        if isinstance(key, str):
            return Keyboard.Key(_pg_key.key_code(key))
        if isinstance(key, int):
            return _pg_key.name(Keyboard.Key(key).value)
        raise TypeError("Bad argument type")

    @staticmethod
    def is_pressed(key: Key | str) -> bool:
        if isinstance(key, str):
            key = Keyboard.Key(_pg_key.key_code(key))
        else:
            key = Keyboard.Key(key)
        return truth(_KEY_STATES[key.value])

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

    class IME(metaclass=ClassNamespaceMeta):
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
        BACKSPACE = _pg_constants.K_BACKSPACE
        TAB = _pg_constants.K_TAB
        CLEAR = _pg_constants.K_CLEAR
        RETURN = _pg_constants.K_RETURN
        PAUSE = _pg_constants.K_PAUSE
        ESCAPE = _pg_constants.K_ESCAPE
        SPACE = _pg_constants.K_SPACE
        EXCLAIM = _pg_constants.K_EXCLAIM
        QUOTEDBL = _pg_constants.K_QUOTEDBL
        HASH = _pg_constants.K_HASH
        DOLLAR = _pg_constants.K_DOLLAR
        AMPERSAND = _pg_constants.K_AMPERSAND
        QUOTE = _pg_constants.K_QUOTE
        LEFTPAREN = _pg_constants.K_LEFTPAREN
        RIGHTPAREN = _pg_constants.K_RIGHTPAREN
        ASTERISK = _pg_constants.K_ASTERISK
        PLUS = _pg_constants.K_PLUS
        COMMA = _pg_constants.K_COMMA
        MINUS = _pg_constants.K_MINUS
        PERIOD = _pg_constants.K_PERIOD
        SLASH = _pg_constants.K_SLASH
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
        COLON = _pg_constants.K_COLON
        SEMICOLON = _pg_constants.K_SEMICOLON
        LESS = _pg_constants.K_LESS
        EQUALS = _pg_constants.K_EQUALS
        GREATER = _pg_constants.K_GREATER
        QUESTION = _pg_constants.K_QUESTION
        AT = _pg_constants.K_AT
        LEFTBRACKET = _pg_constants.K_LEFTBRACKET
        BACKSLASH = _pg_constants.K_BACKSLASH
        RIGHTBRACKET = _pg_constants.K_RIGHTBRACKET
        CARET = _pg_constants.K_CARET
        UNDERSCORE = _pg_constants.K_UNDERSCORE
        BACKQUOTE = _pg_constants.K_BACKQUOTE
        A = _pg_constants.K_a
        B = _pg_constants.K_b
        C = _pg_constants.K_c
        D = _pg_constants.K_d
        E = _pg_constants.K_e
        F = _pg_constants.K_f
        G = _pg_constants.K_g
        H = _pg_constants.K_h
        I = _pg_constants.K_i
        J = _pg_constants.K_j
        K = _pg_constants.K_k
        L = _pg_constants.K_l
        M = _pg_constants.K_m
        N = _pg_constants.K_n
        O = _pg_constants.K_o
        P = _pg_constants.K_p
        Q = _pg_constants.K_q
        R = _pg_constants.K_r
        S = _pg_constants.K_s
        T = _pg_constants.K_t
        U = _pg_constants.K_u
        V = _pg_constants.K_v
        W = _pg_constants.K_w
        X = _pg_constants.K_x
        Y = _pg_constants.K_y
        Z = _pg_constants.K_z
        DELETE = _pg_constants.K_DELETE
        KP0 = _pg_constants.K_KP0
        KP1 = _pg_constants.K_KP1
        KP2 = _pg_constants.K_KP2
        KP3 = _pg_constants.K_KP3
        KP4 = _pg_constants.K_KP4
        KP5 = _pg_constants.K_KP5
        KP6 = _pg_constants.K_KP6
        KP7 = _pg_constants.K_KP7
        KP8 = _pg_constants.K_KP8
        KP9 = _pg_constants.K_KP9
        KP_PERIOD = _pg_constants.K_KP_PERIOD
        KP_DIVIDE = _pg_constants.K_KP_DIVIDE
        KP_MULTIPLY = _pg_constants.K_KP_MULTIPLY
        KP_MINUS = _pg_constants.K_KP_MINUS
        KP_PLUS = _pg_constants.K_KP_PLUS
        KP_ENTER = _pg_constants.K_KP_ENTER
        KP_EQUALS = _pg_constants.K_KP_EQUALS
        UP = _pg_constants.K_UP
        DOWN = _pg_constants.K_DOWN
        RIGHT = _pg_constants.K_RIGHT
        LEFT = _pg_constants.K_LEFT
        INSERT = _pg_constants.K_INSERT
        HOME = _pg_constants.K_HOME
        END = _pg_constants.K_END
        PAGEUP = _pg_constants.K_PAGEUP
        PAGEDOWN = _pg_constants.K_PAGEDOWN
        F1 = _pg_constants.K_F1
        F2 = _pg_constants.K_F2
        F3 = _pg_constants.K_F3
        F4 = _pg_constants.K_F4
        F5 = _pg_constants.K_F5
        F6 = _pg_constants.K_F6
        F7 = _pg_constants.K_F7
        F8 = _pg_constants.K_F8
        F9 = _pg_constants.K_F9
        F10 = _pg_constants.K_F10
        F11 = _pg_constants.K_F11
        F12 = _pg_constants.K_F12
        F13 = _pg_constants.K_F13
        F14 = _pg_constants.K_F14
        F15 = _pg_constants.K_F15
        NUMLOCK = _pg_constants.K_NUMLOCK
        CAPSLOCK = _pg_constants.K_CAPSLOCK
        SCROLLOCK = _pg_constants.K_SCROLLOCK
        RSHIFT = _pg_constants.K_RSHIFT
        LSHIFT = _pg_constants.K_LSHIFT
        RCTRL = _pg_constants.K_RCTRL
        LCTRL = _pg_constants.K_LCTRL
        RALT = _pg_constants.K_RALT
        LALT = _pg_constants.K_LALT
        RMETA = _pg_constants.K_RMETA
        LMETA = _pg_constants.K_LMETA
        LSUPER = _pg_constants.K_LSUPER
        RSUPER = _pg_constants.K_RSUPER
        MODE = _pg_constants.K_MODE
        HELP = _pg_constants.K_HELP
        PRINT = _pg_constants.K_PRINT
        SYSREQ = _pg_constants.K_SYSREQ
        BREAK = _pg_constants.K_BREAK
        MENU = _pg_constants.K_MENU
        POWER = _pg_constants.K_POWER
        EURO = _pg_constants.K_EURO

    @unique
    class Modifiers(IntFlag):
        NONE = _pg_constants.KMOD_NONE
        LSHIFT = _pg_constants.KMOD_LSHIFT
        RSHIFT = _pg_constants.KMOD_RSHIFT
        SHIFT = _pg_constants.KMOD_SHIFT
        LCTRL = _pg_constants.KMOD_LCTRL
        RCTRL = _pg_constants.KMOD_RCTRL
        CTRL = _pg_constants.KMOD_CTRL
        LALT = _pg_constants.KMOD_LALT
        RALT = _pg_constants.KMOD_RALT
        ALT = _pg_constants.KMOD_ALT
        LMETA = _pg_constants.KMOD_LMETA
        RMETA = _pg_constants.KMOD_RMETA
        META = _pg_constants.KMOD_META
        CAPS = _pg_constants.KMOD_CAPS
        NUM = _pg_constants.KMOD_NUM
        MODE = _pg_constants.KMOD_MODE


del _pg_constants
