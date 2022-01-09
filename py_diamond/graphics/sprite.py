# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Sprite module"""

from __future__ import annotations

__all__ = ["AnimatedSprite", "LayeredSpriteGroup", "Mask", "Sprite", "SpriteGroup"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Any, Final, Iterable, Iterator, List, Optional, Sequence, Tuple, Type, TypeVar, Union, overload

from pygame.mask import Mask, from_surface as _pg_mask_from_surface
from pygame.transform import rotate as _surface_rotate, rotozoom as _surface_rotozoom, smoothscale as _surface_smoothscale

from ..window.clock import Clock
from .drawable import DrawableGroup, LayeredGroup, TDrawable
from .rect import Rect
from .renderer import BlendMode, Renderer
from .surface import Surface, create_surface


class Sprite(TDrawable):
    DEFAULT_MASK_THRESHOLD: Final[int] = 127

    def __init__(self, image: Optional[Surface] = None, mask_threshold: int = DEFAULT_MASK_THRESHOLD) -> None:
        TDrawable.__init__(self)
        self.__default_image: Surface = image.convert_alpha() if image is not None else create_surface((0, 0))
        self.__image: Surface = self.__default_image.copy()
        self.__mask_threshold: int
        self.__mask: Mask
        self.__smooth_scale: bool = False
        self.__blend_mode: BlendMode = BlendMode.NONE
        self.set_mask_threshold(mask_threshold)

    def fixed_update(self, *args: Any, **kwargs: Any) -> None:
        pass

    def update_alpha(self, interpolation: float) -> None:
        pass

    def update(self, *args: Any, **kwargs: Any) -> None:
        pass

    def draw_onto(self, target: Renderer) -> None:
        image: Surface = self.__image
        topleft: Tuple[float, float] = self.topleft
        blend_mode: BlendMode = self.__blend_mode
        target.draw(image, topleft, special_flags=blend_mode)

    def get_local_size(self) -> Tuple[float, float]:
        return self.__default_image.get_size()

    def _apply_both_rotation_and_scale(self) -> None:
        angle: float = self.angle
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = _surface_rotozoom(image, angle, scale)
        else:
            if scale != 1:
                w, h = self.get_local_size()
                w = round(w * scale)
                h = round(h * scale)
                image = _surface_smoothscale(image, (w, h))
            self.__image = _surface_rotate(image, angle)
        self.__update_mask()

    def _apply_only_rotation(self) -> None:
        angle: float = self.angle
        image: Surface = self.__default_image
        self.__image = _surface_rotate(image, angle)
        self.__update_mask()

    def _apply_only_scale(self) -> None:
        scale: float = self.scale
        image: Surface = self.__default_image

        if not self.__smooth_scale:
            self.__image = _surface_rotozoom(image, 0, scale)
        elif scale != 1:
            w, h = self.get_local_size()
            w = round(w * scale)
            h = round(h * scale)
            image = _surface_smoothscale(image, (w, h))
        self.__update_mask()

    def __update_mask(self) -> None:
        self.__mask = _pg_mask_from_surface(self.__image, self.__mask_threshold)

    def get_size(self) -> Tuple[float, float]:
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

    def is_colliding(self, other: Sprite) -> Optional[Tuple[int, int]]:
        this_rect: Rect = self.rect
        other_rect: Rect = other.rect
        xoffset: int = other_rect.x - this_rect.x
        yoffset: int = other_rect.y - this_rect.y
        intersection: Optional[Tuple[int, int]] = self.mask.overlap(other.mask, (xoffset, yoffset))
        if intersection is not None:
            intersection = (intersection[0] + this_rect.x, intersection[1] + this_rect.y)
        return intersection

    @property
    def default_image(self) -> Surface:
        return self.__default_image.copy()

    @default_image.setter
    def default_image(self, new_image: Surface) -> None:
        center: Tuple[float, float] = self.center
        self.__default_image = new_image.copy()
        self.apply_rotation_scale()
        self.center = center

    @property
    def image(self) -> Surface:
        return self.__image.copy()

    @property
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
    __T = TypeVar("__T", bound="AnimatedSprite")

    def __init__(self, image: Surface, *images: Surface, mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD) -> None:
        super().__init__(image=image, mask_threshold=mask_threshold)
        self.__list: List[Surface] = [self.default_image, *(i.convert_alpha() for i in images)]
        self.__sprite_idx: int = 0
        self.__clock: Clock = Clock()
        self.__wait_time: float = 10
        self.__animation: bool = False
        self.__loop: bool = False

    @classmethod
    def from_iterable(cls: Type[__T], iterable: Iterable[Surface], *, mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD) -> __T:
        return cls(*iterable, mask_threshold=mask_threshold)

    @classmethod
    def from_spritesheet(
        cls: Type[__T], img: Surface, rect_list: List[Rect], *, mask_threshold: int = Sprite.DEFAULT_MASK_THRESHOLD
    ) -> __T:
        return cls.from_iterable((img.subsurface(rect) for rect in rect_list), mask_threshold=mask_threshold)

    def update(self, *args: Any, **kwargs: Any) -> None:
        if self.is_sprite_animating() and self.__clock.elapsed_time(self.__wait_time):
            self.__sprite_idx = sprite_idx = (self.__sprite_idx + 1) % len(self.__list)
            self.default_image = self.__list[sprite_idx]
            if sprite_idx == 0 and not self.__loop:
                self.stop_sprite_animation(reset=True)
        super().update(*args, **kwargs)

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


class SpriteGroup(DrawableGroup):
    def __init__(self, *objects: Sprite, **kwargs: Any) -> None:
        super().__init__(*objects, **kwargs)

    def __iter__(self) -> Iterator[Sprite]:
        return super().__iter__()  # type: ignore[return-value]

    @overload
    def __getitem__(self, index: int) -> Sprite:
        ...

    @overload
    def __getitem__(self, index: slice) -> Sequence[Sprite]:
        ...

    def __getitem__(self, index: Union[int, slice]) -> Union[Sprite, Sequence[Sprite]]:
        return super().__getitem__(index)  # type: ignore[return-value]

    def __reversed__(self) -> Iterator[Sprite]:
        return super().__reversed__()  # type: ignore[return-value]

    def add(self, *objects: Sprite) -> None:  # type: ignore[override]
        if any(not isinstance(obj, Sprite) for obj in objects):
            raise TypeError("SpriteGroup only accepts Sprite objects")
        return super().add(*objects)

    def remove(self, *objects: Sprite) -> None:  # type: ignore[override]
        return super().remove(*objects)

    def pop(self, index: int = -1) -> Sprite:
        return super().pop(index=index)  # type: ignore[return-value]


class LayeredSpriteGroup(SpriteGroup, LayeredGroup):
    def __init__(self, *objects: Sprite, default_layer: int = 0, **kwargs: Any) -> None:
        super().__init__(*objects, default_layer=default_layer, **kwargs)

    def add(self, *objects: Sprite, layer: Optional[int] = None) -> None:  # type: ignore[override]
        if any(not isinstance(obj, Sprite) for obj in objects):
            raise TypeError("SpriteGroup only accepts Sprite objects")
        return LayeredGroup.add(self, *objects, layer=layer)

    def remove(self, *objects: Sprite) -> None:  # type: ignore[override]
        return super().remove(*objects)

    def get_layer(self, obj: Sprite) -> int:  # type: ignore[override]
        return super().get_layer(obj)

    def change_layer(self, obj: Sprite, layer: int) -> None:  # type: ignore[override]
        return super().change_layer(obj, layer)

    def get_top_drawable(self) -> Sprite:
        return super().get_top_drawable()  # type: ignore[return-value]

    def get_bottom_drawable(self) -> Sprite:
        return super().get_bottom_drawable()  # type: ignore[return-value]

    def move_to_front(self, obj: Sprite) -> None:  # type: ignore[override]
        return super().move_to_front(obj)

    def move_to_back(self, obj: Sprite) -> None:  # type: ignore[override]
        return super().move_to_back(obj)

    def get_from_layer(self, layer: int) -> Sequence[Sprite]:
        return super().get_from_layer(layer)  # type: ignore[return-value]

    def remove_from_layer(self, layer: int) -> Sequence[Sprite]:
        return super().remove_from_layer(layer)  # type: ignore[return-value]
