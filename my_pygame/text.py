# -*- coding: Utf-8 -*

from __future__ import annotations

import os.path

from typing import Dict, List, Optional, Tuple, Union
from enum import Enum, unique
from textwrap import wrap
from operator import truth

import pygame.transform

from pygame.font import Font, SysFont, get_default_font
from pygame.color import Color
from pygame.surface import Surface
from pygame.rect import Rect

from .drawable import ThemedDrawable
from .colors import BLACK
from .theme import NoTheme, Theme
from .surface import create_surface

from .image import Image

_TextFont = Union[Font, Tuple[Optional[str], int]]


class Text(ThemedDrawable):
    @unique
    class Justify(str, Enum):
        LEFT = "left"
        RIGHT = "right"
        CENTER = "center"

    def __init__(
        self,
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
        theme: Optional[Theme] = None,
    ) -> None:
        super().__init__()
        self.__update: bool = True
        self.__str: str = str()
        self.__wrap: int = 0
        self.__font: Font = Text.create_font(None)
        self.__custom_font: Dict[int, Font] = dict()
        self.__color: Color = BLACK
        self.__justify: Text.Justify = Text.Justify.LEFT
        self.__shadow_offset: Tuple[float, float] = (0, 0)
        self.__shadow_color = BLACK
        self.__default_image: Surface = create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.set_font(font, bold=bold, italic=italic, underline=underline)
        self.message = message
        self.color = color
        self.wrap = wrap
        self.justify = justify
        self.shadow = (shadow_x, shadow_y)
        self.shadow_color = shadow_color

    def copy(self) -> Text:
        return Text(
            message=self.message,
            font=self.font,
            color=self.color,
            wrap=self.wrap,
            justify=self.justify,
            shadow_x=self.shadow_x,
            shadow_y=self.shadow_y,
            shadow_color=self.shadow_color,
            theme=NoTheme,
        )

    def draw_onto(self, surface: Surface) -> None:
        self.__update_surface()
        surface.blit(self.__image, self.topleft)

    def to_surface(self) -> Surface:
        self.__update_surface()
        return self.__image.copy()

    def get_local_size(self) -> Tuple[float, float]:
        self.__update_surface()
        return self.__default_image.get_size()

    def get_size(self) -> Tuple[float, float]:
        self.__update_surface()
        return self.__image.get_size()

    @staticmethod
    def create_font(
        font: Optional[_TextFont], bold: Optional[bool] = None, italic: Optional[bool] = None, underline: Optional[bool] = None
    ) -> Font:
        obj: Font
        if isinstance(font, (tuple, list)):
            if font[0] is not None and os.path.isfile(font[0]):
                obj = Font(*font)
                if bold is not None:
                    obj.set_bold(bold)
                if italic is not None:
                    obj.set_italic(italic)
            else:
                font_family: str = font[0] if font[0] is not None and font[0] else get_default_font()
                obj = SysFont(font_family, font[1], bold=truth(bold), italic=truth(italic))
        elif isinstance(font, Font):
            obj = font
            if bold is not None:
                obj.set_bold(bold)
            if italic is not None:
                obj.set_italic(italic)
        else:
            obj = SysFont(get_default_font(), 15, bold=truth(bold), italic=truth(italic))
        if underline is not None:
            obj.set_underline(underline)
        return obj

    def set_font(
        self,
        font: Optional[_TextFont],
        bold: Optional[bool] = None,
        italic: Optional[bool] = None,
        underline: Optional[bool] = None,
    ) -> None:
        self.__font = Text.create_font(font, bold=bold, italic=italic, underline=underline)
        self._need_update()

    def set_custom_line_font(self, index: int, font: Font) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font[index] = Text.create_font(font)
        self._need_update()

    def remove_custom_line_font(self, index: int) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font.pop(index, None)
        self._need_update()

    def _need_update(self) -> None:
        self.__update = True

    def __update_surface(self) -> None:
        if self.__update:
            self.__update = False
            center: Tuple[float, float] = self.center
            self.__default_image = self._render()
            self._apply_rotation_scale()
            self.center = center

    def _apply_rotation_scale(self) -> None:
        self.__image = pygame.transform.rotozoom(self.__default_image, self.angle, self.scale)

    def __render_text(self, color: Color) -> Surface:
        render_lines: List[Surface] = list()
        render_width: float = 0
        render_height: float = 0
        text: Surface
        default_font: Font = self.font
        custom_font: Dict[int, Font] = self.__custom_font
        for index, line in enumerate(self.message.splitlines()):
            font = custom_font.get(index, default_font)
            render = font.render(line, True, color)
            render_width = max(render_width, render.get_width())
            render_height += render.get_height()
            render_lines.append(render)
        if not render_lines:
            return create_surface((0, 0))
        if len(render_lines) == 1:
            text = render_lines[0]
        else:
            text = create_surface((render_width, render_height))
            text_rect = text.get_rect()
            top = 0
            params = {
                Text.Justify.LEFT: {"left": text_rect.left},
                Text.Justify.RIGHT: {"right": text_rect.right},
                Text.Justify.CENTER: {"centerx": text_rect.centerx},
            }[self.__justify]
            for render in render_lines:
                text.blit(render, render.get_rect(**params, top=top))
                top += render.get_height()
        return text

    def _render(self) -> Surface:
        text: Surface = self.__render_text(self.color)
        shadow_x, shadow_y = self.shadow
        if shadow_x == 0 and shadow_y == 0:
            return text
        render_width: float = text.get_width()
        render_height: float = text.get_height()
        shadow_text: Surface = self.__render_text(self.shadow_color)
        render_width += abs(shadow_x)
        render_height += abs(shadow_y)
        render = create_surface((render_width, render_height))

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

    @property
    def font(self) -> Font:
        return self.__font

    @font.setter
    def font(self, font: Font) -> None:
        self.set_font(font)

    @property
    def message(self) -> str:
        return self.__str

    @message.setter
    def message(self, string: str) -> None:
        if string != self.__str:
            self.__str = "\n".join(wrap(string, width=self.__wrap)) if self.__wrap > 0 else string
            self._need_update()

    @property
    def wrap(self) -> int:
        return self.__wrap

    @wrap.setter
    def wrap(self, value: int) -> None:
        value = max(int(value), 0)
        if value != self.__wrap:
            self.__wrap = value
            self.__str = "\n".join(wrap(self.__str, width=self.__wrap)) if self.__wrap > 0 else self.__str
            self._need_update()

    @property
    def justify(self) -> str:
        return str(self.__justify.value)

    @justify.setter
    def justify(self, justify: str) -> None:
        justify = Text.Justify(justify)
        if justify != self.__justify:
            self.__justify = justify
            self._need_update()

    @property
    def color(self) -> Color:
        return Color(self.__color)

    @color.setter
    def color(self, color: Color) -> None:
        if color != self.__color:
            self.__color = Color(color)
            self._need_update()

    @property
    def shadow(self) -> Tuple[float, float]:
        return self.__shadow_offset

    @shadow.setter
    def shadow(self, pos: Tuple[float, float]) -> None:
        if self.__shadow_offset != pos:
            self.__shadow_offset = pos
            self._need_update()

    @property
    def shadow_x(self) -> float:
        return self.shadow[0]

    @shadow_x.setter
    def shadow_x(self, shadow_x: float) -> None:
        self.shadow = (shadow_x, self.shadow_y)

    @property
    def shadow_y(self) -> float:
        return self.shadow[1]

    @shadow_y.setter
    def shadow_y(self, shadow_y: float) -> None:
        self.shadow = (self.shadow_x, shadow_y)

    @property
    def shadow_color(self) -> Color:
        return Color(self.__shadow_color)

    @shadow_color.setter
    def shadow_color(self, color: Color) -> None:
        if self.__shadow_color != color:
            self.__shadow_color = Color(color)
            self._need_update()


class TextImage(Text):
    @unique
    class Compound(str, Enum):
        LEFT = "left"
        RIGHT = "right"
        TOP = "top"
        BOTTOM = "bottom"
        CENTER = "center"

    def __init__(
        self,
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
        theme: Optional[Theme] = None,
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
            theme=NoTheme,
        )
        self.__img: Optional[Image] = _BoundImage(self, img) if img is not None else None
        self.__img_angle: float = 0
        self.__img_scale: float = 1
        self.__compound: TextImage.Compound = TextImage.Compound(compound)
        self.__distance: float = float(distance)
        self._need_update()

    def copy(self) -> TextImage:
        t: TextImage = TextImage(
            message=self.message,
            img=self.__img.get() if self.__img is not None else None,
            compound=self.__compound,
            font=self.font,
            color=self.color,
            wrap=self.wrap,
            justify=self.justify,
            shadow_x=self.shadow_x,
            shadow_y=self.shadow_y,
            shadow_color=self.shadow_color,
            theme=NoTheme,
        )
        if self.__img is not None:
            t.img_set_rotation(self.__img_angle)
            t.img_set_scale(self.__img_scale)
        return t

    def get_img_angle(self) -> float:
        return self.__img_angle

    def get_img_scale(self) -> float:
        return self.__img_scale

    def img_rotate(self, angle_offset: float) -> None:
        if self.__img is not None:
            self.__img.rotate(angle_offset)
            self.__img_angle = self.__img.angle

    def img_set_rotation(self, angle: float) -> None:
        if self.__img is not None:
            self.__img.set_rotation(angle)
            self.__img_angle = self.__img.angle

    def img_set_scale(self, scale: float) -> None:
        if self.__img is not None:
            self.__img.set_scale(scale)
            self.__img_scale = self.__img.scale

    def img_scale_to_width(self, width: float) -> None:
        if self.__img is not None:
            self.__img.scale_to_width(width)
            self.__img_scale = self.__img.scale

    def img_scale_to_height(self, height: float) -> None:
        if self.__img is not None:
            self.__img.scale_to_height(height)
            self.__img_scale = self.__img.scale

    def img_scale_to_size(self, size: Tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.scale_to_size(size)
            self.__img_scale = self.__img.scale

    def img_set_min_width(self, width: float) -> None:
        if self.__img is not None:
            self.__img.set_min_width(width)
            self.__img_scale = self.__img.scale

    def img_set_max_width(self, width: float) -> None:
        if self.__img is not None:
            self.__img.set_max_width(width)
            self.__img_scale = self.__img.scale

    def img_set_min_height(self, height: float) -> None:
        if self.__img is not None:
            self.__img.set_min_height(height)
            self.__img_scale = self.__img.scale

    def img_set_max_height(self, height: float) -> None:
        if self.__img is not None:
            self.__img.set_max_height(height)
            self.__img_scale = self.__img.scale

    def img_set_min_size(self, size: Tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.set_min_size(size)
            self.__img_scale = self.__img.scale

    def img_set_max_size(self, size: Tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.set_max_size(size)
            self.__img_scale = self.__img.scale

    def _render(self) -> Surface:
        text: Surface = super()._render()
        if self.__img is None:
            return text
        text_width, text_height = text.get_size()
        img_width, img_height = self.__img.get_size()
        if img_width == 0 or img_height == 0:
            return text
        if text_width == 0 or text_height == 0:
            return self.__img.to_surface()

        text_rect: Rect = text.get_rect()
        offset: float = self.__distance
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

        self.__img.draw_onto(render)
        render.blit(text, text_rect)

        return render

    @property
    def img(self) -> Optional[Surface]:
        if self.__img is None:
            return None
        return self.__img.get()

    @img.setter
    def img(self, surface: Optional[Surface]) -> None:
        if surface is None:
            if self.__img is None:
                return
            self.__img = None
            self._need_update()
            return
        if self.__img is None:
            self.__img = _BoundImage(self, surface)
            self.__img.set_scale(self.__img_scale)
            self.__img.set_rotation(self.__img_angle)
        else:
            self.__img.set(surface)
        self._need_update()

    @property
    def compound(self) -> str:
        return str(self.__compound.value)

    @compound.setter
    def compound(self, compound: str) -> None:
        compound = TextImage.Compound(compound)
        if compound != self.__compound:
            self.__compound = compound
            self._need_update()

    @property
    def distance(self) -> float:
        return self.__distance

    @distance.setter
    def distance(self, distance: float) -> None:
        if float(distance) != self.__distance:
            self.__distance = distance
            self._need_update()


class _BoundImage(Image):
    def __init__(self, text: TextImage, image: Surface) -> None:
        super().__init__(image)
        self.__text: TextImage = text

    def _apply_rotation_scale(self) -> None:
        super()._apply_rotation_scale()
        self.__text._need_update()

    def set(self, image: Surface) -> None:
        super().set(image)
        self.__text._need_update()
