# -*- coding: Utf-8 -*

from typing import Tuple, Union, final, overload
from operator import truth
from enum import IntEnum

import pygame.key

_KEY_STATES: Tuple[bool, ...] = ()


class Keyboard:
    @staticmethod
    def update() -> None:
        global _KEY_STATES
        _KEY_STATES = tuple(pygame.key.get_pressed())

    @overload
    @staticmethod
    def get(key: int) -> str:
        ...

    @overload
    @staticmethod
    def get(key: str) -> int:
        ...

    @final
    @staticmethod
    def get(key: Union[str, int]) -> Union[str, int]:
        if isinstance(key, str):
            return pygame.key.key_code(key)
        if isinstance(key, int):
            return pygame.key.name(key)
        raise TypeError("Bad argument type")

    @staticmethod
    def is_pressed(key: Union[int, str]) -> bool:
        if isinstance(key, str):
            key = pygame.key.key_code(key)
        return truth(_KEY_STATES[key])

    class Key(IntEnum):
        K_BACKSPACE = pygame.K_BACKSPACE
        K_TAB = pygame.K_TAB
        K_CLEAR = pygame.K_CLEAR
        K_RETURN = pygame.K_RETURN
        K_PAUSE = pygame.K_PAUSE
        K_ESCAPE = pygame.K_ESCAPE
        K_SPACE = pygame.K_SPACE
        K_EXCLAIM = pygame.K_EXCLAIM
        K_QUOTEDBL = pygame.K_QUOTEDBL
        K_HASH = pygame.K_HASH
        K_DOLLAR = pygame.K_DOLLAR
        K_AMPERSAND = pygame.K_AMPERSAND
        K_QUOTE = pygame.K_QUOTE
        K_LEFTPAREN = pygame.K_LEFTPAREN
        K_RIGHTPAREN = pygame.K_RIGHTPAREN
        K_ASTERISK = pygame.K_ASTERISK
        K_PLUS = pygame.K_PLUS
        K_COMMA = pygame.K_COMMA
        K_MINUS = pygame.K_MINUS
        K_PERIOD = pygame.K_PERIOD
        K_SLASH = pygame.K_SLASH
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
        K_COLON = pygame.K_COLON
        K_SEMICOLON = pygame.K_SEMICOLON
        K_LESS = pygame.K_LESS
        K_EQUALS = pygame.K_EQUALS
        K_GREATER = pygame.K_GREATER
        K_QUESTION = pygame.K_QUESTION
        K_AT = pygame.K_AT
        K_LEFTBRACKET = pygame.K_LEFTBRACKET
        K_BACKSLASH = pygame.K_BACKSLASH
        K_RIGHTBRACKET = pygame.K_RIGHTBRACKET
        K_CARET = pygame.K_CARET
        K_UNDERSCORE = pygame.K_UNDERSCORE
        K_BACKQUOTE = pygame.K_BACKQUOTE
        K_a = pygame.K_a
        K_b = pygame.K_b
        K_c = pygame.K_c
        K_d = pygame.K_d
        K_e = pygame.K_e
        K_f = pygame.K_f
        K_g = pygame.K_g
        K_h = pygame.K_h
        K_i = pygame.K_i
        K_j = pygame.K_j
        K_k = pygame.K_k
        K_l = pygame.K_l
        K_m = pygame.K_m
        K_n = pygame.K_n
        K_o = pygame.K_o
        K_p = pygame.K_p
        K_q = pygame.K_q
        K_r = pygame.K_r
        K_s = pygame.K_s
        K_t = pygame.K_t
        K_u = pygame.K_u
        K_v = pygame.K_v
        K_w = pygame.K_w
        K_x = pygame.K_x
        K_y = pygame.K_y
        K_z = pygame.K_z
        K_DELETE = pygame.K_DELETE
        K_KP0 = pygame.K_KP0
        K_KP1 = pygame.K_KP1
        K_KP2 = pygame.K_KP2
        K_KP3 = pygame.K_KP3
        K_KP4 = pygame.K_KP4
        K_KP5 = pygame.K_KP5
        K_KP6 = pygame.K_KP6
        K_KP7 = pygame.K_KP7
        K_KP8 = pygame.K_KP8
        K_KP9 = pygame.K_KP9
        K_KP_PERIOD = pygame.K_KP_PERIOD
        K_KP_DIVIDE = pygame.K_KP_DIVIDE
        K_KP_MULTIPLY = pygame.K_KP_MULTIPLY
        K_KP_MINUS = pygame.K_KP_MINUS
        K_KP_PLUS = pygame.K_KP_PLUS
        K_KP_ENTER = pygame.K_KP_ENTER
        K_KP_EQUALS = pygame.K_KP_EQUALS
        K_UP = pygame.K_UP
        K_DOWN = pygame.K_DOWN
        K_RIGHT = pygame.K_RIGHT
        K_LEFT = pygame.K_LEFT
        K_INSERT = pygame.K_INSERT
        K_HOME = pygame.K_HOME
        K_END = pygame.K_END
        K_PAGEUP = pygame.K_PAGEUP
        K_PAGEDOWN = pygame.K_PAGEDOWN
        K_F1 = pygame.K_F1
        K_F2 = pygame.K_F2
        K_F3 = pygame.K_F3
        K_F4 = pygame.K_F4
        K_F5 = pygame.K_F5
        K_F6 = pygame.K_F6
        K_F7 = pygame.K_F7
        K_F8 = pygame.K_F8
        K_F9 = pygame.K_F9
        K_F10 = pygame.K_F10
        K_F11 = pygame.K_F11
        K_F12 = pygame.K_F12
        K_F13 = pygame.K_F13
        K_F14 = pygame.K_F14
        K_F15 = pygame.K_F15
        K_NUMLOCK = pygame.K_NUMLOCK
        K_CAPSLOCK = pygame.K_CAPSLOCK
        K_SCROLLOCK = pygame.K_SCROLLOCK
        K_RSHIFT = pygame.K_RSHIFT
        K_LSHIFT = pygame.K_LSHIFT
        K_RCTRL = pygame.K_RCTRL
        K_LCTRL = pygame.K_LCTRL
        K_RALT = pygame.K_RALT
        K_LALT = pygame.K_LALT
        K_RMETA = pygame.K_RMETA
        K_LMETA = pygame.K_LMETA
        K_LSUPER = pygame.K_LSUPER
        K_RSUPER = pygame.K_RSUPER
        K_MODE = pygame.K_MODE
        K_HELP = pygame.K_HELP
        K_PRINT = pygame.K_PRINT
        K_SYSREQ = pygame.K_SYSREQ
        K_BREAK = pygame.K_BREAK
        K_MENU = pygame.K_MENU
        K_POWER = pygame.K_POWER
        K_EURO = pygame.K_EURO

    K_BACKSPACE = Key.K_BACKSPACE
    K_TAB = Key.K_TAB
    K_CLEAR = Key.K_CLEAR
    K_RETURN = Key.K_RETURN
    K_PAUSE = Key.K_PAUSE
    K_ESCAPE = Key.K_ESCAPE
    K_SPACE = Key.K_SPACE
    K_EXCLAIM = Key.K_EXCLAIM
    K_QUOTEDBL = Key.K_QUOTEDBL
    K_HASH = Key.K_HASH
    K_DOLLAR = Key.K_DOLLAR
    K_AMPERSAND = Key.K_AMPERSAND
    K_QUOTE = Key.K_QUOTE
    K_LEFTPAREN = Key.K_LEFTPAREN
    K_RIGHTPAREN = Key.K_RIGHTPAREN
    K_ASTERISK = Key.K_ASTERISK
    K_PLUS = Key.K_PLUS
    K_COMMA = Key.K_COMMA
    K_MINUS = Key.K_MINUS
    K_PERIOD = Key.K_PERIOD
    K_SLASH = Key.K_SLASH
    K_0 = Key.K_0
    K_1 = Key.K_1
    K_2 = Key.K_2
    K_3 = Key.K_3
    K_4 = Key.K_4
    K_5 = Key.K_5
    K_6 = Key.K_6
    K_7 = Key.K_7
    K_8 = Key.K_8
    K_9 = Key.K_9
    K_COLON = Key.K_COLON
    K_SEMICOLON = Key.K_SEMICOLON
    K_LESS = Key.K_LESS
    K_EQUALS = Key.K_EQUALS
    K_GREATER = Key.K_GREATER
    K_QUESTION = Key.K_QUESTION
    K_AT = Key.K_AT
    K_LEFTBRACKET = Key.K_LEFTBRACKET
    K_BACKSLASH = Key.K_BACKSLASH
    K_RIGHTBRACKET = Key.K_RIGHTBRACKET
    K_CARET = Key.K_CARET
    K_UNDERSCORE = Key.K_UNDERSCORE
    K_BACKQUOTE = Key.K_BACKQUOTE
    K_a = Key.K_a
    K_b = Key.K_b
    K_c = Key.K_c
    K_d = Key.K_d
    K_e = Key.K_e
    K_f = Key.K_f
    K_g = Key.K_g
    K_h = Key.K_h
    K_i = Key.K_i
    K_j = Key.K_j
    K_k = Key.K_k
    K_l = Key.K_l
    K_m = Key.K_m
    K_n = Key.K_n
    K_o = Key.K_o
    K_p = Key.K_p
    K_q = Key.K_q
    K_r = Key.K_r
    K_s = Key.K_s
    K_t = Key.K_t
    K_u = Key.K_u
    K_v = Key.K_v
    K_w = Key.K_w
    K_x = Key.K_x
    K_y = Key.K_y
    K_z = Key.K_z
    K_DELETE = Key.K_DELETE
    K_KP0 = Key.K_KP0
    K_KP1 = Key.K_KP1
    K_KP2 = Key.K_KP2
    K_KP3 = Key.K_KP3
    K_KP4 = Key.K_KP4
    K_KP5 = Key.K_KP5
    K_KP6 = Key.K_KP6
    K_KP7 = Key.K_KP7
    K_KP8 = Key.K_KP8
    K_KP9 = Key.K_KP9
    K_KP_PERIOD = Key.K_KP_PERIOD
    K_KP_DIVIDE = Key.K_KP_DIVIDE
    K_KP_MULTIPLY = Key.K_KP_MULTIPLY
    K_KP_MINUS = Key.K_KP_MINUS
    K_KP_PLUS = Key.K_KP_PLUS
    K_KP_ENTER = Key.K_KP_ENTER
    K_KP_EQUALS = Key.K_KP_EQUALS
    K_UP = Key.K_UP
    K_DOWN = Key.K_DOWN
    K_RIGHT = Key.K_RIGHT
    K_LEFT = Key.K_LEFT
    K_INSERT = Key.K_INSERT
    K_HOME = Key.K_HOME
    K_END = Key.K_END
    K_PAGEUP = Key.K_PAGEUP
    K_PAGEDOWN = Key.K_PAGEDOWN
    K_F1 = Key.K_F1
    K_F2 = Key.K_F2
    K_F3 = Key.K_F3
    K_F4 = Key.K_F4
    K_F5 = Key.K_F5
    K_F6 = Key.K_F6
    K_F7 = Key.K_F7
    K_F8 = Key.K_F8
    K_F9 = Key.K_F9
    K_F10 = Key.K_F10
    K_F11 = Key.K_F11
    K_F12 = Key.K_F12
    K_F13 = Key.K_F13
    K_F14 = Key.K_F14
    K_F15 = Key.K_F15
    K_NUMLOCK = Key.K_NUMLOCK
    K_CAPSLOCK = Key.K_CAPSLOCK
    K_SCROLLOCK = Key.K_SCROLLOCK
    K_RSHIFT = Key.K_RSHIFT
    K_LSHIFT = Key.K_LSHIFT
    K_RCTRL = Key.K_RCTRL
    K_LCTRL = Key.K_LCTRL
    K_RALT = Key.K_RALT
    K_LALT = Key.K_LALT
    K_RMETA = Key.K_RMETA
    K_LMETA = Key.K_LMETA
    K_LSUPER = Key.K_LSUPER
    K_RSUPER = Key.K_RSUPER
    K_MODE = Key.K_MODE
    K_HELP = Key.K_HELP
    K_PRINT = Key.K_PRINT
    K_SYSREQ = Key.K_SYSREQ
    K_BREAK = Key.K_BREAK
    K_MENU = Key.K_MENU
    K_POWER = Key.K_POWER
    K_EURO = Key.K_EURO
