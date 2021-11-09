# -*- coding: Utf-8 -*

from typing import Optional, Sequence, Tuple, Union, overload
from operator import truth
from enum import IntEnum

import pygame.key

__all__ = ["Keyboard"]

_KEY_STATES: Sequence[bool] = []
_KEY_REPEAT: Tuple[int, int] = (0, 0)


class Keyboard:
    @staticmethod
    def update() -> None:
        global _KEY_STATES
        _KEY_STATES = pygame.key.get_pressed()

    @overload
    @staticmethod
    def get(key: int) -> str:
        ...

    @overload
    @staticmethod
    def get(key: str) -> int:
        ...

    @staticmethod
    def get(key: Union[str, int]) -> Union[str, int]:
        if isinstance(key, str):
            return pygame.key.key_code(key)
        if isinstance(key, int):
            return pygame.key.name(Keyboard.Key(key).value)
        raise TypeError("Bad argument type")

    @staticmethod
    def is_pressed(key: Union[int, str]) -> bool:
        if isinstance(key, str):
            key = pygame.key.key_code(key)
        return truth(_KEY_STATES[Keyboard.Key(key).value])

    @staticmethod
    def get_repeat() -> Tuple[int, int]:
        return pygame.key.get_repeat()

    @overload
    @staticmethod
    def set_repeat(delay: None) -> Tuple[int, int]:
        ...

    @overload
    @staticmethod
    def set_repeat(delay: int, interval: int = 0) -> Tuple[int, int]:
        ...

    @staticmethod
    def set_repeat(delay: Optional[int], interval: int = 0) -> Tuple[int, int]:
        global _KEY_REPEAT
        former_params: Tuple[int, int]
        if not Keyboard.IME.text_input_enabled():
            former_params = pygame.key.get_repeat()
            if delay is None:
                pygame.key.set_repeat()
            else:
                pygame.key.set_repeat(delay, interval)
        else:
            former_params = _KEY_REPEAT
            if delay is None:
                _KEY_REPEAT = (0, 0)
            else:
                _KEY_REPEAT = (delay, interval)
        return former_params

    class IME:
        __start: bool = False

        @staticmethod
        def text_input_enabled() -> bool:
            return Keyboard.IME.__start

        @staticmethod
        def start_text_input() -> None:
            global _KEY_REPEAT
            if not Keyboard.IME.__start:
                pygame.key.start_text_input()
                _KEY_REPEAT = pygame.key.get_repeat()
                pygame.key.set_repeat(500, 50)
                Keyboard.IME.__start = True

        @staticmethod
        def stop_text_input() -> None:
            global _KEY_REPEAT
            if Keyboard.IME.__start:
                pygame.key.stop_text_input()
                pygame.key.set_repeat(*_KEY_REPEAT)
                _KEY_REPEAT = (0, 0)
                Keyboard.IME.__start = False

    class Key(IntEnum):
        BACKSPACE = pygame.K_BACKSPACE
        TAB = pygame.K_TAB
        CLEAR = pygame.K_CLEAR
        RETURN = pygame.K_RETURN
        PAUSE = pygame.K_PAUSE
        ESCAPE = pygame.K_ESCAPE
        SPACE = pygame.K_SPACE
        EXCLAIM = pygame.K_EXCLAIM
        QUOTEDBL = pygame.K_QUOTEDBL
        HASH = pygame.K_HASH
        DOLLAR = pygame.K_DOLLAR
        AMPERSAND = pygame.K_AMPERSAND
        QUOTE = pygame.K_QUOTE
        LEFTPAREN = pygame.K_LEFTPAREN
        RIGHTPAREN = pygame.K_RIGHTPAREN
        ASTERISK = pygame.K_ASTERISK
        PLUS = pygame.K_PLUS
        COMMA = pygame.K_COMMA
        MINUS = pygame.K_MINUS
        PERIOD = pygame.K_PERIOD
        SLASH = pygame.K_SLASH
        K_0 = pygame.K_0
        K_1 = pygame.K_1
        K_2 = pygame.K_2
        K_3 = pygame.K_3
        K_4 = pygame.K_4
        K_5 = pygame.K_5
        K_6 = pygame.K_6
        K_7 = pygame.K_7
        K_8 = pygame.K_8
        K_9 = pygame.K_9
        COLON = pygame.K_COLON
        SEMICOLON = pygame.K_SEMICOLON
        LESS = pygame.K_LESS
        EQUALS = pygame.K_EQUALS
        GREATER = pygame.K_GREATER
        QUESTION = pygame.K_QUESTION
        AT = pygame.K_AT
        LEFTBRACKET = pygame.K_LEFTBRACKET
        BACKSLASH = pygame.K_BACKSLASH
        RIGHTBRACKET = pygame.K_RIGHTBRACKET
        CARET = pygame.K_CARET
        UNDERSCORE = pygame.K_UNDERSCORE
        BACKQUOTE = pygame.K_BACKQUOTE
        a = pygame.K_a
        b = pygame.K_b
        c = pygame.K_c
        d = pygame.K_d
        e = pygame.K_e
        f = pygame.K_f
        g = pygame.K_g
        h = pygame.K_h
        i = pygame.K_i
        j = pygame.K_j
        k = pygame.K_k
        l = pygame.K_l
        m = pygame.K_m
        n = pygame.K_n
        o = pygame.K_o
        p = pygame.K_p
        q = pygame.K_q
        r = pygame.K_r
        s = pygame.K_s
        t = pygame.K_t
        u = pygame.K_u
        v = pygame.K_v
        w = pygame.K_w
        x = pygame.K_x
        y = pygame.K_y
        z = pygame.K_z
        DELETE = pygame.K_DELETE
        KP0 = pygame.K_KP0
        KP1 = pygame.K_KP1
        KP2 = pygame.K_KP2
        KP3 = pygame.K_KP3
        KP4 = pygame.K_KP4
        KP5 = pygame.K_KP5
        KP6 = pygame.K_KP6
        KP7 = pygame.K_KP7
        KP8 = pygame.K_KP8
        KP9 = pygame.K_KP9
        KP_PERIOD = pygame.K_KP_PERIOD
        KP_DIVIDE = pygame.K_KP_DIVIDE
        KP_MULTIPLY = pygame.K_KP_MULTIPLY
        KP_MINUS = pygame.K_KP_MINUS
        KP_PLUS = pygame.K_KP_PLUS
        KP_ENTER = pygame.K_KP_ENTER
        KP_EQUALS = pygame.K_KP_EQUALS
        UP = pygame.K_UP
        DOWN = pygame.K_DOWN
        RIGHT = pygame.K_RIGHT
        LEFT = pygame.K_LEFT
        INSERT = pygame.K_INSERT
        HOME = pygame.K_HOME
        END = pygame.K_END
        PAGEUP = pygame.K_PAGEUP
        PAGEDOWN = pygame.K_PAGEDOWN
        F1 = pygame.K_F1
        F2 = pygame.K_F2
        F3 = pygame.K_F3
        F4 = pygame.K_F4
        F5 = pygame.K_F5
        F6 = pygame.K_F6
        F7 = pygame.K_F7
        F8 = pygame.K_F8
        F9 = pygame.K_F9
        F10 = pygame.K_F10
        F11 = pygame.K_F11
        F12 = pygame.K_F12
        F13 = pygame.K_F13
        F14 = pygame.K_F14
        F15 = pygame.K_F15
        NUMLOCK = pygame.K_NUMLOCK
        CAPSLOCK = pygame.K_CAPSLOCK
        SCROLLOCK = pygame.K_SCROLLOCK
        RSHIFT = pygame.K_RSHIFT
        LSHIFT = pygame.K_LSHIFT
        RCTRL = pygame.K_RCTRL
        LCTRL = pygame.K_LCTRL
        RALT = pygame.K_RALT
        LALT = pygame.K_LALT
        RMETA = pygame.K_RMETA
        LMETA = pygame.K_LMETA
        LSUPER = pygame.K_LSUPER
        RSUPER = pygame.K_RSUPER
        MODE = pygame.K_MODE
        HELP = pygame.K_HELP
        PRINT = pygame.K_PRINT
        SYSREQ = pygame.K_SYSREQ
        BREAK = pygame.K_BREAK
        MENU = pygame.K_MENU
        POWER = pygame.K_POWER
        EURO = pygame.K_EURO

    class Modifiers(IntEnum):
        NONE = pygame.KMOD_NONE
        LSHIFT = pygame.KMOD_LSHIFT
        RSHIFT = pygame.KMOD_RSHIFT
        SHIFT = pygame.KMOD_SHIFT
        LCTRL = pygame.KMOD_LCTRL
        RCTRL = pygame.KMOD_RCTRL
        CTRL = pygame.KMOD_CTRL
        LALT = pygame.KMOD_LALT
        RALT = pygame.KMOD_RALT
        ALT = pygame.KMOD_ALT
        LMETA = pygame.KMOD_LMETA
        RMETA = pygame.KMOD_RMETA
        META = pygame.KMOD_META
        CAPS = pygame.KMOD_CAPS
        NUM = pygame.KMOD_NUM
        MODE = pygame.KMOD_MODE
