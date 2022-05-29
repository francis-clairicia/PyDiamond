# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Image module"""

from __future__ import annotations

__all__ = ["Image"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING, Any, Mapping, overload

from pygame.transform import rotozoom as _surface_rotozoom

from .color import Color
from .drawable import TDrawable
from .rect import Rect
from .surface import Surface, create_surface, load_image, save_image

if TYPE_CHECKING:
    from .renderer import AbstractRenderer


class Image(TDrawable):

    __slots__ = (
        "__default_image",
        "__image",
        "__smooth_scale",
    )

    @overload
    def __init__(self) -> None:
        ...

    @overload
    def __init__(self, image: Surface, *, copy: bool = True, width: float | None = None, height: float | None = None) -> None:
        ...

    @overload
    def __init__(self, image: str, *, width: float | None = None, height: float | None = None) -> None:
        ...

    def __init__(
        self,
        image: Surface | str | None = None,
        *,
        copy: bool = True,
        width: float | None = None,
        height: float | None = None,
    ) -> None:
        super().__init__()

        self.__default_image: Surface
        self.__image: Surface

        match image:
            case None:
                image = create_surface((0, 0))
            case Surface():
                if copy:
                    image = image.copy()
            case str():
                image = load_image(image)
            case _:
                raise TypeError(f"Invalid argument: {image!r}")

        self.__default_image = image
        self.__image = image

        match (width, height):
            case (int() | float() as width, int() | float() as height):
                self.scale_to_size((width, height))
            case (int() | float() as width, None):
                self.scale_to_width(width)
            case (None, int() | float() as height):
                self.scale_to_height(height)
            case (None, None):
                pass
            case _:
                raise TypeError(f"Invalid argument: {image!r}")

        self.topleft = (0, 0)

    def draw_onto(self, target: AbstractRenderer) -> None:
        target.draw_surface(self.__image, self.topleft)

    def get(self, apply_rotation_scale: bool = False) -> Surface:
        if apply_rotation_scale:
            return self.__image.copy()
        return self.__default_image.copy()

    @overload
    def set(self, image: Surface, copy: bool = True) -> None:
        ...

    @overload
    def set(self, image: None) -> None:
        ...

    def set(self, image: Surface | None, copy: bool = True) -> None:
        center: tuple[float, float] = self.center
        if image is None:
            self.__default_image = create_surface((0, 0))
        else:
            self.__default_image = image.copy() if copy else image
        self.apply_rotation_scale()
        self.center = center

    def fill(self, color: Color, rect: Rect | None = None) -> None:
        mask = create_surface(self.__default_image.get_size() if rect is None else rect.size)
        mask.fill(color)
        self.__default_image.blit(mask, rect or (0, 0))
        self.apply_rotation_scale()

    def load(self, file: str) -> None:
        center: tuple[float, float] = self.center
        self.__default_image = load_image(file)
        self.apply_rotation_scale()
        self.center = center

    def save(self, file: str) -> None:
        save_image(self.__image, file)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def _apply_both_rotation_and_scale(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, self.angle, self.scale)

    def _apply_only_rotation(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, self.angle, 1)

    def _apply_only_scale(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, 0, self.scale)

    def _freeze_state(self) -> dict[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        state["image"] = self.__image
        return state

    def _set_frozen_state(self, angle: float, scale: float, state: Mapping[str, Any] | None) -> bool:
        res = super()._set_frozen_state(angle, scale, state)
        if state is None:
            return res
        self.__image = state["image"]
        return True
