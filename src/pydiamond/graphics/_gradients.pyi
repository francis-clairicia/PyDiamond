# isort: dont-add-imports

__all__: list[str] = []

from collections.abc import Callable, Sequence
from typing import Final

from pygame import Rect, Surface, Vector2

BLEND_MODES_AVAILABLE: Final[bool]

type _Number = int | float
type _Size = tuple[_Number, _Number]
type _Coordinate = tuple[_Number, _Number] | Vector2

type _OpaqueColor = tuple[int, int, int]
type _ColorWithTransparency = tuple[int, int, int, int]
type _Color = _OpaqueColor | _ColorWithTransparency

type _Function = Callable[[_Number], _Number]

class ColorInterpolator:
    def __init__(
        self,
        distance: _Number,
        color1: _Color,
        color2: _Color,
        rfunc: _Function,
        gfunc: _Function,
        bfunc: _Function,
        afunc: _Function,
    ): ...
    def eval(self, x: _Number) -> _ColorWithTransparency: ...

class FunctionInterpolator:
    def __init__(self, startvalue: _Number, endvalue: _Number, trange: _Number, func: _Function): ...
    def eval(self, x: _Number) -> int: ...

def vertical(size: _Size, startcolor: _Color, endcolor: _Color) -> Surface: ...
def horizontal(size: _Size, startcolor: _Color, endcolor: _Color) -> Surface: ...
def radial(radius: _Number, startcolor: _Color, endcolor: _Color) -> Surface: ...
def squared(width: _Number, startcolor: _Color, endcolor: _Color) -> Surface: ...
def vertical_func(
    size: _Size,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
) -> Surface: ...
def horizontal_func(
    size: _Size,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
) -> Surface: ...
def radial_func(
    radius: _Number,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    colorkey: _Color = ...,
) -> Surface: ...
def radial_func_offset(
    radius: _Number,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    colorkey: _Color = ...,
    offset: _Coordinate = ...,
) -> Surface: ...
def squared_func(
    width: _Number,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    offset: _Coordinate = ...,
) -> Surface: ...
def draw_gradient(
    surface: Surface,
    startpoint: _Coordinate,
    endpoint: _Coordinate,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    mode: int = ...,
) -> None: ...
def draw_circle(
    surface: Surface,
    startpoint: _Coordinate,
    endpoint: _Coordinate,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    mode: int = ...,
) -> None: ...
def draw_squared(
    surface: Surface,
    startpoint: _Coordinate,
    endpoint: _Coordinate,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    mode: int = ...,
) -> None: ...
def chart(
    startpoint: _Coordinate,
    endpoint: _Coordinate,
    startcolor: _Color,
    endcolor: _Color,
    Rfunc: _Function = ...,
    Gfunc: _Function = ...,
    Bfunc: _Function = ...,
    Afunc: _Function = ...,
    scale: _Number | None = ...,
) -> Surface: ...
def genericFxyGradient(
    surf: Surface,
    clip: Rect,
    color1: _Color,
    color2: _Color,
    func: Callable[[_Number, _Number], _Number],
    intx: Sequence[_Number],
    yint: Sequence[_Number],
    zint: Sequence[_Number] | None = ...,
) -> None: ...
