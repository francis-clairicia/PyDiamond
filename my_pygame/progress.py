# -*- coding: Utf-8 -*

from __future__ import annotations
from enum import Enum, unique
from typing import Any, Dict, Optional, Tuple, Union

from pygame.color import Color


from .shape import RectangleShape
from .renderer import Renderer
from .text import Text
from .colors import BLACK, GRAY, TRANSPARENT, WHITE
from .theme import NoTheme, ThemeType
from .configuration import ConfigAttribute, Configuration, initializer, no_object
from .utils import valid_float


class ProgressBar(RectangleShape):
    @unique
    class Side(str, Enum):
        TOP = "top"
        BOTTOM = "bottom"
        LEFT = "left"
        RIGHT = "right"
        INSIDE = "inside"

    @initializer
    def __init__(
        self,
        width: float,
        height: float,
        from_: float = 0,
        to: float = 1,
        default: Optional[float] = None,
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

        self.__label_text = Text()
        self.__label_text_side = str()
        self.__value_text = Text()
        self.__value_text_side = str()
        self.__value_text_round_n = 0
        self.__value_text_type = str()

        self.hide_label()
        self.hide_value()

    def copy(self) -> ProgressBar:
        return ProgressBar(
            width=self.local_width,
            height=self.local_height,
            from_=self.__start,
            to=self.__end,
            default=self.__value,
            color=self.color,
            scale_color=self.scale_color,
            outline=self.outline,
            outline_color=self.outline_color,
            border_radius=self.border_radius,
            border_top_left_radius=self.border_top_left_radius,
            border_top_right_radius=self.border_top_right_radius,
            border_bottom_left_radius=self.border_bottom_left_radius,
            border_bottom_right_radius=self.border_bottom_right_radius,
            theme=NoTheme,
        )

    def draw_onto(self, target: Renderer) -> None:
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect

        outline_rect.center = self.center
        midleft: Tuple[float, float] = self.midleft
        outline: int = self.outline
        scale_rect.midleft = (midleft[0] + outline / 2, midleft[1])

        super().draw_onto(target)
        scale_rect.draw_onto(target)
        outline_rect.draw_onto(target)

        offset = 10
        movements: Dict[str, Dict[str, Union[float, Tuple[float, float]]]]
        if self.__value_text.is_shown() and self.__value_text_type in ["value", "percent"]:
            movements = {
                ProgressBar.Side.TOP.value: {"bottom": self.top - offset, "centerx": self.centerx},
                ProgressBar.Side.BOTTOM.value: {"top": self.bottom + offset, "centerx": self.centerx},
                ProgressBar.Side.LEFT.value: {"right": self.left - offset, "centery": self.centery},
                ProgressBar.Side.RIGHT.value: {"left": self.right + offset, "centery": self.centery},
                ProgressBar.Side.INSIDE.value: {"center": self.center},
            }
            side = self.__value_text_side
            round_n = self.__value_text_round_n
            if side in movements:
                if self.__value_text_type == "value":
                    self.__value_text.message = f"{round(self.value, round_n) if round_n > 0 else round(self.value)}"
                elif self.__value_text_type == "percent":
                    value = self.percent * 100
                    self.__value_text.message = f"{round(value, round_n) if round_n > 0 else round(value)}%"
                self.__value_text.set_position(**movements[side])
                self.__value_text.draw_onto(target)
        if self.__label_text.is_shown():
            movements = {
                ProgressBar.Side.TOP.value: {"bottom": self.top - offset, "centerx": self.centerx},
                ProgressBar.Side.BOTTOM.value: {"top": self.bottom + offset, "centerx": self.centerx},
                ProgressBar.Side.LEFT.value: {"right": self.left - offset, "centery": self.centery},
                ProgressBar.Side.RIGHT.value: {"left": self.right + offset, "centery": self.centery},
            }
            side = self.__label_text_side
            if side in movements:
                self.__label_text.set_position(**movements[side])
                self.__label_text.draw_onto(target)

    def set_bounds(self, from_: float, to: float) -> None:
        from_ = float(from_)
        to = float(to)
        if to <= from_:
            raise ValueError("end value 'to' must be greather than 'from'")
        self.__start = from_
        self.__end = to
        self.value = from_

    def show_value(self, side: str, round_n: int = 0, **kwargs: Any) -> None:
        self.__value_text.config(**kwargs)
        self.__value_text_side = ProgressBar.Side(side).value
        self.__value_text_round_n = int(round_n)
        self.__value_text_type = "value"
        self.__value_text.show()

    def hide_value(self) -> None:
        self.__value_text.hide()
        self.__value_text_side = str()
        self.__value_text_round_n = 0
        self.__value_text_type = str()

    def show_percent(self, side: str, round_n: int = 0, **kwargs: Any) -> None:
        self.show_value(side, round_n, **kwargs)
        self.__value_text_type = "percent"

    def hide_percent(self) -> None:
        self.hide_value()

    def config_value_text(self, **kwargs: Any) -> None:
        kwargs.pop("message", None)
        self.__value_text.config(**kwargs)

    def show_label(self, label: str, side: str, **kwargs: Any) -> None:
        self.__label_text.config(message=label, **kwargs)
        self.__label_text_side = ProgressBar.Side(side).value
        self.__label_text.show()

    def hide_label(self) -> None:
        self.__label_text.hide()
        self.__label_text_side = str()

    def config_label_text(self, message: Optional[str] = None, **kwargs: Any) -> None:
        if message is not None:
            kwargs["message"] = message
        self.__label_text.config(**kwargs)

    def _apply_rotation_scale(self) -> None:
        if self.angle != 0:
            raise NotImplementedError
        super()._apply_rotation_scale()
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect
        outline_rect.scale = scale_rect.scale = self.scale

    config = Configuration("value", "percent", "scale_color", parent=RectangleShape.config)

    value: ConfigAttribute[float] = ConfigAttribute()
    percent: ConfigAttribute[float] = ConfigAttribute()
    scale_color: ConfigAttribute[Color] = ConfigAttribute()

    @config.validator("value")
    def __valid_value(self, value: Any) -> float:
        value_validator = valid_float(min_value=self.__start, max_value=self.__end)
        return value_validator(value)

    config.validator("percent", no_object(valid_float(min_value=0, max_value=1)))

    config.getter_property("scale_color", lambda self: self.__scale_rect.config.get("color"))
    config.setter_property("scale_color", lambda self, color: self.__scale_rect.config.set("color", color))

    @config.value_updater_property("value")
    def __update_percent(self, value: float) -> None:
        start: float = self.__start
        end: float = self.__end
        self.__percent = (value - start) / (end - start) if end > start else 0

    @config.value_updater_property("percent")
    def __update_value(self, percent: float) -> None:
        start: float = self.__start
        end: float = self.__end
        self.__value = start + (percent * (end - start)) if end > start else 0

    @config.getter("outline")
    @config.getter("outline_color")
    def __outline_getter(self, option: str) -> Any:
        return self.__outline_rect.config.get(option)

    @config.setter("outline")
    @config.setter("outline_color")
    def __outline_setter(self, option: str, value: Any) -> None:
        self.__outline_rect.config.set(option, value)

    @config.value_updater("local_height")
    @config.value_updater("border_radius")
    @config.value_updater("border_top_left_radius")
    @config.value_updater("border_top_right_radius")
    @config.value_updater("border_bottom_left_radius")
    @config.value_updater("border_bottom_right_radius")
    def __update_all_shapes(self, option: str, value: Any) -> None:
        self.__scale_rect.config.set(option, value)
        self.__outline_rect.config.set(option, value)

    @config.updater("value")
    @config.updater("percent")
    @config.updater("local_width")
    def __update_scale(self) -> None:
        width: float = self.local_width
        scale_rect: RectangleShape = self.__scale_rect
        outline_rect: RectangleShape = self.__outline_rect
        scale_rect.local_width = width * self.__percent
        outline_rect.local_width = width

    @property
    def from_value(self) -> float:
        return self.__start

    @property
    def to_value(self) -> float:
        return self.__end
