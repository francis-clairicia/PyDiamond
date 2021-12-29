# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Progress bar module"""

from __future__ import annotations

__all__ = ["ProgressBar"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from enum import Enum, unique
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from ..system.configuration import Configuration, OptionAttribute, initializer
from ..system.utils import valid_float
from .color import BLACK, GRAY, TRANSPARENT, WHITE, Color
from .shape import RectangleShape
from .text import Text
from .theme import NoTheme, ThemeType

if TYPE_CHECKING:
    from .renderer import Renderer


class ProgressBar(RectangleShape):
    @unique
    class Side(str, Enum):
        TOP = "top"
        BOTTOM = "bottom"
        LEFT = "left"
        RIGHT = "right"
        INSIDE = "inside"

    @unique
    class Orient(str, Enum):
        HORIZONTAL = "horizontal"
        VERTICAL = "vertical"

    config = Configuration("value", "percent", "scale_color", "orient", parent=RectangleShape.config)

    value: OptionAttribute[float] = OptionAttribute()
    percent: OptionAttribute[float] = OptionAttribute()
    scale_color: OptionAttribute[Color] = OptionAttribute()
    orient: OptionAttribute[str] = OptionAttribute()

    @initializer
    def __init__(
        self,
        /,
        width: float,
        height: float,
        from_: float = 0,
        to: float = 1,
        default: Optional[float] = None,
        orient: str = "horizontal",
        *,
        color: Color = WHITE,
        scale_color: Color = GRAY,
        outline: int = 2,
        outline_color: Color = BLACK,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: Optional[ThemeType] = None,
    ) -> None:
        self.__scale_rect: RectangleShape = RectangleShape(
            0,
            height,
            color=scale_color,
            theme=NoTheme,
        )
        self.__outline_rect: RectangleShape = RectangleShape(
            width,
            height,
            color=TRANSPARENT,
            theme=NoTheme,
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
            theme=theme,
        )
        from_ = float(from_)
        to = float(to)
        if to <= from_:
            raise ValueError("end value 'to' must be greather than 'from'")
        self.__value: float = 0
        self.__percent: float = 0
        self.__start: float = from_
        self.__end: float = to

        if default is not None:
            self.value = default
        else:
            self.value = from_

        self.orient = orient

        self.__label_text = Text()
        self.__label_text_side = str()
        self.__value_text = Text()
        self.__value_text_side = str()
        self.__value_text_round_n = 0
        self.__value_text_type = str()

        self.hide_label()
        self.hide_value()

    def draw_onto(self, /, target: Renderer) -> None:
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect

        outline_rect.center = self.center
        outline: int = self.outline
        if self.orient == ProgressBar.Orient.HORIZONTAL:
            midleft: Tuple[float, float] = self.midleft
            scale_rect.midleft = (midleft[0] + outline / 2, midleft[1])
        else:
            midtop: Tuple[float, float] = self.midtop
            scale_rect.midtop = (midtop[0], midtop[1] + outline / 2)

        super().draw_onto(target)
        scale_rect.draw_onto(target)
        outline_rect.draw_onto(target)

        offset = 10
        movements: Dict[str, Dict[str, Union[float, Tuple[float, float]]]]
        if self.__value_text.is_shown() and self.__value_text_type in ["value", "percent"]:
            movements = {
                ProgressBar.Side.TOP.value: {"bottom": self.top - offset, "centerx": self.centerx},
                ProgressBar.Side.BOTTOM.value: {
                    "top": self.bottom + offset,
                    "centerx": self.centerx,
                },
                ProgressBar.Side.LEFT.value: {
                    "right": self.left - offset,
                    "centery": self.centery,
                },
                ProgressBar.Side.RIGHT.value: {
                    "left": self.right + offset,
                    "centery": self.centery,
                },
                ProgressBar.Side.INSIDE.value: {"center": self.center},
            }
            side = self.__value_text_side
            round_n = self.__value_text_round_n
            if side in movements:
                if self.__value_text_type == "value":
                    value = self.__value
                    self.__value_text.message = f"{round(value, round_n) if round_n > 0 else round(value)}"
                elif self.__value_text_type == "percent":
                    value = self.__percent * 100
                    self.__value_text.message = f"{round(value, round_n) if round_n > 0 else round(value)}%"
                self.__value_text.set_position(**movements[side])
                self.__value_text.draw_onto(target)
        if self.__label_text.is_shown():
            movements = {
                ProgressBar.Side.TOP.value: {
                    "bottom": self.top - offset,
                    "centerx": self.centerx,
                },
                ProgressBar.Side.BOTTOM.value: {
                    "top": self.bottom + offset,
                    "centerx": self.centerx,
                },
                ProgressBar.Side.LEFT.value: {
                    "right": self.left - offset,
                    "centery": self.centery,
                },
                ProgressBar.Side.RIGHT.value: {
                    "left": self.right + offset,
                    "centery": self.centery,
                },
            }
            side = self.__label_text_side
            if side in movements:
                self.__label_text.set_position(**movements[side])
                self.__label_text.draw_onto(target)

    def set_bounds(self, /, from_: float, to: float) -> None:
        from_ = float(from_)
        to = float(to)
        if to <= from_:
            raise ValueError("end value 'to' must be greather than 'from'")
        self.__start = from_
        self.__end = to
        self.value = from_

    def show_value(self, /, side: str, round_n: int = 0, **kwargs: Any) -> None:
        self.__value_text.config(**kwargs)
        self.__value_text_side = ProgressBar.Side(side).value
        self.__value_text_round_n = int(round_n)
        self.__value_text_type = "value"
        self.__value_text.show()

    def hide_value(self, /) -> None:
        self.__value_text.hide()
        self.__value_text_side = str()
        self.__value_text_round_n = 0
        self.__value_text_type = str()

    def show_percent(self, /, side: str, round_n: int = 0, **kwargs: Any) -> None:
        self.show_value(side, round_n, **kwargs)
        self.__value_text_type = "percent"

    def hide_percent(self, /) -> None:
        self.hide_value()

    def config_value_text(self, /, **kwargs: Any) -> None:
        kwargs.pop("message", None)
        self.__value_text.config(**kwargs)

    def show_label(self, /, label: str, side: str, **kwargs: Any) -> None:
        self.__label_text.config(message=label, **kwargs)
        self.__label_text_side = ProgressBar.Side(side).value
        self.__label_text.show()

    def hide_label(self, /) -> None:
        self.__label_text.hide()
        self.__label_text_side = str()

    def config_label_text(self, /, message: Optional[str] = None, **kwargs: Any) -> None:
        if message is not None:
            kwargs["message"] = message
        self.__label_text.config(**kwargs)

    def _apply_both_rotation_and_scale(self, /) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self, /) -> None:
        raise NotImplementedError

    def _apply_only_scale(self, /) -> None:
        super()._apply_only_scale()
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect
        outline_rect.scale = scale_rect.scale = self.scale

    config.enum("orient", Orient, return_value=True)

    @config.value_converter("value")
    def __valid_value(self, /, value: Any) -> float:
        return valid_float(value=value, min_value=self.__start, max_value=self.__end)

    config.value_converter_static("percent", valid_float(min_value=0, max_value=1))

    config.getter("scale_color", lambda self: self.__scale_rect.config.get("color"))
    config.setter("scale_color", lambda self, color: self.__scale_rect.config.set("color", color))

    @config.on_update_value("value")
    def __update_percent(self, /, value: float) -> None:
        start: float = self.__start
        end: float = self.__end
        self.__percent = (value - start) / (end - start) if end > start else 0

    @config.on_update_value("percent")
    def __update_value(self, /, percent: float) -> None:
        start: float = self.__start
        end: float = self.__end
        self.__value = start + (percent * (end - start)) if end > start else 0

    @config.getter_key("outline")
    @config.getter_key("outline_color")
    def __outline_getter(self, /, option: str) -> Any:
        return self.__outline_rect.config.get(option)

    @config.setter_key("outline")
    @config.setter_key("outline_color")
    def __outline_setter(self, /, option: str, value: Any) -> None:
        self.__outline_rect.config.set(option, value)

    @config.on_update_key_value("border_radius")
    @config.on_update_key_value("border_top_left_radius")
    @config.on_update_key_value("border_top_right_radius")
    @config.on_update_key_value("border_bottom_left_radius")
    @config.on_update_key_value("border_bottom_right_radius")
    def __update_all_shapes(self, /, option: str, value: Any) -> None:
        self.__scale_rect.config.set(option, value)
        self.__outline_rect.config.set(option, value)

    @config.on_update("value")
    @config.on_update("percent")
    @config.on_update("orient")
    @config.on_update("local_width")
    @config.on_update("local_height")
    def __update_scale(self, /) -> None:
        width, height = self.local_size
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect
        percent: float = self.__percent
        if self.orient == ProgressBar.Orient.HORIZONTAL:
            scale_rect.config(local_width=width * percent, local_height=height)
        else:
            scale_rect.config(local_width=width, local_height=height * percent)
        outline_rect.config(local_width=width, local_height=height)

    @property
    def from_value(self, /) -> float:
        return self.__start

    @property
    def to_value(self, /) -> float:
        return self.__end
