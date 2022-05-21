# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Text module"""

__all__ = ["Text", "TextImage", "TextMeta"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os.path
from contextlib import suppress
from enum import auto, unique
from operator import truth
from textwrap import wrap as textwrap
from typing import Any, Final, Mapping, TypeAlias
from weakref import proxy as weakproxy

from pygame.transform import rotate as _surface_rotate, rotozoom as _surface_rotozoom

from ..system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ..system.enum import AutoLowerNameEnum
from ..system.validation import valid_float, valid_integer
from .color import BLACK, Color
from .drawable import TDrawable, TDrawableMeta
from .font import Font, SysFont
from .image import Image
from .rect import Rect
from .renderer import AbstractRenderer, SurfaceRenderer
from .surface import Surface, create_surface
from .theme import ThemedObjectMeta, ThemeType

_TupleFont: TypeAlias = tuple[str | None, int]
_TextFont: TypeAlias = Font | _TupleFont


class TextMeta(TDrawableMeta, ThemedObjectMeta):
    pass


class Text(TDrawable, metaclass=TextMeta):
    @unique
    class Justify(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        CENTER = auto()

    config: ConfigurationTemplate = ConfigurationTemplate(
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

    message: OptionAttribute[str] = OptionAttribute()
    font: OptionAttribute[Font] = OptionAttribute()
    color: OptionAttribute[Color] = OptionAttribute()
    wrap: OptionAttribute[int] = OptionAttribute()
    justify: OptionAttribute[str] = OptionAttribute()
    shadow_x: OptionAttribute[float] = OptionAttribute()
    shadow_y: OptionAttribute[float] = OptionAttribute()
    shadow: OptionAttribute[tuple[float, float]] = OptionAttribute()
    shadow_color: OptionAttribute[Color] = OptionAttribute()

    @initializer
    def __init__(
        self,
        message: str = "",
        *,
        font: _TextFont | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        color: Color = BLACK,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        theme: ThemeType | None = None,
    ) -> None:
        super().__init__()
        self.__custom_font: dict[int, Font] = dict()
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

    def draw_onto(self, target: AbstractRenderer) -> None:
        image: Surface = self.__image
        topleft: tuple[float, float] = self.topleft
        target.draw_surface(image, topleft)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def get(self, wrapped: bool = True) -> str:
        message: str = self.message
        if not wrapped:
            return message
        return "\n".join(textwrap(message, width=wrap)) if (wrap := self.wrap) > 0 else message

    def clear(self) -> None:
        self.message = str()

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
        font: str = getattr(Text, "__default_font__", Font.get_default_font())
        return font

    @staticmethod
    def set_default_font(font: str | None) -> None:
        if font is None:
            with suppress(AttributeError):
                delattr(Text, "__default_font__")
        else:
            setattr(Text, "__default_font__", str(font))

    def set_font(
        self,
        font: _TextFont | None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
    ) -> None:
        self.config.set(
            "font",
            Text.create_font(font, bold=bold, italic=italic, underline=underline),
        )

    def set_custom_line_font(
        self,
        index: int,
        font: _TextFont | None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
    ) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font[index] = Text.create_font(font, bold=bold, italic=italic, underline=underline)
        self.config.update_all_options()

    def remove_custom_line_font(self, index: int) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font.pop(index, None)
        self.config.update_all_options()

    def _apply_both_rotation_and_scale(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, self.angle, self.scale)

    def _apply_only_scale(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, 0, self.scale)

    def _apply_only_rotation(self) -> None:
        self.__image = _surface_rotate(self.__default_image, self.angle)

    def _freeze_state(self) -> Mapping[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        else:
            state = dict(state)
        state["image"] = self.__image
        return state

    def _set_frozen_state(self, angle: float, scale: float, state: Mapping[str, Any] | None) -> bool:
        res = super()._set_frozen_state(angle, scale, state)
        if state is None:
            return res
        self.__image = state["image"]
        return True

    __TEXT_JUSTIFY_DICT: Final[dict[Justify, str]] = {
        Justify.LEFT: "left",
        Justify.RIGHT: "right",
        Justify.CENTER: "centerx",
    }

    @staticmethod
    def static_render_text(
        text: str,
        color: Color,
        font: Font,
        *,
        justify: Justify = Justify.CENTER,
        custom_font: Mapping[int, Font] | None = None,
    ) -> Surface:
        if not text:
            return create_surface((0, 0))
        render_lines: list[Surface] = list()
        render_width: float = 0
        render_height: float = 0
        default_font: Font = font
        for index, line in enumerate(text.splitlines()):
            font = custom_font.get(index, default_font) if custom_font is not None else default_font
            render = font.render(line, True, color)
            render_width = max(render_width, render.get_width())
            render_height += render.get_height()
            render_lines.append(render)
        if not render_lines:
            return create_surface((0, 0))
        if len(render_lines) == 1:
            return render_lines[0]
        text_surface: Surface = create_surface((render_width, render_height))
        text_rect: Rect = text_surface.get_rect()
        top: int = 0
        justify_pos: str = Text.__TEXT_JUSTIFY_DICT[justify]
        params: dict[str, int] = {justify_pos: getattr(text_rect, justify_pos)}
        for render in render_lines:
            text_surface.blit(render, render.get_rect(**params, top=top))
            top += render.get_height()
        return text_surface

    def _render(self) -> Surface:
        message: str = self.get(wrapped=True)
        render_text = self.static_render_text
        text: Surface = render_text(message, self.color, self.font, justify=self.__justify, custom_font=self.__custom_font)
        shadow_x, shadow_y = self.shadow
        shadow_x = int(shadow_x)
        shadow_y = int(shadow_y)
        if shadow_x == 0 and shadow_y == 0:
            return text
        shadow_text: Surface = render_text(
            message, self.shadow_color, self.font, justify=self.__justify, custom_font=self.__custom_font
        )
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

    config.add_enum_converter("justify", Justify, return_value_on_get=True)

    config.add_value_validator_static("message", str)
    config.add_value_converter_static("font", create_font)
    config.add_value_converter_static("wrap", valid_integer(min_value=0))
    config.add_value_validator_static("color", Color)
    config.add_value_converter_static("shadow_x", float)
    config.add_value_converter_static("shadow_y", float)
    config.add_value_converter_static("shadow", tuple)
    config.add_value_validator_static("shadow_color", Color)

    config.set_autocopy("font", copy_on_get=False, copy_on_set=False)

    @config.add_main_update
    def __update_surface(self) -> None:
        if self.config.has_initialization_context():
            self.__default_image = self._render()
            self.apply_rotation_scale()
        else:
            center: tuple[float, float] = self.center
            self.__default_image = self._render()
            self.apply_rotation_scale()
            self.center = center

    config.getter("shadow", lambda self: (self.shadow_x, self.shadow_y))
    config.setter("shadow", lambda self, pos: self.config(shadow_x=pos[0], shadow_y=pos[1]))


class TextImage(Text):
    @unique
    class Compound(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        TOP = auto()
        BOTTOM = auto()
        CENTER = auto()

    config = ConfigurationTemplate("img", "compound", "distance", parent=Text.config)

    img: OptionAttribute[Surface | None] = OptionAttribute()
    compound: OptionAttribute[str] = OptionAttribute()
    distance: OptionAttribute[float] = OptionAttribute()

    @initializer
    def __init__(
        self,
        message: str = "",
        *,
        img: Surface | None = None,
        compound: str = "left",
        distance: float = 5,
        font: _TextFont | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        color: Color = BLACK,
        wrap: int = 0,
        justify: str = "left",
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        theme: ThemeType | None = None,
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
        self.__img: Image | None = None
        self.__compound: TextImage.Compound
        self.__img_angle: float = 0
        self.__img_scale: float = 1
        self.distance = distance
        self.compound = compound
        self.img = img

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

    def img_scale_to_size(self, size: tuple[float, float]) -> None:
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

    def img_set_min_size(self, size: tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.set_min_size(size)
            self.__img_scale = self.__img.scale

    def img_set_max_size(self, size: tuple[float, float]) -> None:
        if self.__img is not None:
            self.__img.set_max_size(size)
            self.__img_scale = self.__img.scale

    def _render(self) -> Surface:
        text: Surface = super()._render()
        img: Image | None = self.__img
        if img is None:
            return text
        text_width, text_height = text.get_size()
        img_width, img_height = img.get_size()
        if img_width == 0 or img_height == 0:
            return text
        if text_width == 0 or text_height == 0:
            return img.get(apply_rotation_scale=True)

        text_rect: Rect = text.get_rect()
        offset: float = self.distance
        render_width: float
        render_height: float
        compound: TextImage.Compound = self.__compound
        match compound:
            case TextImage.Compound.LEFT | TextImage.Compound.RIGHT:
                render_width = text_width + img_width + offset
                render_height = max(text_height, img_height)
            case TextImage.Compound.TOP | TextImage.Compound.BOTTOM:
                render_width = max(text_width, img_width)
                render_height = text_height + img_height + offset
            case TextImage.Compound.CENTER:
                render_width = max(text_width, img_width)
                render_height = max(text_height, img_height)

        render: Surface = create_surface((render_width, render_height))
        render_rect: Rect = render.get_rect()

        match compound:
            case TextImage.Compound.LEFT:
                text_rect.midleft = render_rect.midleft
                img.midright = render_rect.midright
            case TextImage.Compound.RIGHT:
                text_rect.midright = render_rect.midright
                img.midleft = render_rect.midleft
            case TextImage.Compound.TOP:
                text_rect.midtop = render_rect.midtop
                img.midbottom = render_rect.midbottom
            case TextImage.Compound.BOTTOM:
                text_rect.midbottom = render_rect.midbottom
                img.midtop = render_rect.midtop
            case TextImage.Compound.CENTER:
                img.center = text_rect.center = render_rect.center

        img.draw_onto(SurfaceRenderer(render))
        render.blit(text, text_rect)

        return render

    config.set_autocopy("img", copy_on_get=False, copy_on_set=False)

    config.add_enum_converter("compound", Compound, return_value_on_get=True)

    config.add_value_validator_static("img", Surface, accept_none=True)
    config.add_value_converter_static("distance", valid_float(min_value=0))

    @config.getter("img")
    def __get_img_surface(self) -> Surface | None:
        img: Image | None = self.__img
        if img is None:
            return None
        return img.get()

    @config.setter("img")
    def __update_img(self, surface: Surface | None) -> None:
        if surface is None:
            self.__img = None
            return
        img: Image | None = self.__img
        if img is None:
            self.__img = img = _BoundImage(self, surface)
            img.set_scale(self.__img_scale)
            img.set_rotation(self.__img_angle)
        else:
            img.set(surface)


class _BoundImage(Image):
    def __init__(self, text: TextImage, image: Surface) -> None:
        super().__init__(image)
        self.__text: TextImage = weakproxy(text)

    def _apply_both_rotation_and_scale(self) -> None:
        super()._apply_both_rotation_and_scale()
        self.__text.config.update_all_options()

    def _apply_only_rotation(self) -> None:
        super()._apply_only_rotation()
        self.__text.config.update_all_options()

    def _apply_only_scale(self) -> None:
        super()._apply_only_scale()
        self.__text.config.update_all_options()

    def set(self, image: Surface | None, copy: bool = True) -> None:
        super().set(image, copy=copy)  # type: ignore[arg-type]
        self.__text.config.update_all_options()
