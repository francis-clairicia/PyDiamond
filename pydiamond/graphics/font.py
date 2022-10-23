# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Font module"""

from __future__ import annotations

__all__ = [
    "Font",
    "FontFactory",
    "SysFont",
]


import os
from copy import copy
from enum import IntFlag, unique
from typing import TYPE_CHECKING, Any, ClassVar, Final, Iterable, NamedTuple, TypeAlias, overload

import pygame.freetype as _pg_freetype
import pygame.sysfont as _pg_sysfont

from ..math.rect import Rect, move_rect_in_place
from ..system.configuration import ConfigurationTemplate, OptionAttribute
from ..system.object import Object, final

if TYPE_CHECKING:
    from pygame._common import _CanBeRect, _ColorValue, _Coordinate, _FileArg  # pyright: reportMissingModuleSource=false

    from .surface import Surface


def get_fonts() -> list[str]:
    return _pg_sysfont.get_fonts()  # type: ignore[no-untyped-call]


def get_default_font() -> str:
    return _pg_freetype.get_default_font()


def match_font(name: str | bytes | Iterable[str | bytes], bold: bool = False, italic: bool = False) -> str | None:
    return _pg_sysfont.match_font(name, bold=bold, italic=italic)  # type: ignore[no-untyped-call]


def SysFont(name: str | bytes | Iterable[str | bytes], size: float, bold: bool = False, italic: bool = False) -> Font:
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

    def font_constructor(fontpath: str, size: float, bold: bool, italic: bool) -> Font:
        font: Font = Font(fontpath, size)
        font.config.update(wide=bold, oblique=italic)
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
    __slots__ = ("__ft", "__weakref__")

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

    size: OptionAttribute[float] = OptionAttribute()
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
        copy_self.__ft = copy_ft = self.__factory(ft.path, size=1, resolution=self.resolution)
        for attr in {*self.config.known_options(include_section_options=False), "size", "pad", "origin"}:
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

    def get_scale_size(self) -> tuple[float, float]:
        size = self.__ft.size
        if not isinstance(size, tuple):
            return (size, size)
        return size

    def set_scale_size(self, size: tuple[float, float]) -> None:
        w, h = size
        self.__ft.size = (w, h)

    @overload
    def get_rect(
        self,
        text: str,
        style: int = ...,
        rotation: int = ...,
        size: float = ...,
    ) -> Rect:
        ...

    @overload
    def get_rect(
        self,
        text: str,
        style: int = ...,
        rotation: int = ...,
        size: float = ...,
        *,
        x: float = ...,
        y: float = ...,
        top: float = ...,
        left: float = ...,
        bottom: float = ...,
        right: float = ...,
        topleft: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        center: tuple[float, float] = ...,
        centerx: float = ...,
        centery: float = ...,
    ) -> Rect:
        ...

    def get_rect(
        self,
        text: str,
        style: int = STYLE_DEFAULT,
        rotation: int = 0,
        size: float = 0,
        **kwargs: Any,
    ) -> Rect:
        try:
            self.__ft.pad = rotation == 0
            r = self.__ft.get_rect(text or "", style=style, rotation=rotation, size=size)
        finally:
            self.__ft.pad = True
        if kwargs:
            move_rect_in_place(r, **kwargs)
        return r

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
        try:
            self.__ft.pad = rotation == 0
            return self.__ft.render(
                text or "",
                fgcolor=fgcolor,
                bgcolor=bgcolor,
                style=style,
                rotation=rotation,
                size=size,
            )
        finally:
            self.__ft.pad = True

    def render_to(
        self,
        surf: Surface,
        dest: _Coordinate | _CanBeRect,
        text: str,
        fgcolor: _ColorValue,
        bgcolor: _ColorValue | None = None,
        style: int = STYLE_DEFAULT,
        rotation: int = 0,
        size: float = 0,
    ) -> Rect:
        assert fgcolor is not None, "Give a foreground color"
        try:
            self.__ft.pad = rotation == 0
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
        finally:
            self.__ft.pad = True

    config.add_enum_converter("style", FontStyle, store_value=True)
    config.add_value_converter_on_set_static("size", float)
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

    @config.getter_with_key("size", use_override=False)
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

    @config.setter_with_key("size", use_override=False)
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


_TupleFont: TypeAlias = tuple[str | None, float]
_TextFont: TypeAlias = Font | _TupleFont


@final
class FontFactory(Object):
    __slots__ = ("__name", "__weakref__")

    def __init__(self, name: str | None) -> None:
        super().__init__()
        self.__name: str | None = name

    def __call__(self, size: float, bold: bool | None = None, italic: bool | None = None, underline: bool | None = None) -> Font:
        tuple_font = (self.__name, size)
        return self.create_font(tuple_font, bold=bold, italic=italic, underline=underline)

    @staticmethod
    def create_font(
        font: _TextFont | None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
    ) -> Font:
        obj: Font
        if font is None:
            font = (None, 15)
        if isinstance(font, (tuple, list)):
            font_family, font_size = font
            if font_family is None or os.path.isfile(font_family):
                obj = Font(font_family, font_size)
                if bold is not None:
                    obj.wide = bold
                if italic is not None:
                    obj.oblique = italic
            else:
                obj = SysFont(font_family, font_size, bold=bool(bold), italic=bool(italic))
        elif isinstance(font, Font):
            obj = copy(font)
            if bold is not None:
                obj.wide = bold
            if italic is not None:
                obj.oblique = italic
        else:
            raise TypeError("Invalid arguments")
        if underline is not None:
            obj.underline = underline
        return obj
