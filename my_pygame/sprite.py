# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, List, Optional, Tuple

import pygame.mask
import pygame.transform

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.sprite import Sprite as _PygameSprite
from pygame.mask import Mask

from .drawable import Drawable
from .surface import create_surface
from .clock import Clock


class Sprite(Drawable, _PygameSprite):
    def __init__(self, image: Optional[Surface] = None, mask_threshold: int = 127) -> None:
        Drawable.__init__(self)
        _PygameSprite.__init__(self)
        self.__default_image: Surface = image.copy() if image is not None else create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__mask_threshold: int
        self.__mask: Mask
        self.__smooth_scale: bool = False
        self.set_mask_threshold(mask_threshold)

    def copy(self) -> Sprite:
        return Sprite(self.__default_image, mask_threshold=self.__mask_threshold)

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    def draw_onto(self, surface: Surface) -> None:
        surface.blit(self.__image, self.topleft)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__default_image.get_size()

    def _apply_rotation_scale(self) -> None:
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
        self.__update_mask()

    def __update_mask(self) -> None:
        self.__mask = pygame.mask.from_surface(self.__image, self.__mask_threshold)

    def get_size(self) -> Tuple[float, float]:
        return self.__image.get_size()

    def get_mask_threshold(self) -> int:
        return self.__mask_threshold

    def set_mask_threshold(self, threshold: int) -> None:
        self.__mask_threshold = max(int(threshold), 0)
        self.__mask_threshold = min(self.__mask_threshold, 255)
        self.__update_mask()

    def use_smooth_scale(self, status: bool) -> None:
        former_state: bool = self.__smooth_scale
        self.__smooth_scale = actual_state = bool(status)
        if former_state != actual_state:
            self._apply_rotation_scale()

    @property
    def default_image(self) -> Surface:
        return self.__default_image.copy()

    @default_image.setter
    def default_image(self, new_image: Surface) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = new_image.copy()
        self._apply_rotation_scale()
        self.center = center

    @property
    def image(self) -> Surface:  # type: ignore[override]
        return self.__image.copy()

    @property
    def rect(self) -> Rect:  # type: ignore[override]
        return super().rect

    @property
    def mask(self) -> Mask:
        return self.__mask


class AnimatedSprite(Sprite):
    def __init__(self, image: Surface, *images: Surface, mask_threshold: int = 127) -> None:
        super().__init__(image=image, mask_threshold=mask_threshold)
        self.__list: List[Surface] = [self.default_image, *(i.copy() for i in images)]
        self.__sprite_idx: int = 0
        self.__clock: Clock = Clock()
        self.__wait_time: float = 10
        self.__animation: bool = False
        self.__loop: bool = False

    def copy(self) -> AnimatedSprite:
        return AnimatedSprite(*self.__list, mask_threshold=self.get_mask_threshold())

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.is_sprite_animating() and self.__clock.elapsed_time(self.__wait_time):
            self.__sprite_idx = sprite_idx = (self.__sprite_idx + 1) % len(self.__list)
            self.default_image = self.__list[sprite_idx]
            if sprite_idx == 0 and not self.__loop:
                self.stop_sprite_animation(reset=True)

    def is_sprite_animating(self) -> bool:
        return self.__animation

    def start_sprite_animation(self, loop: bool = False) -> None:
        if len(self.__list) <= 1:
            return
        self.__loop = bool(loop)
        self.__sprite_idx = 0
        self.__animation = True
        self.__clock.restart()
        self.default_image = self.__list[0]

    def restart_sprite_animation(self) -> None:
        if len(self.__list) <= 1:
            return
        self.__animation = True
        self.__clock.restart(reset=False)

    def stop_sprite_animation(self, reset: bool = False) -> None:
        self.__animation = False
        if reset:
            self.__sprite_idx = 0
            self.__loop = False
            self.default_image = self.__list[0]

    @property
    def ratio(self) -> float:
        return self.__wait_time

    @ratio.setter
    def ratio(self, value: float) -> None:
        self.__wait_time = max(float(value), 0)
