# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Text module"""

from __future__ import annotations

__all__ = ["Text", "TextImage"]


import os.path
from collections import deque
from contextlib import suppress
from copy import copy
from enum import auto, unique
from textwrap import wrap as textwrap
from typing import Any, ClassVar, Final, Mapping, TypeAlias, overload
from weakref import proxy as weakproxy

from pygame.transform import rotozoom as _surface_rotozoom
from typing_extensions import assert_never

from ..system.configuration import Configuration, ConfigurationTemplate, OptionAttribute, initializer
from ..system.enum import AutoLowerNameEnum
from ..system.theme import ThemedObjectMeta, ThemeType
from ..system.utils.typing import reflect_method_signature
from ..system.validation import valid_float, valid_integer
from ._transform import rotozoom2 as _surface_rotozoom2, scale_by as _surface_scale_by
from .color import BLACK, Color
from .drawable import Drawable
from .font import Font, SysFont, get_default_font
from .image import Image
from .rect import Rect
from .renderer import AbstractRenderer
from .surface import Surface, SurfaceRenderer, create_surface
from .transformable import Transformable

_TupleFont: TypeAlias = tuple[str | None, int]
_TextFont: TypeAlias = Font | _TupleFont


class Text(Drawable, Transformable, metaclass=ThemedObjectMeta):
    @unique
    class Justify(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        CENTER = auto()

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "message",
        "color",
        "wrap",
        "justify",
        "shadow_x",
        "shadow_y",
        "shadow",
        "shadow_color",
        "line_spacing",
    )

    message: OptionAttribute[str] = OptionAttribute()
    color: OptionAttribute[Color] = OptionAttribute()
    wrap: OptionAttribute[int] = OptionAttribute()
    justify: OptionAttribute[str] = OptionAttribute()
    shadow_x: OptionAttribute[float] = OptionAttribute()
    shadow_y: OptionAttribute[float] = OptionAttribute()
    shadow: OptionAttribute[tuple[float, float]] = OptionAttribute()
    shadow_color: OptionAttribute[Color] = OptionAttribute()
    line_spacing: OptionAttribute[float] = OptionAttribute()

    @config.section_property
    def font(self) -> Configuration[Font]:
        return self.__font.config

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
        line_spacing: float = 0,
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.__custom_font: dict[int, Font] = dict()
        self.__default_image: Surface = create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__font: Font
        self.__justify: Text.Justify
        self.__color: Color
        self.__shadow_x: float
        self.__shadow_y: float
        self.__shadow_color: Color
        self.set_font(font, bold=bold, italic=italic, underline=underline)
        self.wrap = wrap
        self.message = message
        self.color = color
        self.justify = justify
        self.line_spacing = line_spacing
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
        obj.antialiased = True
        return obj

    @classmethod
    def get_default_font(cls) -> str:
        try:
            font: str = getattr(cls, "__default_font__")
        except AttributeError:
            font = get_default_font()
        return font

    @classmethod
    def set_default_font(cls, font: str | None) -> None:
        if font is None:
            with suppress(AttributeError):
                delattr(cls, "__default_font__")
        else:
            setattr(cls, "__default_font__", str(font))

    def set_font(
        self,
        font: _TextFont | None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
    ) -> None:
        self.__font = self.create_font(font, bold=bold, italic=italic, underline=underline)
        self.config.update_section("font")

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
        self.__custom_font[index] = self.create_font(font, bold=bold, italic=italic, underline=underline)
        self.config.update_object()

    def remove_custom_line_font(self, index: int) -> None:
        if index < 0:
            raise ValueError(f"Negative index: {index}")
        self.__custom_font.pop(index, None)
        self.config.update_object()

    def _apply_both_rotation_and_scale(self) -> None:
        self.__image = _surface_rotozoom2(self.__default_image, self.angle, self.scale)

    def _apply_only_rotation(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, self.angle, 1)

    def _apply_only_scale(self) -> None:
        self.__image = _surface_scale_by(self.__default_image, self.scale)

    def _freeze_state(self) -> dict[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        state["image"] = self.__image
        return state

    def _set_frozen_state(self, angle: float, scale: tuple[float, float], state: Mapping[str, Any] | None) -> bool:
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

    def _render(self) -> Surface:
        text: str = self.get(wrapped=True)
        default_font: Font = self.__font
        custom_font: dict[int, Font] = self.__custom_font
        line_spacing: int = int(self.line_spacing)
        justify_pos: str = Text.__TEXT_JUSTIFY_DICT[self.__justify]
        fgcolor: Color = self.__color
        shadow_x: int = int(self.__shadow_x)
        shadow_y: int = int(self.__shadow_y)
        shadow_width_offset: int = abs(shadow_x)
        shadow_height_offset: int = abs(shadow_y)
        text_x: float = 0
        text_y: float = 0
        if shadow_x < 0:
            text_x = -shadow_x
            shadow_x = 0
        if shadow_y < 0:
            text_y = -shadow_y
            shadow_y = 0

        render_queue: deque[tuple[str, Font, Rect]] = deque()
        render_width: float = 0
        render_height: float = 0

        # 1- Retrieve all line rects
        line_top: int = 0
        for index, line in enumerate(text.splitlines()):
            font = custom_font.get(index, default_font) if custom_font is not None else default_font
            line_rect = font.get_rect(line)

            line_rect.top = line_top
            line_top = line_rect.bottom + line_spacing

            render_width = max(render_width, line_rect.width)
            render_height += line_rect.height + line_spacing

            render_queue.append((line, font, line_rect))

        # 2 - Compute the target surface
        if not render_queue:  # No message to render
            return create_surface((0, 0))
        if len(render_queue) == 1 and not shadow_width_offset and not shadow_height_offset:
            # Optimization: Single line without shadow
            line, font, _ = render_queue[0]
            return font.render(line, fgcolor)[0]
        render_rect = Rect(0, 0, render_width, render_height)
        final_render_surface = create_surface((render_width + shadow_width_offset, render_height + shadow_height_offset))

        # 3- Apply 'justify' attribute to rects according to *default* render (w/o shadow)
        if len(render_queue) > 1 and justify_pos != "left":  # Ignore for 'left', it will always be 0
            justify_pos_value: int = getattr(render_rect, justify_pos)
            for line_rect in map(lambda i: i[2], render_queue):
                setattr(line_rect, justify_pos, justify_pos_value)

        # 4-a Render shadow if set
        if shadow_width_offset or shadow_height_offset:
            shadow_color: Color = self.__shadow_color
            for line, font, line_rect in render_queue:
                line_rect.move_ip(shadow_x, shadow_y)
                font.render_to(final_render_surface, line_rect, line, shadow_color)
                line_rect.move_ip(-shadow_x, -shadow_y)

        # 4-b Render foreground
        for line, font, line_rect in render_queue:
            line_rect.move_ip(text_x, text_y)
            font.render_to(final_render_surface, line_rect, line, fgcolor)

        return final_render_surface

    config.add_enum_converter("justify", Justify, return_value_on_get=True)

    config.add_value_validator_static("message", str)
    config.add_value_converter_on_set_static("wrap", valid_integer(min_value=0))
    config.add_value_validator_static("color", Color)
    config.add_value_converter_on_set_static("shadow_x", float)
    config.add_value_converter_on_set_static("shadow_y", float)
    config.add_value_converter_on_set_static("shadow", tuple)
    config.add_value_validator_static("shadow_color", Color)
    config.add_value_converter_on_set_static("line_spacing", float)

    @config.add_main_update
    def __update_surface(self) -> None:
        if self.config.has_initialization_context():
            self.__default_image = self._render()
            self.update_transform()
        else:
            center: tuple[float, float] = self.center
            self.__default_image = self._render()
            self.update_transform()
            self.center = center

    config.getter("shadow", lambda self: (self.shadow_x, self.shadow_y), use_override=False)
    config.setter("shadow", lambda self, pos: self.config.update(shadow_x=pos[0], shadow_y=pos[1]), use_override=False)


class TextImage(Text):
    @unique
    class Compound(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        TOP = auto()
        BOTTOM = auto()
        CENTER = auto()

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate("img", "compound", "distance", parent=Text.config)

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
        line_spacing: float = 0,
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
            line_spacing=line_spacing,
            shadow_x=shadow_x,
            shadow_y=shadow_y,
            shadow_color=shadow_color,
            theme=theme,
        )
        self.__img: Image | None = None
        self.__compound: TextImage.Compound
        self.__img_angle: float = 0
        self.__img_scale: tuple[float, float] = (1, 1)
        self.distance = distance
        self.compound = compound
        self.img = img

    def get_img_angle(self) -> float:
        return self.__img_angle

    def get_img_scale(self) -> tuple[float, float]:
        return self.__img_scale

    @reflect_method_signature(Image.rotate)
    def img_rotate(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.rotate(*args, **kwargs)
            self.__img_angle = self.__img.angle

    @reflect_method_signature(Image.set_rotation)
    def img_set_rotation(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_rotation(*args, **kwargs)
            self.__img_angle = self.__img.angle

    @overload
    def img_set_scale(self, *, scale_x: float) -> None:
        ...

    @overload
    def img_set_scale(self, *, scale_y: float) -> None:
        ...

    @overload
    def img_set_scale(self, *, scale_x: float, scale_y: float) -> None:
        ...

    @overload
    def img_set_scale(self, __scale: float, /) -> None:
        ...

    @overload
    def img_set_scale(self, __scale: tuple[float, float], /) -> None:
        ...

    # @reflect_method_signature() doesn't work with overloads
    def img_set_scale(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_scale(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.scale_to_width)
    def img_scale_to_width(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.scale_to_width(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.scale_to_height)
    def img_scale_to_height(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.scale_to_height(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.scale_to_size)
    def img_scale_to_size(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.scale_to_size(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.set_min_width)
    def img_set_min_width(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_min_width(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.set_max_width)
    def img_set_max_width(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_max_width(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.set_min_height)
    def img_set_min_height(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_min_height(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.set_max_height)
    def img_set_max_height(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_max_height(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.set_min_size)
    def img_set_min_size(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_min_size(*args, **kwargs)
            self.__img_scale = self.__img.scale

    @reflect_method_signature(Image.set_max_size)
    def img_set_max_size(self, *args: Any, **kwargs: Any) -> None:
        if self.__img is not None:
            self.__img.set_max_size(*args, **kwargs)
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
            case _:
                assert_never(compound)

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
            case _:
                assert_never(compound)

        img.draw_onto(SurfaceRenderer(render))
        render.blit(text, text_rect)

        return render

    config.add_enum_converter("compound", Compound, return_value_on_get=True)

    config.add_value_validator_static("img", Surface, accept_none=True)
    config.add_value_converter_on_set_static("distance", valid_float(min_value=0))

    @config.getter("img")
    def get_img_surface(self, *, apply_rotation_scale: bool = False) -> Surface | None:
        img: Image | None = self.__img
        if img is None:
            return None
        return img.get(apply_rotation_scale=apply_rotation_scale)

    @config.setter("img")
    def set_img_surface(self, surface: Surface | None) -> None:
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
        self.__text.config.update_object()

    def _apply_only_rotation(self) -> None:
        super()._apply_only_rotation()
        self.__text.config.update_object()

    def _apply_only_scale(self) -> None:
        super()._apply_only_scale()
        self.__text.config.update_object()

    def set(self, image: Surface | None, copy: bool = True) -> None:
        super().set(image, copy=copy)  # type: ignore[arg-type]
        self.__text.config.update_object()
