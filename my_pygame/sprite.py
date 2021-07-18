# -*- coding: Utf-8 -*

from typing import Optional, Tuple

import pygame.mask
import pygame.transform

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.sprite import Sprite as PygameSprite, AbstractGroup
from pygame.mask import Mask

from .drawable import Drawable
from .surface import create_surface


class Sprite(Drawable, PygameSprite):
    def __init__(self, *groups: AbstractGroup, image: Optional[Surface] = None) -> None:
        Drawable.__init__(self)
        PygameSprite.__init__(self, *groups)
        self.__default_image: Surface = image.copy() if image is not None else create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__mask: Mask = pygame.mask.from_surface(self.__image)

    @property
    def default_image(self) -> Surface:
        return self.__default_image

    @default_image.setter
    def default_image(self, new_image: Surface) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = new_image.copy()
        self._apply_rotation_scale()
        self.center = center

    def draw_onto(self, surface: Surface) -> None:
        surface.blit(self.image, self.topleft)

    def get_local_size(self) -> Tuple[float, float]:
        return self.default_image.get_size()

    def to_surface(self) -> Surface:
        return self.image.copy()

    def _apply_rotation_scale(self) -> None:
        w, h = self.get_local_size()
        if self.scale != 1:
            w *= self.scale
            h *= self.scale
            self.__image = pygame.transform.smoothscale(self.default_image, (int(w), int(h)))
        else:
            self.__image = self.__default_image
        self.__image = pygame.transform.rotate(self.__image, self.angle)
        self.__mask = pygame.mask.from_surface(self.__image)

    def get_size(self) -> Tuple[float, float]:
        return self.image.get_size()

    @property
    def image(self) -> Surface:  # type: ignore
        return self.__image

    @property
    def rect(self) -> Rect:  # type: ignore
        return self.image.get_rect(topleft=self.topleft)

    @property
    def mask(self) -> Mask:
        return self.__mask
