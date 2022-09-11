# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Progress bar module"""

from __future__ import annotations

__all__ = ["ProgressBar"]


from dataclasses import dataclass
from enum import auto, unique
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Mapping, Sequence, TypeAlias

from typing_extensions import assert_never

from ..system.configuration import Configuration, ConfigurationTemplate, OptionAttribute, initializer
from ..system.enum import AutoLowerNameEnum
from ..system.theme import ThemedObjectMeta, ThemeType
from ..system.validation import valid_float, valid_integer
from .color import BLACK, GRAY, TRANSPARENT, WHITE, Color
from .shape import RectangleShape
from .text import Text

if TYPE_CHECKING:
    from .font import Font
    from .renderer import AbstractRenderer

    _TupleFont: TypeAlias = tuple[str | None, int]
    _TextFont: TypeAlias = Font | _TupleFont


_NO_DEFAULT: Any = object()


class ProgressBar(RectangleShape, metaclass=ThemedObjectMeta):
    __theme_ignore__: ClassVar[Sequence[str]] = (
        "from_",
        "to",
        "default",
        "orient",
    )

    @unique
    class Side(AutoLowerNameEnum):
        TOP = auto()
        BOTTOM = auto()
        LEFT = auto()
        RIGHT = auto()
        INSIDE = auto()

    @unique
    class Orient(AutoLowerNameEnum):
        HORIZONTAL = auto()
        VERTICAL = auto()

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "value",
        "percent",
        "scale_color",
        "orient",
        "cursor_color",
        "cursor_thickness",
        parent=RectangleShape.config,
    )

    value: OptionAttribute[float] = OptionAttribute()
    percent: OptionAttribute[float] = OptionAttribute()
    scale_color: OptionAttribute[Color] = OptionAttribute()
    orient: OptionAttribute[str] = OptionAttribute()
    cursor_color: OptionAttribute[Color] = OptionAttribute()
    cursor_thickness: OptionAttribute[int] = OptionAttribute()

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
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        self.__scale_rect: RectangleShape = RectangleShape(
            0,
            height,
            color=scale_color,
        )
        self.__outline_rect: RectangleShape = RectangleShape(
            width,
            height,
            color=TRANSPARENT,
        )
        super().__init__(
            width,
            height,
            color,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
            **kwargs,
        )
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

        self.__text_label = _ProgressTextLabel(Text(), None)
        self.__text_value = _ProgressTextValue(Text(), None, 0, None)

        self.hide_label()
        self.hide_value()

    def draw_onto(self, target: AbstractRenderer) -> None:
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect

        outline_rect.center = self.center
        if self.orient == ProgressBar.Orient.HORIZONTAL:
            scale_rect.midleft = self.midleft
        else:
            scale_rect.midtop = self.midtop

        super().draw_onto(target)
        scale_rect.draw_onto(target)

        if (cursor_thickness := self.cursor_thickness) > 0:
            cursor_start: tuple[float, float]
            cursor_end: tuple[float, float]
            outline: int = self.outline
            if self.orient == ProgressBar.Orient.HORIZONTAL:
                cursor_start, cursor_end = scale_rect.topright, scale_rect.bottomright
                cursor_end = cursor_end[0], cursor_end[1] - (outline / 2)
            else:
                cursor_start, cursor_end = scale_rect.bottomleft, scale_rect.bottomright
                cursor_end = cursor_end[0] - (outline / 2), cursor_end[1]
            target.draw_line(self.cursor_color, cursor_start, cursor_end, width=cursor_thickness)

        outline_rect.draw_onto(target)

        offset = 10
        match self.__text_value:
            case _ProgressTextValue(
                text=text,
                type="value" | "percent" as text_type,
                round_n=int(round_n),
                side=ProgressBar.Side() as side,
            ) if text.is_shown():
                if round_n > 0:
                    message_fmt = "{:." + str(round_n) + "f}"
                else:
                    message_fmt = "{:d}"
                match text_type:
                    case "value":
                        value = self.value
                        text.message = message_fmt.format(value if round_n > 0 else round(value))
                    case "percent":
                        value = self.percent * 100
                        text.message = f"{message_fmt.format(value if round_n > 0 else round(value))}%"
                    case _:
                        assert_never(text_type)

                self.__place_text(text, side, offset=offset)
                text.draw_onto(target)

        match self.__text_label:
            case _ProgressTextLabel(text=text, side=ProgressBar.Side() as side) if text.is_shown():
                self.__place_text(text, side, offset=offset)
                text.draw_onto(target)

    def __place_text(self, text: Text, side: Side, *, offset: int = 0) -> None:
        match side:
            case ProgressBar.Side.LEFT:
                text.midright = (self.left - offset, self.centery)
            case ProgressBar.Side.RIGHT:
                text.midleft = (self.right + offset, self.centery)
            case ProgressBar.Side.TOP:
                text.midbottom = (self.centerx, self.top - offset)
            case ProgressBar.Side.BOTTOM:
                text.midtop = (self.centerx, self.bottom + offset)
            case ProgressBar.Side.INSIDE:
                text.center = self.center
            case _:
                assert_never(side)

    def set_bounds(self, from_: float, to: float) -> None:
        from_ = float(from_)
        to = float(to)
        if to <= from_:
            raise ValueError("end value 'to' must be strictly greather than 'from'")
        self.__start = from_
        self.__end = to
        self.config.reset("value")

    def show_value(self, side: str, round_n: int = 0, *, font: _TextFont | None = _NO_DEFAULT, **kwargs: Any) -> None:
        self.config_value_text(font=font, **kwargs)
        self.__text_value.side = ProgressBar.Side(side)
        self.__text_value.round_n = int(round_n)
        self.__text_value.type = "value"
        self.__text_value.text.show()

    def hide_value(self) -> None:
        self.__text_value.text.hide()
        self.__text_value.side = None
        self.__text_value.round_n = 0
        self.__text_value.type = None

    def show_percent(self, side: str, round_n: int = 0, *, font: _TextFont | None = _NO_DEFAULT, **kwargs: Any) -> None:
        self.show_value(side, round_n, font=font, **kwargs)
        self.__text_value.type = "percent"

    def hide_percent(self) -> None:
        self.hide_value()

    def config_value_text(self, *, font: _TextFont | None = _NO_DEFAULT, **kwargs: Any) -> None:
        if font is not _NO_DEFAULT:
            self.__text_value.text.set_font(font)
        self.text_value.update(**kwargs)

    def show_label(self, label: str, side: str, *, font: _TextFont | None = _NO_DEFAULT, **kwargs: Any) -> None:
        self.config_label_text(message=label, font=font, **kwargs)
        self.__text_label.side = ProgressBar.Side(side)
        self.__text_label.text.show()

    def hide_label(self) -> None:
        self.__text_label.text.hide()
        self.__text_label.side = None

    def config_label_text(self, message: str = _NO_DEFAULT, *, font: _TextFont | None = _NO_DEFAULT, **kwargs: Any) -> None:
        if message is not _NO_DEFAULT:
            kwargs["message"] = message
        if font is not _NO_DEFAULT:
            self.__text_label.text.set_font(font)
        self.text_label.update(**kwargs)

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        super()._apply_only_scale()
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect
        outline_rect.scale = scale_rect.scale = self.scale

    def _freeze_state(self) -> dict[str, Any] | None:
        return None

    def _set_frozen_state(self, angle: float, scale: tuple[float, float], state: Mapping[str, Any] | None) -> bool:
        return super()._set_frozen_state(angle, scale, state)

    config.add_enum_converter("orient", Orient, return_value_on_get=True)

    @config.add_value_converter_on_set("value")
    def __valid_value(self, value: Any) -> float:
        return valid_float(value=value, min_value=self.__start, max_value=self.__end)

    config.add_value_converter_on_set_static("percent", valid_float(min_value=0, max_value=1))

    config.add_value_validator_static("cursor_color", Color)
    config.add_value_converter_on_set_static("cursor_thickness", valid_integer(min_value=0))

    config.getter("scale_color", lambda self: self.__scale_rect.config.get("color"), use_override=False)
    config.setter("scale_color", lambda self, color: self.__scale_rect.config.set("color", color), use_override=False)

    @config.on_update_value("value")
    def __update_percent(self, value: float) -> None:
        start: float = self.__start
        end: float = self.__end
        percent = (value - start) / (end - start) if end > start else 0
        self.config.only_set("percent", percent)

    @config.on_update_value("percent")
    def __update_value(self, percent: float) -> None:
        start: float = self.__start
        end: float = self.__end
        value = start + (percent * (end - start)) if end > start else 0
        self.config.only_set("value", value)

    config.remove_parent_ownership("outline")
    config.remove_parent_ownership("outline_color")

    @config.getter_with_key("outline")
    @config.getter_with_key("outline_color")
    def __outline_getter(self, option: str) -> Any:
        return self.__outline_rect.config.get(option)

    @config.setter_with_key("outline")
    @config.setter_with_key("outline_color")
    def __outline_setter(self, option: str, value: Any) -> None:
        self.__outline_rect.config.set(option, value)

    @config.on_update_value_with_key("border_radius")
    @config.on_update_value_with_key("border_top_left_radius")
    @config.on_update_value_with_key("border_top_right_radius")
    @config.on_update_value_with_key("border_bottom_left_radius")
    @config.on_update_value_with_key("border_bottom_right_radius")
    def __update_all_shapes(self, option: str, value: Any) -> None:
        self.__scale_rect.config.set(option, value)
        self.__outline_rect.config.set(option, value)

    @config.on_update("value")
    @config.on_update("percent")
    @config.on_update("orient")
    @config.on_update("local_width")
    @config.on_update("local_height")
    def __update_scale(self) -> None:
        width, height = self.local_size
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect
        percent: float = self.percent
        if self.orient == ProgressBar.Orient.HORIZONTAL:
            scale_rect.config.update(local_width=width * percent, local_height=height)
        else:
            scale_rect.config.update(local_width=width, local_height=height * percent)
        outline_rect.config.update(local_width=width, local_height=height)

    @property
    def from_value(self) -> float:
        return self.__start

    @property
    def to_value(self) -> float:
        return self.__end


@dataclass
class _ProgressTextLabel:
    text: Text
    side: ProgressBar.Side | None


@dataclass
class _ProgressTextValue:
    text: Text
    side: ProgressBar.Side | None
    round_n: int
    type: Literal["value", "percent"] | None
