# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Tuple, Union, overload

import pygame.transform
from pygame.surface import Surface

from .drawable import Drawable
from .surface import load_image, save_image


class Image(Drawable):
    @overload
    def __init__(self, image: Surface) -> None:
        ...

    @overload
    def __init__(self, image: str) -> None:
        ...

    def __init__(self, image: Union[Surface, str]) -> None:
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

    def copy(self) -> Image:
        return Image(self.__default_image)

    def to_surface(self) -> Surface:
        return self.__image.copy()

    def draw_onto(self, surface: Surface) -> None:
        surface.blit(self.__image, self.topleft)

    def get(self) -> Surface:
        return self.__default_image.copy()

    def set(self, image: Surface) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = image.copy()
        self._apply_rotation_scale()
        self.center = center

    def load(self, file: str) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = load_image(file)
        self._apply_rotation_scale()
        self.center = center

    def save(self, file: str) -> None:
        save_image(self.__image, file)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__default_image.get_size()

    def get_size(self) -> Tuple[float, float]:
        return self.__image.get_size()

    def use_smooth_scale(self, status: bool) -> None:
        self.__smooth_scale = bool(status)

    def _apply_rotation_scale(self) -> None:
        if not self.__smooth_scale:
            self.__image = pygame.transform.rotozoom(self.__default_image, self.angle, self.scale)
        else:
            if self.scale != 1:
                w, h = self.get_local_size()
                w = round(w * self.scale)
                h = round(h * self.scale)
                self.__image = pygame.transform.smoothscale(self.__default_image, (w, h))
            else:
                self.__image = self.__default_image
            self.__image = pygame.transform.rotate(self.__image, self.angle)
