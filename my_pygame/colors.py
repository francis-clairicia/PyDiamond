# -*- coding: Utf-8 -*

from pygame.color import Color

WHITE = Color(255, 255, 255)
BLACK = Color(0, 0, 0)
GRAY = Color(127, 127, 127)
GRAY_DARK = Color(95, 95, 95)
GRAY_LIGHT = Color(175, 175, 175)
RED = Color(255, 0, 0)
RED_DARK = Color(128, 0, 0)
RED_LIGHT = Color(255, 128, 128)
ORANGE = Color(255, 175, 0)
YELLOW = Color(255, 255, 0)
GREEN = Color(0, 255, 0)
GREEN_DARK = Color(0, 128, 0)
GREEN_LIGHT = Color(128, 255, 128)
CYAN = Color(0, 255, 255)
BLUE = Color(0, 0, 255)
BLUE_DARK = Color(0, 0, 128)
BLUE_LIGHT = Color(128, 128, 255)
MAGENTA = Color(255, 0, 255)
PURPLE = Color(165, 0, 255)
TRANSPARENT = Color(0, 0, 0, 0)


def change_brightness(color: Color, value: int) -> Color:
    c = Color(color)
    H, S, V, A = c.hsva
    V += value
    if V > 100:
        V = 100
    elif V < 0:
        V = 0
    c.hsva = (H, S, V, A)
    return c


def change_saturation(color: Color, value: int) -> Color:
    c = Color(color)
    H, S, V, A = c.hsva
    S += value
    if S > 100:
        S = 100
    elif S < 0:
        S = 0
    c.hsva = (H, S, V, A)
    return c


def set_color_alpha(color: Color, value: int) -> Color:
    return Color(color.r, color.g, color.b, value)
