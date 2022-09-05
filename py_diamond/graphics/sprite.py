# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Sprite module"""

from __future__ import annotations

__all__ = ["AnimatedSprite", "LayeredSpriteGroup", "Mask", "Sprite", "SpriteGroup"]


from collections import deque
from functools import cached_property
from itertools import combinations
from typing import TYPE_CHECKING, Any, Final, Iterable, Iterator, Mapping, TypeVar, overload

from pygame.mask import Mask, from_surface as _pg_mask_from_surface
from pygame.transform import rotozoom as _surface_rotozoom

from ..system.clock import Clock
from ..system.object import Object, final
from ._transform import rotozoom2 as _surface_rotozoom2, scale_by as _surface_scale_by
from .animation import TransformAnimation
from .drawable import BaseDrawableGroup, BaseLayeredDrawableGroup, Drawable
from .rect import Rect
from .renderer import AbstractRenderer, BlendMode
from .surface import Surface, create_surface
from .transformable import Transformable


@final
class _SpriteTransformAnimation(cached_property[TransformAnimation], Object):
    def __init__(self) -> None:
        def func(self: Sprite) -> TransformAnimation:
            return TransformAnimation(self)

        super().__init__(func)

    if TYPE_CHECKING:

        @overload  # type: ignore[override]
        def __get__(self, instance: None, owner: type[Any] | None = None) -> _SpriteTransformAnimation:
            ...

        @overload
        def __get__(self, instance: Sprite, owner: type[Any] | None = None) -> TransformAnimation:
            ...

        def __get__(
            self, instance: Sprite | None, owner: type[Any] | None = None
        ) -> _SpriteTransformAnimation | TransformAnimation:
            ...


class Sprite(Drawable, Transformable):
    DEFAULT_MASK_THRESHOLD: Final[int] = 127

    __slots__ = (
        "__default_image",
        "__image",
        "__mask_threshold",
        "__mask",
        "__smooth_scale",
        "__blend_mode",
    )

    animation: Final[_SpriteTransformAnimation] = final(_SpriteTransformAnimation())  # type: ignore[type-var]

    def __init__(
        self,
        image: Surface | None = None,
        *,
        mask_threshold: int = DEFAULT_MASK_THRESHOLD,
        width: float | None = None,
        height: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.__default_image: Surface = image.convert_alpha() if image is not None else create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__mask_threshold: int
        self.__mask: Mask
        self.__blend_mode: BlendMode = BlendMode.NONE
        self.set_mask_threshold(mask_threshold)

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
                raise TypeError(f"Invalid argument: {(width, height)!r}")

        self.topleft = (0, 0)

    def fixed_update(self, **kwargs: Any) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.animation.update(interpolation)

    def update(self, **kwargs: Any) -> None:
        pass

    @final
    def draw_onto(self, target: AbstractRenderer) -> None:
        target.draw_surface(self.__image, self.topleft, special_flags=self.__blend_mode)

    def get_local_size(self) -> tuple[float, float]:
        return self.__default_image.get_size()

    def _apply_both_rotation_and_scale(self) -> None:
        self.__image = _surface_rotozoom2(self.__default_image, self.angle, self.scale)
        self.update_mask()

    def _apply_only_rotation(self) -> None:
        self.__image = _surface_rotozoom(self.__default_image, self.angle, 1)
        self.update_mask()

    def _apply_only_scale(self) -> None:
        self.__image = _surface_scale_by(self.__default_image, self.scale)
        self.update_mask()

    def _freeze_state(self) -> dict[str, Any] | None:
        state = super()._freeze_state()
        if state is None:
            state = {}
        state["image"] = self.__image
        state["mask"] = self.__mask
        return state

    def _set_frozen_state(self, angle: float, scale: tuple[float, float], state: Mapping[str, Any] | None) -> bool:
        res = super()._set_frozen_state(angle, scale, state)
        if state is None:
            return res
        self.__image = state["image"]
        self.__mask = state["mask"]
        return True

    def update_mask(self) -> None:
        self.__mask = _pg_mask_from_surface(self.__image, self.__mask_threshold)

    def get_size(self) -> tuple[float, float]:
        return self.__image.get_size()

    def get_mask_threshold(self) -> int:
        return self.__mask_threshold

    def set_mask_threshold(self, threshold: int) -> None:
        self.__mask_threshold = min(max(int(threshold), 0), 255)
        self.update_mask()

    def is_colliding(self, other: Sprite) -> bool:
        return self is other or self.is_mask_colliding(other, relative=True) is not None

    @final
    def is_mask_colliding(self, other: Sprite, *, relative: bool = False) -> tuple[int, int] | None:
        this_rect: Rect = self.get_rect()
        if other is self:  # Why would you do that ? Idk
            return (0, 0) if relative else this_rect.topleft
        other_rect: Rect = other.get_rect()
        xoffset: int = other_rect.x - this_rect.x
        yoffset: int = other_rect.y - this_rect.y
        intersection: tuple[int, int] | None = self.__mask.overlap(other.__mask, (xoffset, yoffset))
        if not relative and intersection is not None:
            intersection = (intersection[0] + this_rect.x, intersection[1] + this_rect.y)
        return intersection

    @property
    def default_image(self) -> Surface:
        return self.__default_image.copy()

    @default_image.setter
    def default_image(self, new_image: Surface) -> None:
        center: tuple[float, float] = self.center
        self.__default_image = new_image.copy()
        self.update_transform()
        self.center = center

    @property
    def image(self) -> Surface:
        return self.__image

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

    def __init__(
        self,
        image: Surface,
        *images: Surface,
        mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD,
        width: float | None = None,
        height: float | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(image=image, mask_threshold=mask_threshold, width=width, height=height, **kwargs)
        self.__list: list[Surface] = [self.default_image, *(i.convert_alpha() for i in images)]
        self.__sprite_idx: int = 0
        self.__clock: Clock = Clock()
        self.__wait_time: float = 10
        self.__animation: bool = False
        self.__loop: bool = False

    @classmethod
    def from_iterable(
        cls: type[__Self],
        iterable: Iterable[Surface],
        *,
        mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD,
        width: float | None = None,
        height: float | None = None,
    ) -> __Self:
        return cls(*iterable, mask_threshold=mask_threshold, width=width, height=height)

    @classmethod
    def from_spritesheet(
        cls: type[__Self],
        img: Surface,
        rect_list: Iterable[Rect],
        *,
        mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD,
        width: float | None = None,
        height: float | None = None,
    ) -> __Self:
        return cls.from_iterable(
            (img.subsurface(rect) for rect in rect_list),
            mask_threshold=mask_threshold,
            width=width,
            height=height,
        )

    def fixed_update(self, **kwargs: Any) -> None:
        if self.is_sprite_animating() and self.__clock.elapsed_time(self.__wait_time):
            self.__sprite_idx = sprite_idx = (self.__sprite_idx + 1) % len(self.__list)
            self.default_image = self.__list[sprite_idx]
            if sprite_idx == 0 and not self.__loop:
                self.stop_sprite_animation(reset=True)
        super().fixed_update(**kwargs)

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


_S = TypeVar("_S", bound=Sprite)


class BaseSpriteGroup(BaseDrawableGroup[_S]):
    __slots__ = ()

    def draw_onto(self, target: AbstractRenderer) -> None:
        target.draw_many_surfaces(((s.image, s.topleft, None, s.blend) for s in self), doreturn=False)

    def fixed_update(self, **kwargs: Any) -> None:
        for s in self:
            s.fixed_update(**kwargs)

    def interpolation_update(self, interpolation: float) -> None:
        for s in self:
            s.interpolation_update(interpolation)

    def update(self, **kwargs: Any) -> None:
        for s in self:
            s.update(**kwargs)

    def sprite_collide(self, sprite: _S, dokill: bool) -> Iterator[_S]:
        collide_sprite = sprite.is_colliding
        if dokill:
            for s in (s for s in tuple(self) if collide_sprite(s)):
                s.kill()
                yield s
            return

        return (yield from (s for s in self if collide_sprite(s)))

    def group_collide(self, other: BaseSpriteGroup[_S], dokill_self: bool, dokill_other: bool) -> dict[_S, list[_S]]:
        other_sprite_collide = other.sprite_collide
        if dokill_self:
            crashed: dict[_S, list[_S]] = {}

            for self_sprite, collided_list in (
                (self_sprite, collided_list)
                for self_sprite in tuple(self)
                if (collided_list := list(other_sprite_collide(self_sprite, dokill_other)))
            ):
                self_sprite.kill()
                crashed[self_sprite] = collided_list

            return crashed

        return {
            self_sprite: collided_list
            for self_sprite in self
            if (collided_list := list(other_sprite_collide(self_sprite, dokill_other)))
        }

    def sprite_collide_any(self, sprite: _S) -> _S | None:
        collide_sprite = sprite.is_colliding
        return next((s for s in self if collide_sprite(s)), None)

    def flush_colliding(self) -> list[_S]:
        crashed: deque[_S] = deque()

        for s1, s2 in ((s1, s2) for s1, s2 in combinations(tuple(self), r=2) if s1.is_alive() and s2.is_alive()):
            if s1.is_colliding(s2):
                s1.kill()
                s2.kill()
                crashed.extend((s1, s2))

        return list(crashed)


class SpriteGroup(BaseSpriteGroup[Sprite], Drawable):
    __slots__ = ()


class BaseLayeredSpriteGroup(BaseLayeredDrawableGroup[_S], BaseSpriteGroup[_S]):
    __slots__ = ()

    def __init__(self, *objects: _S, default_layer: int = 0, **kwargs: Any) -> None:
        super().__init__(*objects, default_layer=default_layer, **kwargs)

    def sprite_collide(self, sprite: _S, dokill: bool, *, layer: int | None = None) -> Iterator[_S]:
        sprites: Iterable[_S]

        collide_sprite = sprite.is_colliding
        if dokill:
            sprites = tuple(self) if layer is None else self.get_from_layer(layer)
            for s in (s for s in sprites if collide_sprite(s)):
                s.kill()
                yield s
            return

        sprites = self if layer is None else self.iter_in_layer(layer)
        return (yield from (s for s in sprites if collide_sprite(s)))

    def group_collide(
        self,
        other: BaseSpriteGroup[_S],
        dokill_self: bool,
        dokill_other: bool,
        *,
        layer: int | None = None,
    ) -> dict[_S, list[_S]]:
        sprites: Iterable[_S]

        other_sprite_collide = other.sprite_collide
        if dokill_self:
            crashed: dict[_S, list[_S]] = {}
            sprites = tuple(self) if layer is None else self.get_from_layer(layer)

            for self_sprite, collided_list in (
                (self_sprite, collided_list)
                for self_sprite in sprites
                if (collided_list := list(other_sprite_collide(self_sprite, dokill_other)))
            ):
                self_sprite.kill()
                crashed[self_sprite] = collided_list

            return crashed

        sprites = self if layer is None else self.iter_in_layer(layer)
        return {
            self_sprite: collided_list
            for self_sprite in sprites
            if (collided_list := list(other_sprite_collide(self_sprite, dokill_other)))
        }

    def sprite_collide_any(self, sprite: _S, *, layer: int | None = None) -> _S | None:
        sprites: Iterable[_S] = self if layer is None else self.iter_in_layer(layer)
        collide_sprite = sprite.is_colliding
        return next((s for s in sprites if collide_sprite(s)), None)

    def flush_colliding(self, *, layer: int | None = None) -> list[_S]:
        crashed: deque[_S] = deque()
        sprites: Iterable[_S] = tuple(self) if layer is None else self.get_from_layer(layer)

        for s1, s2 in ((s1, s2) for s1, s2 in combinations(sprites, r=2) if s1.is_alive() and s2.is_alive()):
            if s1.is_colliding(s2):
                s1.kill()
                s2.kill()
                crashed.extend((s1, s2))

        return list(crashed)


class LayeredSpriteGroup(BaseLayeredSpriteGroup[Sprite], Drawable):
    __slots__ = ()
