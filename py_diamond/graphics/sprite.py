# -*- coding: Utf-8 -*

from __future__ import annotations

__all__ = ["Sprite", "AnimatedSprite"]

from typing import Any, Iterable, List, Optional, Tuple, Type, TypeVar

import pygame.mask
import pygame.transform
from pygame.mask import Mask
from pygame.sprite import Sprite as _PygameSprite, collide_mask

from ..system.clock import Clock
from .drawable import TDrawable
from .rect import Rect
from .renderer import Renderer
from .surface import Surface, create_surface


class Sprite(TDrawable, _PygameSprite):
    def __init__(self, /, image: Optional[Surface] = None, mask_threshold: int = 127) -> None:
        TDrawable.__init__(self)
        _PygameSprite.__init__(self)
        self.__default_image: Surface = image.copy() if image is not None else create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__mask_threshold: int
        self.__mask: Mask
        self.__smooth_scale: bool = False
        self.set_mask_threshold(mask_threshold)

    def update(self, /, *args: Any, **kwargs: Any) -> None:
        super().update(*args, **kwargs)

    def draw_onto(self, /, target: Renderer) -> None:
        image: Surface = self.__image
        topleft: Tuple[float, float] = self.topleft
        target.draw(image, topleft)

    def get_local_size(self, /) -> Tuple[float, float]:
        return self.__default_image.get_size()

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
        self.__update_mask()

    def _apply_only_rotation(self, /) -> None:
        angle: float = self.angle
        image: Surface = self.__default_image
        self.__image = pygame.transform.rotate(image, angle)
        self.__update_mask()

    def _apply_only_scale(self, /) -> None:
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = pygame.transform.rotozoom(image, 0, scale)
        elif scale != 1:
            w, h = self.get_local_size()
            w = round(w * scale)
            h = round(h * scale)
            image = pygame.transform.smoothscale(image, (w, h))
        self.__update_mask()

    def __update_mask(self, /) -> None:
        self.__mask = pygame.mask.from_surface(self.__image, self.__mask_threshold)

    def get_size(self, /) -> Tuple[float, float]:
        return self.__image.get_size()

    def get_mask_threshold(self, /) -> int:
        return self.__mask_threshold

    def set_mask_threshold(self, /, threshold: int) -> None:
        self.__mask_threshold = min(max(int(threshold), 0), 255)
        self.__update_mask()

    def use_smooth_scale(self, /, status: bool) -> None:
        former_state: bool = self.__smooth_scale
        self.__smooth_scale = actual_state = bool(status)
        if former_state != actual_state:
            self.apply_rotation_scale()

    def is_colliding(self, /, other: Sprite) -> bool:
        return collide_mask(self, other) is not None

    @property
    def default_image(self, /) -> Surface:
        return self.__default_image.copy()

    @default_image.setter
    def default_image(self, /, new_image: Surface) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = new_image.copy()
        self.apply_rotation_scale()
        self.center = center

    @property
    def image(self, /) -> Surface:  # type: ignore[override]
        return self.__image

    @property
    def rect(self, /) -> Rect:  # type: ignore[override]
        return super().rect

    @property
    def mask(self, /) -> Mask:
        return self.__mask


class AnimatedSprite(Sprite):
    __T = TypeVar("__T", bound="AnimatedSprite")

    def __init__(self, /, image: Surface, *images: Surface, mask_threshold: int = 127) -> None:
        super().__init__(image=image, mask_threshold=mask_threshold)
        self.__list: List[Surface] = [self.default_image, *(i.copy() for i in images)]
        self.__sprite_idx: int = 0
        self.__clock: Clock = Clock()
        self.__wait_time: float = 10
        self.__animation: bool = False
        self.__loop: bool = False

    @classmethod
    def from_iterable(cls: Type[__T], iterable: Iterable[Surface], *, mask_threshold: int = 127) -> __T:
        return cls(*iterable, mask_threshold=mask_threshold)

    @classmethod
    def from_spritesheet(cls: Type[__T], img: Surface, rect_list: List[Rect], *, mask_threshold: int = 127) -> __T:
        return cls.from_iterable((img.subsurface(rect) for rect in rect_list), mask_threshold=mask_threshold)

    def update(self, /, *args: Any, **kwargs: Any) -> None:
        if self.is_sprite_animating() and self.__clock.elapsed_time(self.__wait_time):
            self.__sprite_idx = sprite_idx = (self.__sprite_idx + 1) % len(self.__list)
            self.default_image = self.__list[sprite_idx]
            if sprite_idx == 0 and not self.__loop:
                self.stop_sprite_animation(reset=True)
        super().update(*args, **kwargs)

    def is_sprite_animating(self, /) -> bool:
        return self.__animation

    def start_sprite_animation(self, /, loop: bool = False) -> None:
        if len(self.__list) <= 1:
            return
        self.__loop = bool(loop)
        self.__sprite_idx = 0
        self.__animation = True
        self.__clock.restart()
        self.default_image = self.__list[0]

    def restart_sprite_animation(self, /) -> None:
        if len(self.__list) <= 1:
            return
        self.__animation = True
        self.__clock.restart(reset=False)

    def stop_sprite_animation(self, /, reset: bool = False) -> None:
        self.__animation = False
        if reset:
            self.__sprite_idx = 0
            self.__loop = False
            self.default_image = self.__list[0]

    @property
    def ratio(self, /) -> float:
        return self.__wait_time

    @ratio.setter
    def ratio(self, /, value: float) -> None:
        self.__wait_time = max(float(value), 0)