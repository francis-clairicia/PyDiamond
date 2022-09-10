# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Font module"""

from __future__ import annotations

__all__ = [
    "Font",
    "SysFont",
]

from enum import IntFlag, unique
from typing import TYPE_CHECKING, Any, ClassVar, Final, Iterable, NamedTuple

import pygame.freetype as _pg_freetype
import pygame.sysfont as _pg_sysfont

from ..math.vector2 import Vector2
from ..system.configuration import ConfigurationTemplate, OptionAttribute
from ..system.object import Object, final
from .rect import Rect
from .surface import Surface

if TYPE_CHECKING:
    from pygame._common import _ColorValue, _FileArg  # pyright: reportMissingModuleSource=false


def get_fonts() -> list[str]:
    return _pg_sysfont.get_fonts()  # type: ignore[no-untyped-call]


def get_default_font() -> str:
    return _pg_freetype.get_default_font()


def match_font(name: str | bytes | Iterable[str | bytes], bold: bool = False, italic: bool = False) -> str | None:
    return _pg_sysfont.match_font(name, bold=bold, italic=italic)  # type: ignore[no-untyped-call]


def SysFont(name: str | bytes | Iterable[str | bytes], size: int, bold: bool = False, italic: bool = False) -> Font:
    """SysFont(name, size, bold=False, italic=False) -> Font
    Create a pygame Font from system font resources.

    This will search the system fonts for the given font
    name. You can also enable bold or italic styles, and
    the appropriate system font will be selected if available.

    This will always return a valid Font object, and will
    fallback on the builtin pygame font if the given font
    is not found.

    Name can also be an iterable of font names, a string of
    comma-separated font names, or a bytes of comma-separated
    font names, in which case the set of names will be searched
    in order. Pygame uses a small set of common font aliases. If the
    specific font you ask for is not available, a reasonable
    alternative may be used.
    """

    def font_constructor(fontpath: str, size: int, bold: bool, italic: bool) -> Font:
        font: Font = Font(fontpath, size)
        font.wide = bold
        font.oblique = italic
        return font

    font: Font = _pg_sysfont.SysFont(name, size, bold=bold, italic=italic, constructor=font_constructor)  # type: ignore[no-untyped-call]
    return font


class GlyphMetrics(NamedTuple):
    min_x: int
    max_x: int
    min_y: int
    max_y: int
    horizontal_advance_x: float
    horizontal_advance_y: float


@unique
class FontStyle(IntFlag):
    NORMAL = _pg_freetype.STYLE_NORMAL
    OBLIQUE = _pg_freetype.STYLE_OBLIQUE
    STRONG = _pg_freetype.STYLE_STRONG
    UNDERLINE = _pg_freetype.STYLE_UNDERLINE
    WIDE = _pg_freetype.STYLE_WIDE


STYLE_DEFAULT: Final[int] = _pg_freetype.STYLE_DEFAULT


class FontSizeInfo(NamedTuple):
    point_size: int
    width: int
    height: int
    horizontal_ppem: float
    vertical_ppem: float


@final
class Font(Object):
    from pygame import encode_file_path as __encode_file_path  # type: ignore[misc]

    __factory = staticmethod(_pg_freetype.Font)
    __encode_file_path = staticmethod(__encode_file_path)
    __get_default_resolution = staticmethod(_pg_freetype.get_default_resolution)
    __default_font = __encode_file_path(get_default_font())

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "size",
        "style",
        "underline",
        "strong",
        "oblique",
        "wide",
        "strength",
        "underline_adjustment",
        "use_bitmap_strikes",
        "antialiased",
        "kerning",
        # "vertical",
        "ucs4",
    )

    style: OptionAttribute[FontStyle] = OptionAttribute()
    underline: OptionAttribute[bool] = OptionAttribute()
    strong: OptionAttribute[bool] = OptionAttribute()
    oblique: OptionAttribute[bool] = OptionAttribute()
    wide: OptionAttribute[bool] = OptionAttribute()
    strength: OptionAttribute[float] = OptionAttribute()
    underline_adjustment: OptionAttribute[float] = OptionAttribute()
    use_bitmap_strikes: OptionAttribute[bool] = OptionAttribute()
    antialiased: OptionAttribute[bool] = OptionAttribute()
    kerning: OptionAttribute[bool] = OptionAttribute()
    # vertical: OptionAttribute[bool] = OptionAttribute()
    ucs4: OptionAttribute[bool] = OptionAttribute()

    def __init__(
        self,
        file: _FileArg | None,
        size: float = 0,
    ) -> None:
        size = max(size, 1)
        bfile: Any
        if isinstance(file, str):
            try:
                bfile = self.__encode_file_path(file, ValueError)
            except ValueError:
                bfile = ""
        else:
            bfile = file
        if isinstance(bfile, bytes) and bfile == self.__default_font:
            file = None
        if file is None:
            resolution = int(self.__get_default_resolution() * 0.6875)
            if resolution == 0:
                resolution = 1
        else:
            resolution = 0
        self.__ft: _pg_freetype.Font = self.__factory(file, size=size, resolution=resolution)
        self.__ft.strength = 1.0 / 12.0
        self.__ft.kerning = False
        self.__ft.origin = False
        self.__ft.pad = True
        self.__ft.ucs4 = True
        self.__ft.underline_adjustment = 1.0
        self.__ft.antialiased = True

        super().__init__()

    def copy(self) -> Font:
        cls = self.__class__
        copy_self = cls.__new__(cls)
        ft = self.__ft
        try:
            ft_size = float(ft.size)  # type: ignore[arg-type]
        except ValueError:
            ft_size = max(ft.size)  # type: ignore[arg-type]
        copy_self.__ft = copy_ft = self.__factory(ft.path, size=ft_size, resolution=self.resolution)
        for attr in {*self.config.info.options, "pad", "origin"}:
            setattr(copy_ft, attr, getattr(ft, attr))
        return copy_self

    __copy__ = copy

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> Font:  # allow 'deep' copy
        return self.__copy__()

    @property
    def name(self) -> str:
        return self.__ft.name

    @property
    def path(self) -> str:
        return self.__ft.path

    @property
    def resolution(self) -> int:
        return self.__ft.resolution

    @property
    def size(self) -> float | tuple[float, float]:
        return self.__ft.size

    @size.setter
    def size(self, value: float | tuple[float, float]) -> None:
        self.__ft.size = value

    @property
    def height(self) -> int:
        return self.__ft.height

    @property
    def ascender(self) -> int:
        return self.__ft.ascender

    @property
    def descender(self) -> int:
        return self.__ft.descender

    @property
    def fixed_width(self) -> int:
        return self.__ft.fixed_width

    @property
    def fixed_sizes(self) -> int:
        return self.__ft.fixed_sizes

    @property
    def scalable(self) -> bool:
        return self.__ft.scalable

    def get_rect(
        self,
        text: str,
        style: int = STYLE_DEFAULT,
        rotation: int = 0,
        size: float = 0,
    ) -> Rect:
        return self.__ft.get_rect(text or "", style=style, rotation=rotation, size=size)

    def get_metrics(self, text: str, size: float = 0) -> list[GlyphMetrics]:
        return [GlyphMetrics._make(metrics) for metrics in self.__ft.get_metrics(text or "", size=size)]

    def get_sized_ascender(self, size: float = 0) -> int:
        return self.__ft.get_sized_ascender(size)

    def get_sized_descender(self, size: float = 0) -> int:
        return self.__ft.get_sized_descender(size)

    def get_sized_height(self, size: float = 0) -> int:
        return self.__ft.get_sized_height(size)

    def get_sized_glyph_height(self, size: float = 0) -> int:
        return self.__ft.get_sized_glyph_height(size)

    def get_sizes(self) -> list[FontSizeInfo]:
        return [FontSizeInfo._make(info) for info in self.__ft.get_sizes()]

    def render(
        self,
        text: str,
        fgcolor: _ColorValue,
        bgcolor: _ColorValue | None = None,
        style: int = STYLE_DEFAULT,
        rotation: int = 0,
        size: float = 0,
    ) -> tuple[Surface, Rect]:
        assert fgcolor is not None, "Give a foreground color"
        return self.__ft.render(
            text or "",
            fgcolor=fgcolor,
            bgcolor=bgcolor,
            style=style,
            rotation=rotation,
            size=size,
        )

    def render_to(
        self,
        surf: Surface,
        dest: tuple[float, float] | Vector2 | Rect,
        text: str,
        fgcolor: _ColorValue,
        bgcolor: _ColorValue | None = None,
        style: int = STYLE_DEFAULT,
        rotation: int = 0,
        size: float = 0,
    ) -> Rect:
        assert fgcolor is not None, "Give a foreground color"
        return self.__ft.render_to(
            surf,
            dest,  # type: ignore[arg-type]
            text or "",
            fgcolor=fgcolor,
            bgcolor=bgcolor,
            style=style,
            rotation=rotation,
            size=size,
        )

    config.use_descriptor("size", size)

    config.add_enum_converter("style", FontStyle, store_value=True)
    config.add_value_converter_on_set_static("underline", bool)
    config.add_value_converter_on_set_static("strong", bool)
    config.add_value_converter_on_set_static("oblique", bool)
    config.add_value_converter_on_set_static("wide", bool)
    config.add_value_converter_on_set_static("strength", float)
    config.add_value_converter_on_set_static("underline_adjustment", float)
    config.add_value_converter_on_set_static("use_bitmap_strikes", bool)
    config.add_value_converter_on_set_static("antialiased", bool)
    config.add_value_converter_on_set_static("kerning", bool)
    # config.add_value_converter_static("vertical", bool)
    config.add_value_converter_on_set_static("ucs4", bool)

    @config.getter_with_key("style", use_override=False)
    @config.getter_with_key("underline", use_override=False)
    @config.getter_with_key("strong", use_override=False)
    @config.getter_with_key("oblique", use_override=False)
    @config.getter_with_key("wide", use_override=False)
    @config.getter_with_key("strength", use_override=False)
    @config.getter_with_key("underline_adjustment", use_override=False)
    @config.getter_with_key("use_bitmap_strikes", use_override=False)
    @config.getter_with_key("antialiased", use_override=False)
    @config.getter_with_key("kerning", use_override=False)
    # @config.getter_key("vertical", use_override=False)
    @config.getter_with_key("ucs4", use_override=False)
    def __get_property(self, option: str) -> Any:
        return getattr(self.__ft, option)

    @config.setter_with_key("style", use_override=False)
    @config.setter_with_key("underline", use_override=False)
    @config.setter_with_key("strong", use_override=False)
    @config.setter_with_key("oblique", use_override=False)
    @config.setter_with_key("wide", use_override=False)
    @config.setter_with_key("strength", use_override=False)
    @config.setter_with_key("underline_adjustment", use_override=False)
    @config.setter_with_key("use_bitmap_strikes", use_override=False)
    @config.setter_with_key("antialiased", use_override=False)
    @config.setter_with_key("kerning", use_override=False)
    # @config.setter_key("vertical", use_override=False)
    @config.setter_with_key("ucs4", use_override=False)
    def __set_property(self, option: str, value: Any) -> Any:
        return setattr(self.__ft, option, value)

    del __get_property, __set_property
