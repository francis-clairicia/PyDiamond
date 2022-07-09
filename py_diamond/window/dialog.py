# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Dialog module"""

from __future__ import annotations

__all__ = [
    "Dialog",
    "PopupDialog",
]

from abc import abstractmethod
from typing import Any

from ..graphics.color import BLACK, TRANSPARENT, WHITE, Color
from ..graphics.movable import MovableProxy
from ..graphics.shape import RectangleShape
from ..system.object import final
from ..system.validation import valid_optional_float
from .event import WindowSizeChangedEvent
from .scene import Scene, SceneWindow


class Dialog(Scene):
    def __init__(self) -> None:
        super().__init__()
        self.__master: Scene
        try:
            self.__master
        except AttributeError:
            raise TypeError(f"Trying to instantiate {self.__class__.__name__!r} dialog outside a SceneWindow manager") from None
        self.background_color = Color(0, 0, 0, 0)

    def run_start_transition(self) -> None:
        pass

    def run_quit_transition(self) -> None:
        pass

    @property
    def master(self) -> Scene:
        return self.__master


class PopupDialog(Dialog):
    def awake(
        self,
        *,
        width_ratio: float | None = None,
        height_ratio: float | None = None,
        width: float | None = None,
        height: float | None = None,
        bg_color: Color = WHITE,
        outline: int = 3,
        outline_color: Color = BLACK,
        border_radius: int = -1,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        # draggable: bool = False,
        **kwargs: Any,
    ) -> None:
        super().awake(**kwargs)
        window: SceneWindow = self.window
        width_ratio = valid_optional_float(value=width_ratio, min_value=0, max_value=1)
        height_ratio = valid_optional_float(value=height_ratio, min_value=0, max_value=1)
        width = valid_optional_float(value=width, min_value=0)
        height = valid_optional_float(value=height, min_value=0)
        if width is not None and width_ratio is not None:
            raise ValueError("Must give either 'width' or 'width_ratio', not both")
        if height is not None and height_ratio is not None:
            raise ValueError("Must give either 'height' or 'height_ratio', not both")

        self.__width_ratio: float | None = None
        self.__height_ratio: float | None = None

        if width is None:
            if width_ratio is None:
                width_ratio = 0.5
            self.__width_ratio = width_ratio
            width = window.width * width_ratio
        if height is None:
            if height_ratio is None:
                height_ratio = 0.5
            self.__height_ratio = height_ratio
            height = window.height * height_ratio

        self.__bg: RectangleShape = RectangleShape(
            width,
            height,
            bg_color,
            outline=0,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        self.__outline: RectangleShape = RectangleShape(
            width,
            height,
            TRANSPARENT,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )

        if self.__width_ratio or self.__height_ratio:  # Exclude '0' value
            self.event.bind(WindowSizeChangedEvent, self.__handle_window_resize)
        # if draggable:
        #     from .draggable import Draggable  # lazy import to avoid circular import
        #     setattr(self, "__draggable", Draggable(self, target=self.__bg))

    def on_start_loop_before_transition(self) -> None:
        self.set_default_popup_position()
        return super().on_start_loop_before_transition()

    def set_default_popup_position(self) -> None:
        self.popup.center = self.window.center

    @final
    def render(self) -> None:
        self.__outline.center = self.__bg.center
        self.window.draw(self.__bg)
        self._render()
        self.window.draw(self.__outline)

    @abstractmethod
    def _render(self) -> None:
        raise NotImplementedError

    def _on_popup_resize(self) -> None:
        pass

    def __handle_window_resize(self, event: WindowSizeChangedEvent) -> None:
        bg: RectangleShape = self.__bg
        outline: RectangleShape = self.__outline
        width_ratio: float | None = self.__width_ratio
        height_ratio: float | None = self.__height_ratio
        width: float | None = event.x * width_ratio if width_ratio is not None else None
        height: float | None = event.y * height_ratio if height_ratio is not None else None

        if width is not None and height is not None:
            bg.local_size = (width, height)
        elif width is not None:
            bg.local_width = width
        elif height is not None:
            bg.local_height = height
        else:
            return
        outline.local_size = bg.local_size
        return self._on_popup_resize()

    @property
    def popup(self) -> MovableProxy:
        return MovableProxy(self.__bg)
