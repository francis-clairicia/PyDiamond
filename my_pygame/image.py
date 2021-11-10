# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Optional, Tuple, Union, overload

import pygame.transform
from pygame.surface import Surface

from .drawable import TDrawable
from .renderer import Renderer
from .surface import load_image, save_image

__all__ = ["Image"]


class Image(TDrawable):
    @overload
    def __init__(self, /, image: Surface, *, width: Optional[float] = None, height: Optional[float] = None) -> None:
        ...

    @overload
    def __init__(self, /, image: str, *, width: Optional[float] = None, height: Optional[float] = None) -> None:
        ...

    def __init__(self, /, image: Union[Surface, str], *, width: Optional[float] = None, height: Optional[float] = None) -> None:
        super().__init__()
        self.__default_image: Surface
        self.__image: Surface
        self.__smooth_scale: bool = False

        if isinstance(image, Surface):
            self.__default_image = image.copy()
            self.__image = self.__default_image.copy()
        else:
            self.__default_image = Surface((0, 0))
            self.__image = self.__default_image.copy()
            self.load(image)
        if width is not None and height is not None:
            self.scale_to_size((width, height))
        elif width is not None:
            self.scale_to_width(width)
        elif height is not None:
            self.scale_to_height(height)
        self.topleft = (0, 0)

    def draw_onto(self, /, target: Renderer) -> None:
        image: Surface = self.__image
        topleft: Tuple[float, float] = self.topleft
        target.draw(image, topleft)

    def get(self, /, apply_rotation_scale: bool = False) -> Surface:
        if apply_rotation_scale:
            return self.__image.copy()
        return self.__default_image.copy()

    def set(self, /, image: Surface) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = image.copy()
        self._apply_rotation_scale()
        self.center = center

    def load(self, /, file: str) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = load_image(file)
        self._apply_rotation_scale()
        self.center = center

    def save(self, /, file: str) -> None:
        save_image(self.__image, file)

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self, /) -> Tuple[float, float]:
        return self.__image.get_size()

    def use_smooth_scale(self, /, status: bool) -> None:
        former_state: bool = self.__smooth_scale
        self.__smooth_scale = actual_state = bool(status)
        if former_state != actual_state:
            self._apply_rotation_scale()

    def _apply_both_rotation_and_scale(self, /) -> None:
        angle: float = self.angle
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = pygame.transform.rotozoom(image, angle, scale)
        else:
            if scale != 1:
                w, h = self.get_local_size()
                w = round(w * scale)
                h = round(h * scale)
                image = pygame.transform.smoothscale(image, (w, h))
            self.__image = pygame.transform.rotate(image, angle)

    def _apply_only_rotation(self, /) -> None:
        angle: float = self.angle
        image: Surface = self.__default_image
        self.__image = pygame.transform.rotate(image, angle)

    def _apply_only_scale(self, /) -> None:
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = pygame.transform.rotozoom(image, 0, scale)
        else:
            if scale != 1:
                w, h = self.get_local_size()
                w = round(w * scale)
                h = round(h * scale)
                image = pygame.transform.smoothscale(image, (w, h))
