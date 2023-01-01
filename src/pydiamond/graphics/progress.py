# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Progress bar module"""

from __future__ import annotations

__all__ = ["ProgressBar", "ProgressBarOrient", "ProgressBarTextSide"]

from dataclasses import dataclass
from enum import auto, unique
from typing import TYPE_CHECKING, Any, ClassVar, Literal

from pygame.transform import rotozoom as _surface_rotozoom
from typing_extensions import assert_never

from ..math.rect import Rect
from ..system.configuration import Configuration, ConfigurationTemplate, OptionAttribute, initializer
from ..system.utils.enum import AutoLowerNameEnum
from ..system.validation import valid_float, valid_integer, valid_sequence
from ._transform import rotozoom2 as _surface_rotozoom2, scale_by as _surface_scale_by
from .color import BLACK, GRAY, TRANSPARENT, WHITE, Color
from .drawable import Drawable
from .shape import RectangleShape
from .surface import Surface, SurfaceRenderer
from .text import Text
from .transformable import Transformable

if TYPE_CHECKING:
    from .font import _TextFont
    from .renderer import AbstractRenderer


_NO_DEFAULT: Any = object()


@unique
class ProgressBarTextSide(AutoLowerNameEnum):
    TOP = auto()
    BOTTOM = auto()
    LEFT = auto()
    RIGHT = auto()
    INSIDE = auto()


@unique
class ProgressBarOrient(AutoLowerNameEnum):
    HORIZONTAL = auto()
    VERTICAL = auto()


class ProgressBar(Drawable, Transformable):

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "value",
        "percent",
        "scale_color",
        "orient",
        "cursor_color",
        "cursor_thickness",
        "label_offset",
        "value_display_offset",
    )

    value: OptionAttribute[float] = OptionAttribute()
    percent: OptionAttribute[float] = OptionAttribute()
    scale_color: OptionAttribute[Color] = OptionAttribute()
    orient: OptionAttribute[str] = OptionAttribute()
    cursor_color: OptionAttribute[Color] = OptionAttribute()
    cursor_thickness: OptionAttribute[int] = OptionAttribute()
    value_display_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()
    label_offset: OptionAttribute[tuple[float, float]] = OptionAttribute()

    @config.section_property(
        exclude_options={
            "border_radius",
            "border_top_left_radius",
            "border_top_right_radius",
            "border_bottom_left_radius",
            "border_bottom_right_radius",
        }
    )
    def shape(self) -> Configuration[RectangleShape]:
        return self.__shape.config

    @config.section_property(exclude_options={"message"})
    def text_value(self) -> Configuration[Text]:
        return self.__text_value.text.config

    @config.section_property
    def text_label(self) -> Configuration[Text]:
        return self.__text_label.text.config

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        *,
        from_: float = 0,
        to: float = 1,
        default: float | None = None,
        percent_default: float | None = None,
        orient: str = "horizontal",
        color: Color = WHITE,
        scale_color: Color = GRAY,
        cursor_color: Color = BLACK,
        cursor_thickness: int = 0,
        outline: int = 2,
        outline_color: Color = BLACK,
        value_display_offset: tuple[float, float] = (0, 0),
        label_offset: tuple[float, float] = (0, 0),
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.__shape: RectangleShape = RectangleShape(
            width,
            height,
            color,
            outline=outline,
            outline_color=outline_color,
        )
        self.scale_color = scale_color
        self.cursor_color = cursor_color
        self.cursor_thickness = cursor_thickness

        from_ = float(from_)
        to = float(to)
        if to <= from_:
            raise ValueError("end value 'to' must be greather than 'from'")
        self.__start: float = from_
        self.__end: float = to

        if default is not None and percent_default is not None:
            raise ValueError("Set either 'default' or 'percent_default'")

        if default is not None:
            self.value = default
        elif percent_default is not None:
            self.percent = percent_default
        else:
            self.value = from_

        self.orient = orient

        self.label_offset = label_offset
        self.value_display_offset = value_display_offset

        self.__text_label = _ProgressTextLabel(Text(), None)
        self.__text_value = _ProgressTextValue(Text(), None, 0, None)

        self.__default_image: Surface
        self.__image: Surface

        self.hide_label()
        self.hide_value()

    def draw_onto(self, target: AbstractRenderer) -> None:
        target.draw_surface(self.__image, self.topleft)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def set_bounds(self, from_: float, to: float) -> None:
        from_ = float(from_)
        to = float(to)
        if to <= from_:
            raise ValueError("end value 'to' must be strictly greather than 'from'")
        self.__start = from_
        self.__end = to
        self.config.reset("value")

    def show_value(
        self,
        side: str,
        round_n: int = 0,
        *,
        font: _TextFont | None = _NO_DEFAULT,
        offset: tuple[float, float] = _NO_DEFAULT,
        **kwargs: Any,
    ) -> None:
        with self.config.initialization():
            self.config_value_text(offset=offset, font=font, **kwargs)
            self.__text_value.side = ProgressBarTextSide(side)
            self.__text_value.round_n = int(round_n)
            self.__text_value.type = "value"

    def hide_value(self) -> None:
        self.__text_value.side = None
        self.__text_value.round_n = 0
        self.__text_value.type = None

    def show_percent(
        self,
        side: str,
        round_n: int = 0,
        *,
        offset: tuple[float, float] = _NO_DEFAULT,
        font: _TextFont | None = _NO_DEFAULT,
        **kwargs: Any,
    ) -> None:
        with self.config.initialization():
            self.config_value_text(offset=offset, font=font, **kwargs)
            self.__text_value.side = ProgressBarTextSide(side)
            self.__text_value.round_n = int(round_n)
            self.__text_value.type = "percent"

    def hide_percent(self) -> None:
        self.__text_value.side = None
        self.__text_value.round_n = 0
        self.__text_value.type = None
        self.config.update_object()

    def config_value_text(
        self,
        *,
        offset: tuple[float, float] = _NO_DEFAULT,
        font: _TextFont | None = _NO_DEFAULT,
        **kwargs: Any,
    ) -> None:
        with self.config.initialization():
            if font is not _NO_DEFAULT:
                self.__text_value.text.set_font(font)
            self.text_value.update(**kwargs)
            if offset is not _NO_DEFAULT:
                self.value_display_offset = offset

    def show_label(
        self,
        label: str,
        side: str,
        *,
        offset: tuple[float, float] = _NO_DEFAULT,
        font: _TextFont | None = _NO_DEFAULT,
        **kwargs: Any,
    ) -> None:
        with self.config.initialization():
            self.config_label_text(message=label, offset=offset, font=font, **kwargs)
            self.__text_label.side = ProgressBarTextSide(side)

    def hide_label(self) -> None:
        self.__text_label.side = None
        self.config.update_object()

    def config_label_text(
        self,
        message: str = _NO_DEFAULT,
        *,
        offset: tuple[float, float] = _NO_DEFAULT,
        font: _TextFont | None = _NO_DEFAULT,
        **kwargs: Any,
    ) -> None:
        with self.config.initialization():
            if message is not _NO_DEFAULT:
                kwargs["message"] = message
            if font is not _NO_DEFAULT:
                self.__text_label.text.set_font(font)
            self.text_label.update(**kwargs)
            if offset is not _NO_DEFAULT:
                self.label_offset = offset

    def _apply_both_rotation_and_scale(self) -> None:
        self.__image = _surface_rotozoom2(self.__default_image, self.angle, self.scale)

    def _apply_only_rotation(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, self.angle, 1)

    def _apply_only_scale(self) -> None:
        self.__image = _surface_scale_by(self.__default_image, self.scale)

    def _render(self) -> Surface:
        shape = self.__shape
        with shape.config.temporary_options(False, outline=0):
            shape_surface = shape._make(apply_rotation=False, apply_scale=False)

            width, height = shape.local_size
            percent: float = self.percent
            if self.orient == ProgressBarOrient.HORIZONTAL:
                width *= percent
            else:
                height *= percent

            with shape.config.temporary_options(False, color=self.scale_color, local_width=width, local_height=height):
                scale_shape_surface = shape._make(apply_rotation=False, apply_scale=False)
                shape_rect = shape_surface.get_rect()
                if self.orient == ProgressBarOrient.HORIZONTAL:
                    scale_rect = scale_shape_surface.get_rect(midleft=shape_rect.midleft)
                else:
                    scale_rect = scale_shape_surface.get_rect(midtop=shape_rect.midtop)
                shape_surface.blit(scale_shape_surface, scale_rect)

        with shape.config.temporary_options(False, color=TRANSPARENT):
            outline_shape_surface = shape._make(apply_rotation=False, apply_scale=False)

        shape_renderer = SurfaceRenderer.from_size(outline_shape_surface.get_size())
        shape_renderer.draw_surface(shape_surface, shape_surface.get_rect(center=outline_shape_surface.get_rect().center))
        shape_renderer.draw_surface(outline_shape_surface, (0, 0))

        if (cursor_thickness := self.cursor_thickness) > 0:
            cursor_start: tuple[float, float]
            cursor_end: tuple[float, float]
            outline: int = shape.outline
            if self.orient == ProgressBarOrient.HORIZONTAL:
                cursor_start, cursor_end = scale_rect.topright, scale_rect.bottomright
                cursor_end = cursor_end[0], cursor_end[1] - (outline / 2)
            else:
                cursor_start, cursor_end = scale_rect.bottomleft, scale_rect.bottomright
                cursor_end = cursor_end[0] - (outline / 2), cursor_end[1]
            shape_renderer.draw_line(self.cursor_color, cursor_start, cursor_end, width=cursor_thickness)

        shape_renderer.draw_surface(outline_shape_surface, (0, 0))
        text_value: Text | None = None
        text_label: Text | None = None
        whole_rect = shape_renderer.get_rect()
        match self.__text_value:
            case _ProgressTextValue(
                text=text_value,
                type="value" | "percent" as text_type,
                round_n=int(round_n),
                side=ProgressBarTextSide() as side,
            ):
                if round_n > 0:
                    message_fmt = "{:." + str(round_n) + "f}"
                else:
                    message_fmt = "{:d}"
                match text_type:
                    case "value":
                        value = self.value
                        text_value.message = message_fmt.format(value if round_n > 0 else round(value))
                    case "percent":
                        value = self.percent * 100
                        text_value.message = f"{message_fmt.format(value if round_n > 0 else round(value))}%"
                    case _:
                        assert_never(text_type)

                self.__place_text(text_value, side, self.value_display_offset, shape_renderer.get_rect())
                whole_rect.union_ip(text_value.get_rect())

        match self.__text_label:
            case _ProgressTextLabel(text=text_label, side=ProgressBarTextSide() as side):
                self.__place_text(text_label, side, self.label_offset, shape_renderer.get_rect())
                whole_rect.union_ip(text_label.get_rect())

        if text_label is None and text_value is None:
            return shape_renderer.get_target()

        whole_area = SurfaceRenderer.from_size(whole_rect.size)
        whole_area.draw_surface(shape_renderer.get_target(), (-whole_rect.x, -whole_rect.y))

        text_object: Text
        for text_object in filter(None, [text_label, text_value]):
            text_object.move(-whole_rect.x, -whole_rect.y)
            text_object.draw_onto(whole_area)

        return whole_area.get_target()

    @staticmethod
    def __place_text(text: Text, side: ProgressBarTextSide, offset: tuple[float, float], rect: Rect) -> None:
        dx, dy = offset
        del offset
        match side:
            case ProgressBarTextSide.LEFT:
                text.midright = (rect.left + dx, rect.centery + dy)
            case ProgressBarTextSide.RIGHT:
                text.midleft = (rect.right + dx, rect.centery + dy)
            case ProgressBarTextSide.TOP:
                text.midbottom = (rect.centerx + dx, rect.top + dy)
            case ProgressBarTextSide.BOTTOM:
                text.midtop = (rect.centerx + dx, rect.bottom + dy)
            case ProgressBarTextSide.INSIDE:
                text.center = (rect.centerx + dx, rect.centery + dy)
            case _:
                assert_never(side)

    @config.add_main_update(use_override=False)
    def __update_shape(self) -> None:
        if self.config.has_initialization_context():
            self.__default_image = self._render()
            self.update_transform()
        else:
            center: tuple[float, float] = self.center
            self.__default_image = self._render()
            self.update_transform()
            self.center = center

    del __update_shape

    config.add_enum_converter("orient", ProgressBarOrient, return_value_on_get=True)

    @config.add_value_converter_on_set("value", use_override=False)
    def __valid_value(self, value: Any) -> float:
        return valid_float(value=value, min_value=self.__start, max_value=self.__end)

    del __valid_value

    config.add_value_converter_on_set_static("percent", valid_float(min_value=0, max_value=1))

    config.add_value_validator_static("cursor_color", Color)
    config.add_value_converter_on_set_static("cursor_thickness", valid_integer(min_value=0))

    config.add_value_converter_on_set_static("value_display_offset", valid_sequence(length=2, validator=float))
    config.add_value_converter_on_set_static("label_offset", valid_sequence(length=2, validator=float))

    @config.on_update_value("value", use_override=False)
    def __update_percent(self, value: float) -> None:
        start: float = self.__start
        end: float = self.__end
        percent = (value - start) / (end - start) if end > start else 0
        self.config.only_set("percent", percent)

    @config.on_update_value("percent", use_override=False)
    def __update_value(self, percent: float) -> None:
        start: float = self.__start
        end: float = self.__end
        value = start + (percent * (end - start)) if end > start else 0
        self.config.only_set("value", value)

    del __update_value, __update_percent

    @property
    def from_value(self) -> float:
        return self.__start

    @property
    def to_value(self) -> float:
        return self.__end


@dataclass
class _ProgressTextLabel:
    text: Text
    side: ProgressBarTextSide | None


@dataclass
class _ProgressTextValue:
    text: Text
    side: ProgressBarTextSide | None
    round_n: int
    type: Literal["value", "percent"] | None
