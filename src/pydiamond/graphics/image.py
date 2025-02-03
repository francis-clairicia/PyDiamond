# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Image module"""

from __future__ import annotations

__all__ = ["Image"]

from typing import TYPE_CHECKING, Any, Mapping, overload

from pygame.transform import rotozoom as _surface_rotozoom
from typing_extensions import assert_never

from ..math.rect import Rect
from ._transform import rotozoom2 as _surface_rotozoom2, scale_by as _surface_scale_by
from .color import Color
from .drawable import Drawable
from .surface import Surface, create_surface, save_image
from .transformable import Transformable

if TYPE_CHECKING:
    from .renderer import AbstractRenderer


class Image(Drawable, Transformable):
    def __init__(
        self,
        image: Surface | None = None,
        *,
        width: float | None = None,
        height: float | None = None,
        copy: bool = True,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)

        self.__default_image: Surface
        self.__image: Surface

        match image:
            case None:
                image = create_surface((0, 0))
            case Surface():
                if copy:
                    image = image.copy()
            case _:
                assert_never(image)

        self.__default_image = image
        self.__image = image

        if width is not None and height is not None:
            self.scale_to_size((width, height))
        elif width is not None:
            self.scale_to_width(width)
        elif height is not None:
            self.scale_to_height(height)

        self.topleft = (0, 0)

    def draw_onto(self, target: AbstractRenderer) -> None:
        target.draw_surface(self.__image, self.topleft)

    def get(self, apply_rotation_scale: bool = False) -> Surface:
        if apply_rotation_scale:
            return self.__image.copy()
        return self.__default_image.copy()

    @overload
    def set(self, image: Surface, copy: bool = True) -> None: ...

    @overload
    def set(self, image: None) -> None: ...

    def set(self, image: Surface | None, copy: bool = True) -> None:
        center: tuple[float, float] = self.center
        if image is None:
            self.__default_image = create_surface((0, 0))
        else:
            self.__default_image = image.copy() if copy else image
        self.update_transform()
        self.center = center

    def fill(self, color: Color, rect: Rect | None = None) -> None:
        mask = create_surface(self.__default_image.get_size() if rect is None else rect.size)
        mask.fill(color)
        self.__default_image.blit(mask, rect or (0, 0))
        self.update_transform()

    def save(self, filepath: str) -> None:
        save_image(self.__image, filepath)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

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
