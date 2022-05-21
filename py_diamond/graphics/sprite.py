# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Sprite module"""

from __future__ import annotations

__all__ = ["AnimatedSprite", "LayeredSpriteGroup", "Mask", "Sprite", "SpriteGroup"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING, Any, Final, Iterable, Mapping, TypeVar

from pygame.mask import Mask, from_surface as _pg_mask_from_surface
from pygame.transform import rotate as _surface_rotate, scale as _surface_fastscale, smoothscale as _surface_smoothscale

from ..system.object import final
from ..window.clock import Clock
from .drawable import BaseDrawableGroup, BaseLayeredDrawableGroup, Drawable, TDrawable
from .rect import Rect
from .renderer import AbstractRenderer, BlendMode
from .surface import Surface, create_surface


class Sprite(TDrawable):
    DEFAULT_MASK_THRESHOLD: Final[int] = 127

    __slots__ = (
        "__default_image",
        "__image",
        "__mask_threshold",
        "__mask",
        "__smooth_scale",
        "__blend_mode",
    )

    def __init__(self, image: Surface | None = None, mask_threshold: int = DEFAULT_MASK_THRESHOLD) -> None:
        TDrawable.__init__(self)
        self.__default_image: Surface = image.convert_alpha() if image is not None else create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__mask_threshold: int
        self.__mask: Mask
        self.__smooth_scale: bool = False
        self.__blend_mode: BlendMode = BlendMode.NONE
        self.set_mask_threshold(mask_threshold)

    def fixed_update(self, *args: Any, **kwargs: Any) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.animation.update(interpolation)

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    def draw_onto(self, target: AbstractRenderer) -> None:
        image: Surface = self.__image
        topleft: tuple[float, float] = self.topleft
        blend_mode: BlendMode = self.__blend_mode
        target.draw_surface(image, topleft, special_flags=blend_mode)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def _apply_both_rotation_and_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        image: Surface = self.__default_image
        if scale != 1:
            w, h = image.get_size()
            if self.__smooth_scale:
                image = _surface_smoothscale(image, (w * scale, h * scale))
            else:
                image = _surface_fastscale(image, (w * scale, h * scale))
        if angle != 0:
            image = _surface_rotate(image, angle)
        self.__image = image

    def _apply_only_rotation(self) -> None:
        angle: float = self.angle
        image: Surface = self.__default_image
        if angle != 0:
            image = _surface_rotate(image, angle)
        self.__image = image

    def _apply_only_scale(self) -> None:
        scale: float = self.scale
        image: Surface = self.__default_image
        if scale != 1:
            w, h = image.get_size()
            if self.__smooth_scale:
                image = _surface_smoothscale(image, (w * scale, h * scale))
            else:
                image = _surface_fastscale(image, (w * scale, h * scale))
        self.__image = image

    def _freeze_state(self) -> Mapping[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        else:
            state = dict(state)
        state["image"] = self.__image
        return state

    def _set_frozen_state(self, angle: float, scale: float, state: Mapping[str, Any] | None) -> bool:
        res = super()._set_frozen_state(angle, scale, state)
        if state is None:
            return res
        self.__image = state["image"]
        return True

    def __update_mask(self) -> None:
        self.__mask = _pg_mask_from_surface(self.__image, self.__mask_threshold)

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def get_mask_threshold(self) -> int:
        return self.__mask_threshold

    def set_mask_threshold(self, threshold: int) -> None:
        self.__mask_threshold = min(max(int(threshold), 0), 255)
        self.__update_mask()

    def use_smooth_scale(self, status: bool) -> None:
        former_state: bool = self.__smooth_scale
        self.__smooth_scale = actual_state = bool(status)
        if former_state != actual_state:
            self.apply_rotation_scale()

    def is_colliding(self, other: Sprite, *, relative: bool = False) -> tuple[int, int] | None:
        this_rect: Rect = self.rect
        other_rect: Rect = other.rect
        xoffset: int = other_rect.x - this_rect.x
        yoffset: int = other_rect.y - this_rect.y
        intersection: tuple[int, int] | None = self.__mask.overlap(other.__mask, (xoffset, yoffset))
        if intersection is not None and not relative:
            intersection = (intersection[0] + this_rect.x, intersection[1] + this_rect.y)
        return intersection

    @property
    def default_image(self) -> Surface:
        return self.__default_image.copy()

    @default_image.setter
    def default_image(self, new_image: Surface) -> None:
        center: tuple[float, float] = self.center
        self.__default_image = new_image.copy()
        self.apply_rotation_scale()
        self.center = center

    @property
    def image(self) -> Surface:
        return self.__image.copy()

    @property
    @final
    def mask(self) -> Mask:
        return self.__mask

    @property
    def blend(self) -> BlendMode:
        return self.__blend_mode

    @blend.setter
    def blend(self, mode: BlendMode) -> None:
        mode = BlendMode(mode)
        self.__blend_mode = mode


class AnimatedSprite(Sprite):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AnimatedSprite")

    __slots__ = (
        "__list",
        "__sprite_idx",
        "__clock",
        "__wait_time",
        "__animation",
        "__loop",
    )

    def __init__(self, image: Surface, *images: Surface, mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD) -> None:
        super().__init__(image=image, mask_threshold=mask_threshold)
        self.__list: list[Surface] = [self.default_image, *(i.convert_alpha() for i in images)]
        self.__sprite_idx: int = 0
        self.__clock: Clock = Clock()
        self.__wait_time: float = 10
        self.__animation: bool = False
        self.__loop: bool = False

    @classmethod
    def from_iterable(
        cls: type[__Self], iterable: Iterable[Surface], *, mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD
    ) -> __Self:
        return cls(*iterable, mask_threshold=mask_threshold)

    @classmethod
    def from_spritesheet(
        cls: type[__Self], img: Surface, rect_list: list[Rect], *, mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD
    ) -> __Self:
        return cls.from_iterable((img.subsurface(rect) for rect in rect_list), mask_threshold=mask_threshold)

    def fixed_update(self, *args: Any, **kwargs: Any) -> None:
        if self.is_sprite_animating() and self.__clock.elapsed_time(self.__wait_time):
            self.__sprite_idx = sprite_idx = (self.__sprite_idx + 1) % len(self.__list)
            self.default_image = self.__list[sprite_idx]
            if sprite_idx == 0 and not self.__loop:
                self.stop_sprite_animation(reset=True)
        super().fixed_update(*args, **kwargs)

    def is_sprite_animating(self) -> bool:
        return self.__animation

    def start_sprite_animation(self, loop: bool = False) -> None:
        if len(self.__list) < 2:
            return
        self.__loop = bool(loop)
        self.__sprite_idx = 0
        self.__animation = True
        self.__clock.restart()
        self.default_image = self.__list[0]

    def restart_sprite_animation(self) -> None:
        if len(self.__list) < 2:
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


class SpriteGroup(BaseDrawableGroup[Sprite], Drawable):
    __slots__ = ()


class LayeredSpriteGroup(BaseLayeredDrawableGroup[Sprite], SpriteGroup):
    __slots__ = ()

    def __init__(self, *objects: Sprite, default_layer: int = 0, **kwargs: Any) -> None:
        super().__init__(*objects, default_layer=default_layer, **kwargs)
