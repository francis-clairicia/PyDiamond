# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Dict, Iterator, List, Optional, Tuple, TypeVar, Union
from functools import wraps

import pygame
from pygame.surface import Surface
from pygame.rect import Rect
from pygame.math import Vector2

from .theme import MetaThemedObject, ThemedObject, abstract_theme_class
from .clock import Clock
from .scene import Scene

if TYPE_CHECKING:
    from .window import Window, WindowCallback

__all__ = ["MetaDrawable", "Drawable", "MetaThemedDrawable", "ThemedDrawable"]


def _draw_decorator(func: Callable[[Drawable, Surface], None]) -> Callable[[Drawable, Surface], None]:
    @wraps(func)
    def wrapper(self: Drawable, surface: Surface) -> None:
        if self.is_shown():
            func(self, surface)

    return wrapper


def _can_apply_decorator(func: Callable[..., Any]) -> bool:
    return not getattr(func, "__isabstractmethod__", False)


class MetaDrawable(ABCMeta):
    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> MetaDrawable:
        if "copy" not in namespace:
            namespace["copy"] = Drawable.copy

        draw_method: Optional[Callable[[Drawable, Surface], None]] = namespace.get("draw_onto")
        if callable(draw_method) and _can_apply_decorator(draw_method):
            namespace["draw_onto"] = _draw_decorator(draw_method)

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class Drawable(metaclass=MetaDrawable):
    __DrawableType = TypeVar("__DrawableType", bound="Drawable")

    def __init__(self) -> None:
        self.__x: float = 0
        self.__y: float = 0
        self.__angle: float = 0
        self.__scale: float = 1
        self.__draw: bool = True
        self.__animation: _Animation = _Animation(self)

    @abstractmethod
    def draw_onto(self, surface: Surface) -> None:
        raise NotImplementedError

    @abstractmethod
    def copy(self: __DrawableType) -> __DrawableType:
        raise NotImplementedError

    def deep_copy(self: __DrawableType) -> __DrawableType:
        copy_self: Drawable.__DrawableType = self.copy()
        copy_self.scale = self.scale
        copy_self.angle = self.angle
        copy_self.center = self.center
        return copy_self

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)

    def set_visibility(self, status: bool) -> None:
        self.__draw = bool(status)

    def is_shown(self) -> bool:
        return self.__draw

    def set_position(self, **position: Union[float, Tuple[float, float]]) -> None:
        all_valid_positions: Tuple[str, ...] = (
            "x",
            "y",
            "left",
            "right",
            "top",
            "bottom",
            "center",
            "centerx",
            "centery",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
            "midtop",
            "midbottom",
            "midleft",
            "midright",
        )
        for name, value in position.items():
            if name not in all_valid_positions:
                raise AttributeError(f"Unknown position attribute {name!r}")
            setattr(self, name, value)

    def move(self, dx: float, dy: float) -> None:
        self.x += dx
        self.y += dy

    def translate(self, vector: Union[Vector2, Tuple[float, float]]) -> None:
        self.x += vector[0]
        self.y += vector[1]

    def rotate(self, angle_offset: float, pivot: Optional[Union[Tuple[float, float], Vector2, str]] = None) -> None:
        self.set_rotation(self.__angle + angle_offset, pivot=pivot)

    def set_rotation(self, angle: float, pivot: Optional[Union[Tuple[float, float], Vector2, str]] = None) -> None:
        angle %= 360
        if angle < 0:
            angle += 360
        if self.angle == angle:
            return
        center: Vector2 = Vector2(self.center)  # type: ignore[arg-type]
        former_angle: float = self.__angle
        self.__angle = angle
        try:
            self._apply_rotation_scale()
        except NotImplementedError:
            self.__angle = 0
            raise
        except pygame.error:
            pass
        if pivot is None:
            pivot = center
        elif isinstance(pivot, str):
            pivot = getattr(self, pivot)
            if not isinstance(pivot, tuple) or len(pivot) != 2:
                raise AttributeError(f"Bad pivot attribute: {pivot}")
        pivot = Vector2(pivot)  # type: ignore[arg-type]
        if pivot != center:
            center = pivot + (center - pivot).rotate(-self.__angle + former_angle)
        self.center = center.x, center.y

    def rotate_around_point(self, angle_offset: float, pivot: Union[Tuple[float, float], Vector2, str]) -> None:
        if angle_offset == 0:
            return
        if isinstance(pivot, str):
            pivot = getattr(self, pivot)
            if not isinstance(pivot, tuple) or len(pivot) != 2:
                raise AttributeError(f"Bad pivot attribute: {pivot}")
        pivot = Vector2(pivot)  # type: ignore[arg-type]
        center: Vector2 = Vector2(self.center)  # type: ignore[arg-type]
        if pivot == center:
            return
        center = pivot + (center - pivot).rotate(-angle_offset)
        self.center = center.x, center.y

    def set_scale(self, scale: float) -> None:
        scale = max(scale, 0)
        if self.scale == scale:
            return
        center: Tuple[float, float] = self.center
        self.__scale = scale
        try:
            self._apply_rotation_scale()
        except NotImplementedError:
            self.__scale = 1
            raise
        except pygame.error:
            pass
        self.center = center

    def scale_to_width(self, width: float) -> None:
        w: float = self.get_local_size()[0]
        self.set_scale(width / w)

    def scale_to_height(self, height: float) -> None:
        h: float = self.get_local_size()[1]
        self.set_scale(height / h)

    def scale_to_size(self, size: Tuple[float, float]) -> None:
        w, h = self.get_local_size()
        scale_width: float = size[0] / w
        scale_height: float = size[1] / h
        self.set_scale(min(scale_width, scale_height))

    def set_min_width(self, width: float) -> None:
        if self.width < width:
            self.scale_to_width(width)

    def set_max_width(self, width: float) -> None:
        if self.width > width:
            self.scale_to_width(width)

    def set_min_height(self, height: float) -> None:
        if self.height < height:
            self.scale_to_height(height)

    def set_max_height(self, height: float) -> None:
        if self.height > height:
            self.scale_to_height(height)

    def set_min_size(self, size: Tuple[float, float]) -> None:
        if self.width < size[0] or self.height < size[1]:
            self.scale_to_size(size)

    def set_max_size(self, size: Tuple[float, float]) -> None:
        if self.width > size[0] or self.height > size[1]:
            self.scale_to_size(size)

    def _apply_rotation_scale(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_local_size(self) -> Tuple[float, float]:
        raise NotImplementedError

    def get_local_width(self) -> float:
        return self.get_local_size()[0]

    def get_local_height(self) -> float:
        return self.get_local_size()[1]

    def get_size(self) -> Tuple[float, float]:
        return self.get_area()

    def get_area(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> Tuple[float, float]:
        if not apply_scale and not apply_rotation:
            return self.get_local_size()

        scale: float = self.__scale
        angle: float = self.__angle
        w, h = self.get_local_size()
        if apply_scale:
            w *= scale
            h *= scale
        if not apply_rotation or angle == 0 or angle == 180:
            return (w, h)
        if angle == 90 or angle == 270:
            return (h, w)

        center: Vector2 = Vector2(w / 2, h / 2)
        corners: List[Vector2] = [Vector2(0, 0), Vector2(w, 0), Vector2(w, h), Vector2(0, h)]
        all_points: List[Vector2] = [center + (point - center).rotate(-angle) for point in corners]
        left: float = min((point.x for point in all_points), default=0)
        right: float = max((point.x for point in all_points), default=0)
        top: float = min((point.y for point in all_points), default=0)
        bottom: float = max((point.y for point in all_points), default=0)
        return (right - left, bottom - top)

    def get_width(self) -> float:
        return self.get_size()[0]

    def get_height(self) -> float:
        return self.get_size()[1]

    def get_local_rect(self, **kwargs: Union[float, Tuple[float, float]]) -> Rect:
        r: Rect = Rect((0, 0), self.get_local_size())
        for name, value in kwargs.items():
            if not hasattr(r, name):
                raise AttributeError(f"{type(r).__name__!r} has no attribute {name!r}")
            setattr(r, name, value)
        return r

    def get_rect(self, **kwargs: Union[float, Tuple[float, float]]) -> Rect:
        r: Rect = self.rect
        for name, value in kwargs.items():
            if not hasattr(r, name):
                raise AttributeError(f"{type(r).__name__!r} has no attribute {name!r}")
            setattr(r, name, value)
        return r

    @property
    def animation(self) -> _Animation:
        return self.__animation

    @property
    def angle(self) -> float:
        return self.__angle

    @angle.setter
    def angle(self, angle: float) -> None:
        self.set_rotation(angle)

    @property
    def scale(self) -> float:
        return self.__scale

    @scale.setter
    def scale(self, scale: float) -> None:
        self.set_scale(scale)

    @property
    def rect(self) -> Rect:
        return Rect(self.topleft, self.get_size())

    @property
    def x(self) -> float:
        return self.__x

    @x.setter
    def x(self, x: float) -> None:
        self.__x = x

    @property
    def y(self) -> float:
        return self.__y

    @y.setter
    def y(self, y: float) -> None:
        self.__y = y

    @property
    def size(self) -> Tuple[float, float]:
        return self.get_size()

    @size.setter
    def size(self, size: Tuple[float, float]) -> None:
        self.scale_to_size(size)

    @property
    def width(self) -> float:
        return self.get_size()[0]

    @width.setter
    def width(self, width: float) -> None:
        self.scale_to_width(width)

    @property
    def height(self) -> float:
        return self.get_size()[1]

    @height.setter
    def height(self, height: float) -> None:
        self.scale_to_height(height)

    @property
    def left(self) -> float:
        return self.x

    @left.setter
    def left(self, left: float) -> None:
        self.x = left

    @property
    def right(self) -> float:
        return self.x + self.width

    @right.setter
    def right(self, right: float) -> None:
        self.x = right - self.width

    @property
    def top(self) -> float:
        return self.y

    @top.setter
    def top(self, top: float) -> None:
        self.y = top

    @property
    def bottom(self) -> float:
        return self.y + self.height

    @bottom.setter
    def bottom(self, bottom: float) -> None:
        self.y = bottom - self.height

    @property
    def center(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + (w / 2), self.y + (h / 2))

    @center.setter
    def center(self, center: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = center[0] - (w / 2)
        self.y = center[1] - (h / 2)

    @property
    def centerx(self) -> float:
        return self.x + (self.width / 2)

    @centerx.setter
    def centerx(self, centerx: float) -> None:
        self.x = centerx - (self.width / 2)

    @property
    def centery(self) -> float:
        return self.y + (self.height / 2)

    @centery.setter
    def centery(self, centery: float) -> None:
        self.y = centery - (self.height / 2)

    @property
    def topleft(self) -> Tuple[float, float]:
        return (self.x, self.y)

    @topleft.setter
    def topleft(self, topleft: Tuple[float, float]) -> None:
        self.x = topleft[0]
        self.y = topleft[1]

    @property
    def topright(self) -> Tuple[float, float]:
        return (self.x + self.width, self.y)

    @topright.setter
    def topright(self, topright: Tuple[float, float]) -> None:
        self.x = topright[0] - self.width
        self.y = topright[1]

    @property
    def bottomleft(self) -> Tuple[float, float]:
        return (self.x, self.y + self.height)

    @bottomleft.setter
    def bottomleft(self, bottomleft: Tuple[float, float]) -> None:
        self.x = bottomleft[0]
        self.y = bottomleft[1] - self.height

    @property
    def bottomright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + w, self.y + h)

    @bottomright.setter
    def bottomright(self, bottomright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = bottomright[0] - w
        self.y = bottomright[1] - h

    @property
    def midtop(self) -> Tuple[float, float]:
        return (self.x + (self.width / 2), self.y)

    @midtop.setter
    def midtop(self, midtop: Tuple[float, float]) -> None:
        self.x = midtop[0] - (self.width / 2)
        self.y = midtop[1]

    @property
    def midbottom(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + (w / 2), self.y + h)

    @midbottom.setter
    def midbottom(self, midbottom: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = midbottom[0] - (w / 2)
        self.y = midbottom[1] - h

    @property
    def midleft(self) -> Tuple[float, float]:
        return (self.x, self.y + (self.height / 2))

    @midleft.setter
    def midleft(self, midleft: Tuple[float, float]) -> None:
        self.x = midleft[0]
        self.y = midleft[1] - (self.height / 2)

    @property
    def midright(self) -> Tuple[float, float]:
        w, h = self.get_size()
        return (self.x + w, self.y + (h / 2))

    @midright.setter
    def midright(self, midright: Tuple[float, float]) -> None:
        w, h = self.get_size()
        self.x = midright[0] - w
        self.y = midright[1] - (h / 2)


class MetaThemedDrawable(MetaDrawable, MetaThemedObject):
    pass


@abstract_theme_class
class ThemedDrawable(Drawable, ThemedObject, metaclass=MetaThemedDrawable):
    pass


class _AbstractAnimationClass(metaclass=ABCMeta):
    def __init__(self, drawable: Drawable, milliseconds: float):
        self.__drawable: Drawable = drawable
        self.__clock: Clock = Clock()
        self.__milliseconds: float = max(milliseconds, 0)
        self.__animation_started: bool = True

    def started(self) -> bool:
        return self.__milliseconds > 0 and self.__animation_started

    def stop(self) -> None:
        self.__animation_started = False
        try:
            self.default()
        except NotImplementedError:
            pass

    def ready(self) -> bool:
        if not self.started():
            return False
        return self.__clock.elapsed_time(self.__milliseconds)

    @abstractmethod
    def __call__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def default(self) -> None:
        raise NotImplementedError

    @property
    def drawable(self) -> Drawable:
        return self.__drawable

    @property
    def milliseconds(self) -> float:
        return self.__milliseconds


class _AnimationSetPosition(_AbstractAnimationClass):
    def __init__(
        self, drawable: Drawable, milliseconds: float, speed: float, **position: Union[float, Tuple[float, float]]
    ) -> None:
        super().__init__(drawable, milliseconds)
        self.__position: Dict[str, Union[float, Tuple[float, float]]] = position
        self.__speed: float = speed

    def started(self) -> bool:
        return super().started() and self.__speed > 0

    def __call__(self) -> None:
        if not self.ready():
            return
        projection = self.drawable.get_rect(**self.__position)
        direction = Vector2(projection.center) - Vector2(self.drawable.center)  # type: ignore[arg-type]
        length = direction.length()
        if length > 0 and length > self.__speed:
            direction.scale_to_length(self.__speed)
            self.drawable.translate(direction)
        else:
            self.stop()

    def default(self) -> None:
        self.drawable.set_position(**self.__position)


class _AnimationMove(_AbstractAnimationClass):
    def __init__(
        self, drawable: Drawable, translation: Union[Vector2, Tuple[float, float]], milliseconds: float, speed: float
    ) -> None:
        super().__init__(drawable, milliseconds)
        self.__vector: Vector2 = Vector2(translation)  # type: ignore[arg-type]
        self.__speed: float = speed
        self.__traveled: float = 0
        self.__end: bool = False

    def started(self) -> bool:
        return super().started() and self.__speed > 0 and self.__vector != Vector2(0, 0)

    def __call__(self) -> None:
        if not self.ready():
            return
        direction = self.__vector.xy
        if direction.length() > self.__traveled + self.__speed:
            self.__traveled += self.__speed
            direction.scale_to_length(self.__speed)
            self.drawable.translate(direction)
        else:
            self.stop()

    def default(self) -> None:
        if not self.__end:
            self.__vector.scale_to_length(abs(self.__vector.length() - self.__traveled))
            self.drawable.translate(self.__vector)
            self.__vector = Vector2(0, 0)
            self.__end = True


class _AnimationRotation(_AbstractAnimationClass):
    def __init__(
        self,
        drawable: Drawable,
        milliseconds: float,
        angle: float,
        offset: float,
        pivot: Union[Vector2, Tuple[float, float], str, None],
    ):
        super().__init__(drawable, milliseconds)
        self.__angle: float = abs(angle)
        self.__sign: int = int(angle // abs(angle)) if angle != 0 and offset > 0 else 0
        self.__offset: float = offset * self.__sign if offset > 0 else 0
        self.__actual_angle: float = 0
        self.__pivot: Union[Vector2, Tuple[float, float], None]
        if isinstance(pivot, str):
            pivot = getattr(self.drawable, pivot)
            if not isinstance(pivot, tuple) or len(pivot) != 2:
                raise AttributeError(f"Bad pivot attribute: {pivot}")
        self.__pivot = pivot

    def started(self) -> bool:
        return super().started() and self.__angle != 0 and self.__offset != 0

    def __call__(self) -> None:
        if not self.ready():
            return
        if self.__actual_angle + abs(self.__offset) < self.__angle:
            self.__actual_angle += abs(self.__offset)
            self.drawable.rotate(self.__offset, self.__pivot)
        else:
            self.stop()

    def default(self) -> None:
        if self.__actual_angle != self.__angle:
            self.drawable.rotate(abs(self.__angle - self.__actual_angle) * self.__sign, self.__pivot)
            self.__actual_angle = self.__angle


class _AnimationScaleSize(_AbstractAnimationClass):
    def __init__(self, drawable: Drawable, milliseconds: float, field: str, size: float, offset: float):
        super().__init__(drawable, milliseconds)
        self.__size: float = max(size, 0)
        self.__field: str = field
        self.__offset: float
        self.__sign: int
        self.__actual_size = self.get_drawable_size()
        size_offset = self.__size - self.__actual_size
        if offset == 0 or size_offset == 0:
            self.__offset = self.__sign = 0
        else:
            self.__sign = int(size_offset // abs(size_offset))
            self.__offset = abs(offset) * self.__sign

    def started(self) -> bool:
        return super().started() and self.__offset != 0

    def __call__(self) -> None:
        if not self.ready():
            return
        self.__actual_size += self.__offset
        if (self.__offset < 0 and self.__actual_size > self.__size) or (self.__offset > 0 and self.__actual_size < self.__size):
            self.set_drawable_size(self.__actual_size)
        else:
            self.stop()

    def get_drawable_size(self) -> float:
        return float(getattr(self.drawable, self.__field))

    def set_drawable_size(self, value: float) -> None:
        setattr(self.drawable, self.__field, value)

    def default(self) -> None:
        self.set_drawable_size(self.__size)


class _AnimationScaleWidth(_AnimationScaleSize):
    def __init__(self, drawable: Drawable, milliseconds: float, width: float, offset: float) -> None:
        super().__init__(drawable, milliseconds, "width", width, offset)


class _AnimationScaleHeight(_AnimationScaleSize):
    def __init__(self, drawable: Drawable, milliseconds: float, height: float, offset: float) -> None:
        super().__init__(drawable, milliseconds, "height", height, offset)


class _Animation:
    def __init__(self, drawable: Drawable):
        self.__drawable: Drawable = drawable
        self.__animations_order: List[str] = ["scale_width", "scale_height", "rotate", "rotate_point", "move"]
        self.__animations: Dict[str, Optional[_AbstractAnimationClass]] = dict.fromkeys(self.__animations_order)
        self.__window_callback: Optional[WindowCallback] = None
        self.__save_window_callback: Optional[WindowCallback] = None
        self.__save_animations: Optional[Dict[str, Optional[_AbstractAnimationClass]]] = None

    def register_position(
        self, speed: float = 1, milliseconds: float = 10, **position: Union[float, Tuple[float, float]]
    ) -> _Animation:
        self.__animations["move"] = _AnimationSetPosition(self.__drawable, milliseconds, speed, **position)
        return self

    def register_translation(
        self, translation: Union[Vector2, Tuple[float, float]], speed: float = 1, milliseconds: float = 10
    ) -> _Animation:
        self.__animations["move"] = _AnimationMove(self.__drawable, translation, milliseconds, speed)
        return self

    def register_rotation(
        self,
        angle: float,
        offset: float = 1,
        pivot: Optional[Union[Vector2, Tuple[float, float], str]] = None,
        milliseconds: float = 10,
    ) -> _Animation:
        animation = "rotate" if pivot is None else "rotate_point"
        self.__animations[animation] = _AnimationRotation(self.__drawable, milliseconds, angle, offset, pivot)
        return self

    def register_rotation_set(
        self,
        angle: float,
        offset: float = 1,
        pivot: Optional[Union[Vector2, Tuple[float, float], str]] = None,
        milliseconds: float = 10,
    ) -> _Animation:
        angle %= 360
        if angle < 0:
            angle += 360
        if offset != 0:
            if self.__drawable.angle > angle:
                if offset > 0:
                    angle += 360
            else:
                if offset < 0:
                    angle -= 360
            angle -= self.__drawable.angle
        return self.register_rotation(angle, abs(offset), pivot, milliseconds)

    def register_width_offset(self, width_offset: float, step: float = 1, milliseconds: float = 10) -> _Animation:
        width: float = self.__drawable.width + width_offset
        return self.register_width_set(width, max(step, 0), milliseconds)

    def register_width_set(self, width: float, offset: float = 1, milliseconds: float = 10) -> _Animation:
        self.__animations.pop("scale_height", None)
        self.__animations["scale_width"] = _AnimationScaleWidth(self.__drawable, milliseconds, width, offset)
        return self

    def register_height_offset(self, height_offset: float, step: float = 1, milliseconds: float = 10) -> _Animation:
        height: float = self.__drawable.height + height_offset
        return self.register_height_set(height, max(step, 0), milliseconds)

    def register_height_set(self, height: float, offset: float = 1, milliseconds: float = 10) -> _Animation:
        self.__animations.pop("scale_width", None)
        self.__animations["scale_height"] = _AnimationScaleHeight(self.__drawable, milliseconds, height, offset)
        return self

    def start(self, master: Union[Window, Scene], at_every_frame: Optional[Callable[[], None]] = None) -> None:
        scene: Optional[Scene] = None
        if isinstance(master, Scene):
            scene = master
            if not scene.looping():
                return
            master = master.window
        while self.started():
            self.__animate(at_every_frame)
            if scene is not None and not scene.looping():
                break
            master.handle_events()
            master.draw_and_refresh()
        self.__animate(at_every_frame)
        master.draw_and_refresh()
        self.__clear()

    def start_in_background(
        self,
        master: Union[Window, Scene],
        at_every_frame: Optional[Callable[[], None]] = None,
        after_animation: Optional[Callable[[], None]] = None,
    ) -> None:
        if self.__window_callback is not None:
            self.__window_callback.kill()
            self.__window_callback = None
        self.__start_window_callback(master, at_every_frame, after_animation)

    def started(self) -> bool:
        return any(animation.started() for animation in self.__iter_animations())

    def stop_background(self) -> None:
        if self.__window_callback is not None:
            self.__window_callback.kill()
            self.__save_window_callback = self.__window_callback
            self.__window_callback = None
            self.__save_animations = self.__animations.copy()
            self.__clear()

    def restart_background(self) -> None:
        if self.__window_callback is None and self.__save_window_callback is not None:
            if self.__save_animations is not None:
                self.__animations = self.__save_animations.copy()
            self.__save_window_callback()
            self.__save_window_callback = None

    def is_set(self, animation: str) -> bool:
        return self.__animations.get(animation) is not None

    def __iter_animations(self) -> Iterator[_AbstractAnimationClass]:
        for animation_name in self.__animations_order:
            animation: Optional[_AbstractAnimationClass] = self.__animations.get(animation_name)
            if animation is not None:
                yield animation

    def __clear(self) -> None:
        for key in self.__animations:
            self.__animations[key] = None

    def __animate(self, at_every_frame: Optional[Callable[[], None]]) -> None:
        for animation in self.__iter_animations():
            try:
                if animation.started():
                    animation()
                else:
                    animation.default()
            except NotImplementedError:
                if animation.started():
                    animation.stop()
                continue
        if callable(at_every_frame):
            at_every_frame()

    def __start_window_callback(
        self,
        master: Union[Window, Scene],
        at_every_frame: Optional[Callable[[], None]],
        after_animation: Optional[Callable[[], None]],
    ) -> None:
        self.__animate(at_every_frame)
        if self.started():
            self.__window_callback = master.after(
                0,
                self.__start_window_callback,
                master=master,
                at_every_frame=at_every_frame,
                after_animation=after_animation,
            )
        else:
            self.__animate(at_every_frame)
            self.__clear()
            if self.__window_callback is not None:
                self.__window_callback.kill()
                self.__window_callback = None
            self.__save_animations = self.__save_window_callback = None
            if callable(after_animation):
                after_animation()
