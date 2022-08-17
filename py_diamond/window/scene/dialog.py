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
from typing import TYPE_CHECKING, Any

from ...graphics.color import BLACK, TRANSPARENT, WHITE, Color
from ...graphics.movable import MovableProxy
from ...graphics.shape import RectangleShape
from ...system.object import final
from ...system.validation import valid_optional_float
from . import Scene, SceneWindow

if TYPE_CHECKING:
    from ..draggable import Draggable


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
        draggable: bool = False,
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

        if width is None:
            if width_ratio is None:
                width_ratio = 0.5
            width = window.width * width_ratio
        if height is None:
            if height_ratio is None:
                height_ratio = 0.5
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

        self.draggable_popup: Draggable | None = None
        if draggable:
            from ..draggable import DraggingContainer  # lazy import to avoid circular import

            self.draggable_popup = DraggingContainer(self, target=self.__bg)

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

    @property
    def popup(self) -> MovableProxy:
        return MovableProxy(self.__bg)
