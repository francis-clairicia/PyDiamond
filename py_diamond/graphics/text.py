# -*- coding: Utf-8 -*

__all__ = ["MetaText", "Text", "TextImage"]

import os.path
from contextlib import suppress
from enum import Enum, unique
from operator import truth
from typing import Dict, List, Optional, Tuple, Union
from textwrap import wrap as textwrap

import pygame.transform

from .color import Color, BLACK
from .drawable import TDrawable, MetaTDrawable
from .font import Font, SysFont, get_default_font
from .image import Image
from .rect import Rect
from .renderer import Renderer, SurfaceRenderer
from .surface import Surface, create_surface
from ..system.configuration import ConfigAttribute, Configuration, initializer
from ..system.utils import valid_float, valid_integer
from .theme import MetaThemedObject, ThemeType

_TextFont = Union[Font, Tuple[Optional[str], int]]


class MetaText(MetaTDrawable, MetaThemedObject):
    pass


class Text(TDrawable, metaclass=MetaText):
    @unique
    class Justify(str, Enum):
        LEFT = "left"
        RIGHT = "right"
        CENTER = "center"

    @initializer
    def __init__(
        self,
        /,
        message: str = "",
        *,
        font: Optional[_TextFont] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        color: Color = BLACK,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__()
        self.__custom_font: Dict[int, Font] = dict()
        self.__default_image: Surface = create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__justify: Text.Justify
        self.set_font(font, bold=bold, italic=italic, underline=underline)
        self.wrap = wrap
        self.message = message
        self.color = color
        self.justify = justify
        self.shadow = (shadow_x, shadow_y)
        self.shadow_color = shadow_color

    def draw_onto(self, /, target: Renderer) -> None:
        image: Surface = self.__image
        topleft: Tuple[float, float] = self.topleft
        target.draw(image, topleft)

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self, /) -> Tuple[float, float]:
        return self.__image.get_size()

    def get(self, /, wrapped: bool = False) -> str:
        message: str = self.message
        if not wrapped:
            return message
        wrap: int = self.wrap
        return "\n".join(textwrap(message, width=wrap)) if wrap > 0 else message

    @staticmethod
    def create_font(
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> Font:
        obj: Font
        if font is None:
            font = (None, 15)
        if isinstance(font, (tuple, list)):
            font_family, font_size = font
            if font_family is None:
                font_family = Text.get_default_font()
            if os.path.isfile(font_family):
                obj = Font(font_family, font_size)
                if bold is not None:
                    obj.set_bold(bold)
                if italic is not None:
                    obj.set_italic(italic)
            else:
                obj = SysFont(font_family, font_size, bold=truth(bold), italic=truth(italic))
        elif isinstance(font, Font):
            obj = font
            if bold is not None:
                obj.set_bold(bold)
            if italic is not None:
                obj.set_italic(italic)
        else:
            raise TypeError("Invalid arguments")
        if underline is not None:
            obj.set_underline(underline)
        return obj

    @staticmethod
    def get_default_font() -> str:
        font: str = getattr(Text, "__default_font__", get_default_font())
        return font

    @staticmethod
    def set_default_font(font: Union[str, None]) -> None:
        if font is None:
            with suppress(AttributeError):
                delattr(Text, "__default_font__")
        else:
            setattr(Text, "__default_font__", str(font))

    def set_font(
        self,
        /,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> None:
        self.config.set(
            "font",
            Text.create_font(font, bold=bold, italic=italic, underline=underline),
        )

    def set_custom_line_font(self, /, index: int, font: Font) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font[index] = Text.create_font(font)
        self.config.update_all_options()

    def remove_custom_line_font(self, /, index: int) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font.pop(index, None)
        self.config.update_all_options()

    def _apply_both_rotation_and_scale(self, /) -> None:
        self.__image = pygame.transform.rotozoom(self.__default_image, self.angle, self.scale)

    def _apply_only_scale(self, /) -> None:
        self.__image = pygame.transform.rotozoom(self.__default_image, 0, self.scale)

    def _apply_only_rotation(self, /) -> None:
        self.__image = pygame.transform.rotate(self.__default_image, self.angle)

    def __render_text(self, /, color: Color) -> Surface:
        render_lines: List[Surface] = list()
        render_width: float = 0
        render_height: float = 0
        default_font: Font = self.font
        custom_font: Dict[int, Font] = self.__custom_font
        for index, line in enumerate(self.get(wrapped=True).splitlines()):
            font = custom_font.get(index, default_font)
            render = font.render(line, True, color)
            render_width = max(render_width, render.get_width())
            render_height += render.get_height()
            render_lines.append(render)
        if not render_lines:
            return create_surface((0, 0))
        if len(render_lines) == 1:
            return render_lines[0]
        text: Surface = create_surface((render_width, render_height))
        text_rect: Rect = text.get_rect()
        top: int = 0
        params: Dict[str, int] = {
            Text.Justify.LEFT: {"left": text_rect.left},
            Text.Justify.RIGHT: {"right": text_rect.right},
            Text.Justify.CENTER: {"centerx": text_rect.centerx},
        }[self.__justify]
        for render in render_lines:
            text.blit(render, render.get_rect(**params, top=top))
            top += render.get_height()
        return text

    def _render(self, /) -> Surface:
        text: Surface = self.__render_text(self.color)
        shadow_x, shadow_y = self.shadow
        shadow_x = int(shadow_x)
        shadow_y = int(shadow_y)
        if shadow_x == 0 and shadow_y == 0:
            return text
        shadow_text: Surface = self.__render_text(self.shadow_color)
        render = create_surface((text.get_width() + abs(shadow_x), text.get_height() + abs(shadow_y)))

        text_x: float = 0
        text_y: float = 0

        if shadow_x < 0:
            text_x = -shadow_x
            shadow_x = 0
        if shadow_y < 0:
            text_y = -shadow_y
            shadow_y = 0

        render.blit(shadow_text, (shadow_x, shadow_y))
        render.blit(text, (text_x, text_y))

        return render

    config: Configuration = Configuration(
        "message",
        "font",
        "color",
        "wrap",
        "justify",
        "shadow_x",
        "shadow_y",
        "shadow",
        "shadow_color",
        autocopy=True,
    )

    config.enum("justify", Justify, return_value=True)

    config.value_validator_static("message", str)
    config.value_converter_static("font", create_font)
    config.value_converter_static("wrap", valid_integer(min_value=0))
    config.value_validator_static("color", Color)
    config.value_converter_static("shadow_x", float)
    config.value_converter_static("shadow_y", float)
    config.value_converter_static("shadow", tuple)
    config.value_validator_static("shadow_color", Color)

    config.set_autocopy("font", copy_on_get=False, copy_on_set=False)

    @config.on_update
    def __update_surface(self, /) -> None:
        if self.config.has_initialization_context():
            self.__default_image = self._render()
            self._apply_rotation_scale()
        else:
            center: Tuple[float, float] = self.center
            self.__default_image = self._render()
            self._apply_rotation_scale()
            self.center = center

    message: ConfigAttribute[str] = ConfigAttribute()
    font: ConfigAttribute[Font] = ConfigAttribute()
    color: ConfigAttribute[Color] = ConfigAttribute()
    wrap: ConfigAttribute[int] = ConfigAttribute()
    justify: ConfigAttribute[str] = ConfigAttribute()
    shadow_x: ConfigAttribute[float] = ConfigAttribute()
    shadow_y: ConfigAttribute[float] = ConfigAttribute()
    shadow: ConfigAttribute[Tuple[float, float]] = ConfigAttribute()
    shadow_color: ConfigAttribute[Color] = ConfigAttribute()

    config.getter("shadow", lambda self: (self.shadow_x, self.shadow_y))
    config.setter("shadow", lambda self, pos: self.config(shadow_x=pos[0], shadow_y=pos[1]))


class TextImage(Text):
    @unique
    class Compound(str, Enum):
        LEFT = "left"
        RIGHT = "right"
        TOP = "top"
        BOTTOM = "bottom"
        CENTER = "center"

    @initializer
    def __init__(
        self,
        /,
        message: str = "",
        *,
        img: Optional[Surface] = None,
        compound: str = "left",
        distance: float = 5,
        font: Optional[_TextFont] = None,
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
        color: Color = BLACK,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        theme: Optional[ThemeType] = None,
    ) -> None:
        super().__init__(
            message=message,
            font=font,
            bold=bold,
            italic=italic,
            underline=underline,
            color=color,
            wrap=wrap,
            justify=justify,
            shadow_x=shadow_x,
            shadow_y=shadow_y,
            shadow_color=shadow_color,
            theme=theme,
        )
        self.__img: Optional[Image] = None
        self.__compound: TextImage.Compound
        self.__img_angle: float = 0
        self.__img_scale: float = 1
        self.img = img
        self.compound = compound
        self.distance = distance

    def get_img_angle(self, /) -> float:
        return self.__img_angle

    def get_img_scale(self, /) -> float:
        return self.__img_scale

    def img_rotate(self, /, angle_offset: float) -> None:
        if self.__img is not None:
            self.__img.rotate(angle_offset)
            self.__img_angle = self.__img.angle

    def img_set_rotation(self, /, angle: float) -> None:
        if self.__img is not None:
            self.__img.set_rotation(angle)
            self.__img_angle = self.__img.angle

    def img_set_scale(self, /, scale: float) -> None:
        if self.__img is not None:
            self.__img.set_scale(scale)
            self.__img_scale = self.__img.scale

    def img_scale_to_width(self, /, width: float) -> None:
        if self.__img is not None:
            self.__img.scale_to_width(width)
            self.__img_scale = self.__img.scale

    def img_scale_to_height(self, /, height: float) -> None:
        if self.__img is not None:
            self.__img.scale_to_height(height)
            self.__img_scale = self.__img.scale

    def img_scale_to_size(self, /, size: Tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.scale_to_size(size)
            self.__img_scale = self.__img.scale

    def img_set_min_width(self, /, width: float) -> None:
        if self.__img is not None:
            self.__img.set_min_width(width)
            self.__img_scale = self.__img.scale

    def img_set_max_width(self, /, width: float) -> None:
        if self.__img is not None:
            self.__img.set_max_width(width)
            self.__img_scale = self.__img.scale

    def img_set_min_height(self, /, height: float) -> None:
        if self.__img is not None:
            self.__img.set_min_height(height)
            self.__img_scale = self.__img.scale

    def img_set_max_height(self, /, height: float) -> None:
        if self.__img is not None:
            self.__img.set_max_height(height)
            self.__img_scale = self.__img.scale

    def img_set_min_size(self, /, size: Tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.set_min_size(size)
            self.__img_scale = self.__img.scale

    def img_set_max_size(self, /, size: Tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.set_max_size(size)
            self.__img_scale = self.__img.scale

    def _render(self, /) -> Surface:
        text: Surface = super()._render()
        if self.__img is None:
            return text
        text_width, text_height = text.get_size()
        img_width, img_height = self.__img.get_size()
        if img_width == 0 or img_height == 0:
            return text
        if text_width == 0 or text_height == 0:
            return self.__img.get(apply_rotation_scale=True)

        text_rect: Rect = text.get_rect()
        offset: float = self.distance
        render_width: float
        render_height: float
        if self.__compound in [TextImage.Compound.LEFT, TextImage.Compound.RIGHT]:
            render_width = text_width + img_width + offset
            render_height = max(text_height, img_height)
        elif self.__compound in [TextImage.Compound.TOP, TextImage.Compound.BOTTOM]:
            render_width = max(text_width, img_width)
            render_height = text_height + img_height + offset
        else:
            render_width = max(text_width, img_width)
            render_height = max(text_height, img_height)
        render: Surface = create_surface((render_width, render_height))
        render_rect: Rect = render.get_rect()

        if self.__compound == TextImage.Compound.LEFT:
            text_rect.midleft = render_rect.midleft
            self.__img.midright = render_rect.midright
        elif self.__compound == TextImage.Compound.RIGHT:
            text_rect.midright = render_rect.midright
            self.__img.midleft = render_rect.midleft
        elif self.__compound == TextImage.Compound.TOP:
            text_rect.midtop = render_rect.midtop
            self.__img.midbottom = render_rect.midbottom
        elif self.__compound == TextImage.Compound.BOTTOM:
            text_rect.midbottom = render_rect.midbottom
            self.__img.midtop = render_rect.midtop
        else:
            self.__img.center = text_rect.center = render_rect.center

        self.__img.draw_onto(SurfaceRenderer(render))
        render.blit(text, text_rect)

        return render

    config = Configuration("img", "compound", "distance", parent=Text.config)
    config.set_autocopy("img", copy_on_get=False, copy_on_set=False)

    config.enum("compound", Compound, return_value=True)

    config.value_validator_static("img", Surface, accept_none=True)
    config.value_converter_static("distance", valid_float(min_value=0))

    @config.getter("img")
    def __get_img_surface(self, /) -> Optional[Surface]:
        img: Optional[Image] = self.__img
        if img is None:
            return None
        return img.get()

    @config.setter("img")
    def __update_img(self, /, surface: Optional[Surface]) -> None:
        if surface is None:
            self.__img = None
            return
        img: Optional[Image] = self.__img
        if img is None:
            self.__img = img = _BoundImage(self, surface)
            img.set_scale(self.__img_scale)
            img.set_rotation(self.__img_angle)
        else:
            img.set(surface)

    img: ConfigAttribute[Optional[Surface]] = ConfigAttribute()
    compound: ConfigAttribute[str] = ConfigAttribute()
    distance: ConfigAttribute[float] = ConfigAttribute()


class _BoundImage(Image):
    def __init__(self, /, text: TextImage, image: Surface) -> None:
        super().__init__(image)
        self.__text: TextImage = text

    def _apply_both_rotation_and_scale(self, /) -> None:
        super()._apply_both_rotation_and_scale()
        self.__text.config.update_all_options()

    def set(self, /, image: Surface) -> None:
        super().set(image)
        self.__text.config.update_all_options()
