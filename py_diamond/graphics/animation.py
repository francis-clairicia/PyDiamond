# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Animation module"""

from __future__ import annotations

__all__ = ["TransformAnimation"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Callable, Iterator, Literal, NamedTuple, TypeAlias, TypeVar

from ..math import Vector2
from ..window.time import Time

if TYPE_CHECKING:
    from ..window.scene import Scene, SceneWindow
    from .transformable import Transformable

_AnimationType: TypeAlias = Literal["move", "rotate", "rotate_point", "scale"]


class TransformAnimation:

    __slots__ = (
        "__transformable",
        "__animations_order",
        "__animations",
        "__actual_state",
        "__previous_state",
        "__on_stop",
        "__wait",
    )

    def __init__(self, transformable: Transformable) -> None:
        self.__transformable: Transformable = transformable
        self.__animations_order: list[_AnimationType] = ["scale", "rotate", "rotate_point", "move"]
        self.__animations: dict[_AnimationType, _AbstractAnimationClass] = {}
        self.__actual_state: _TransformState | None = None
        self.__previous_state: _TransformState | None = None
        self.__on_stop: Callable[[], None] | None = None
        self.__wait: bool = True

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="TransformAnimation")

    def smooth_set_position(self: __Self, speed: float = 100, **position: float | tuple[float, float]) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["move"] = _AnimationSetPosition(transformable, speed, position)
        return self

    def smooth_translation(self: __Self, translation: Vector2 | tuple[float, float], speed: float = 100) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["move"] = _AnimationMove(transformable, speed, translation)
        return self

    def infinite_translation(self: __Self, direction: Vector2 | tuple[float, float], speed: float = 100) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["move"] = _AnimationInfiniteMove(transformable, speed, direction)
        return self

    def smooth_set_angle(
        self: __Self,
        angle: float,
        speed: float = 100,
        *,
        pivot: str | tuple[float, float] | Vector2 | None = None,
        counter_clockwise: bool = True,
    ) -> __Self:
        transformable: Transformable = self.__transformable
        if pivot is not None:
            self.__animations.pop("rotate_point", None)
        self.__animations["rotate"] = _AnimationSetRotation(transformable, angle, speed, pivot, counter_clockwise)
        return self

    def smooth_rotation(
        self: __Self,
        angle: float,
        speed: float = 100,
    ) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["rotate"] = _AnimationRotation(transformable, angle, speed)
        return self

    def smooth_rotation_around_point(
        self: __Self,
        angle: float,
        pivot: str | tuple[float, float] | Vector2,
        speed: float = 100,
        *,
        rotate_object: bool = False,
    ) -> __Self:
        transformable: Transformable = self.__transformable
        if rotate_object:
            self.__animations.pop("rotate", None)
        self.__animations["rotate_point"] = _AnimationRotationAroundPoint(transformable, angle, speed, pivot, rotate_object)
        return self

    def infinite_rotation(self: __Self, speed: float = 100, *, counter_clockwise: bool = True) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["rotate"] = _AnimationInfiniteRotate(transformable, speed, counter_clockwise)
        return self

    def infinite_rotation_around_point(
        self: __Self,
        pivot: str | tuple[float, float] | Vector2,
        speed: float = 100,
        *,
        counter_clockwise: bool = True,
        rotate_object: bool = False,
    ) -> __Self:
        transformable: Transformable = self.__transformable
        if rotate_object:
            self.__animations.pop("rotate", None)
        self.__animations["rotate_point"] = _AnimationInfiniteRotateAroundPoint(
            transformable, speed, pivot, counter_clockwise, rotate_object
        )
        return self

    def smooth_scale_to_width(self: __Self, width: float, speed: float = 100) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["scale"] = _AnimationSetSize(transformable, width, speed, "width")
        return self

    def smooth_scale_to_height(self: __Self, height: float, speed: float = 100) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["scale"] = _AnimationSetSize(transformable, height, speed, "height")
        return self

    def smooth_width_growth(self: __Self, width_offset: float, speed: float = 100) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["scale"] = _AnimationSizeGrowth(transformable, width_offset, speed, "width")
        return self

    def smooth_height_growth(self: __Self, height_offset: float, speed: float = 100) -> __Self:
        transformable: Transformable = self.__transformable
        self.__animations["scale"] = _AnimationSizeGrowth(transformable, height_offset, speed, "height")
        return self

    def fixed_update(self, *, use_of_linear_interpolation: bool = False) -> None:
        if not self.started():
            return
        transformable: Transformable = self.__transformable
        self.__previous_state = state = self.__actual_state
        if use_of_linear_interpolation and state is not None:
            state.apply_on(transformable, apply_rotation_scale=False)
        else:
            self.__previous_state = self.__actual_state = None
        for animation in self.__iter_animations():
            if animation.started():
                animation.fixed_update(apply_rotation_scale=not use_of_linear_interpolation)
            else:
                animation.default()
        if self.has_animation_started():
            if use_of_linear_interpolation:
                self.__actual_state = _TransformState.from_transformable(transformable)
        else:
            on_stop = self.__on_stop
            if on_stop:
                on_stop()
                self.__on_stop = None

    def set_interpolation(self, interpolation: float) -> None:
        if not self.started() or not self.__previous_state or not self.__actual_state:
            return
        interpolation = min(max(interpolation, 0), 1)
        transformable: Transformable = self.__transformable
        previous: _TransformState = self.__previous_state
        actual: _TransformState = self.__actual_state
        previous.interpolate(actual, interpolation).apply_on(transformable)

    def has_animation_started(self) -> bool:
        return any(animation.started() for animation in self.__animations.values())

    def started(self) -> bool:
        return not self.__wait and self.has_animation_started()

    def on_stop(self, callback: Callable[[], None] | None) -> None:
        if not (callback is None or callable(callback)):
            raise TypeError("Invalid arguments")
        self.__on_stop = callback

    def start(self) -> None:
        self.__wait = False

    def pause(self) -> None:
        self.__wait = True

    def clear(self, *, pause: bool = False) -> None:
        if pause:
            self.pause()
        self.__animations.clear()
        self.__actual_state = self.__previous_state = None

    def wait_until_finish(self, scene: Scene) -> None:
        if not scene.looping():
            return
        window: SceneWindow = scene.window
        self.__on_stop = None
        self.start()
        with window.block_all_events_context(), window.no_window_callback_processing():
            while window.looping() and self.has_animation_started():
                for _ in window.process_events():
                    pass
                window._fixed_updates_call(lambda: self.fixed_update(use_of_linear_interpolation=True))
                window._interpolation_updates_call(self.set_interpolation)
                window.render_scene()
                window.refresh()

    def __iter_animations(self) -> Iterator[_AbstractAnimationClass]:
        for animation_name in self.__animations_order:
            animation: _AbstractAnimationClass | None = self.__animations.get(animation_name)
            if animation is not None:
                yield animation
        if not self.has_animation_started():
            self.clear(pause=False)


class _TransformState(NamedTuple):
    angle: float
    scale: float
    center: tuple[float, float]

    @staticmethod
    def from_transformable(t: Transformable) -> _TransformState:
        return _TransformState(t.angle, t.scale, t.center)

    def interpolate(self, other: _TransformState, alpha: float) -> _TransformState:
        angle = self.angle_interpolation(self.angle, other.angle, alpha)
        scale = self.scale * (1.0 - alpha) + other.scale * alpha
        center = Vector2(self.center).lerp(Vector2(other.center), alpha)
        return _TransformState(angle, scale, (center.x, center.y))

    @staticmethod
    def angle_interpolation(start: float, end: float, alpha: float) -> float:
        shortest_angle = ((end - start) + 180) % 360 - 180
        return (start + shortest_angle * alpha) % 360

    def apply_on(self, t: Transformable, *, apply_rotation_scale: bool = True) -> None:
        t.set_rotation(self.angle, apply=False)
        t.set_scale(self.scale, apply=False)
        if apply_rotation_scale:
            t.apply_rotation_scale()
        t.center = self.center


class _AbstractAnimationClass(metaclass=ABCMeta):

    __slots__ = (
        "__transformable",
        "__animation_started",
        "__speed",
    )

    def __init__(self, transformable: Transformable, speed: float) -> None:
        self.__transformable: Transformable = transformable
        self.__animation_started: bool = True
        self.__speed: float = speed

    def started(self) -> bool:
        return self.__animation_started and self.__speed > 0

    def stop(self) -> None:
        self.__animation_started = False
        self.__speed = 0
        self.default()

    @abstractmethod
    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def default(self) -> None:
        raise NotImplementedError

    @property
    def transformable(self) -> Transformable:
        return self.__transformable

    @property
    def speed(self) -> float:
        return self.__speed * Time.fixed_delta()


class _AnimationSetPosition(_AbstractAnimationClass):

    __slots__ = ("__position",)

    def __init__(self, transformable: Transformable, speed: float, position: dict[str, float | tuple[float, float]]) -> None:
        super().__init__(transformable, speed)
        self.__position: dict[str, float | tuple[float, float]] = position

    def started(self) -> bool:
        return super().started() and len(self.__position) > 0

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable = self.transformable
        actual_position = Vector2(transformable.center)
        projection = transformable.get_rect(**self.__position)
        direction = Vector2(projection.center) - actual_position
        speed = self.speed
        length = direction.length()
        if length > 0 and length > speed:
            direction.scale_to_length(speed)
            transformable.translate(direction)
        else:
            self.stop()

    def default(self) -> None:
        if self.__position:
            self.transformable.set_position(**self.__position)
            self.__position.clear()


class _AnimationMove(_AbstractAnimationClass):

    __slots__ = ("__vector", "__traveled")

    def __init__(self, transformable: Transformable, speed: float, translation: Vector2 | tuple[float, float]) -> None:
        super().__init__(transformable, speed)
        self.__vector: Vector2 = Vector2(translation)
        self.__traveled: float = 0

    def started(self) -> bool:
        return super().started() and self.__vector.length_squared() > 0

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable = self.transformable
        direction = self.__vector.xy
        length: float = direction.length()
        speed: float = self.speed
        traveled: float = self.__traveled
        offset: float = min(length - traveled, speed)
        if offset == 0:
            return self.stop()
        direction.scale_to_length(offset)
        transformable.translate(direction)
        self.__traveled += offset

    def default(self) -> None:
        length: float = self.__vector.length()
        if length:
            self.__traveled = length
            self.__vector = Vector2(0, 0)


class _AnimationInfiniteMove(_AbstractAnimationClass):

    __slots__ = ("__vector",)

    def __init__(self, transformable: Transformable, speed: float, direction: Vector2 | tuple[float, float]) -> None:
        super().__init__(transformable, speed)
        self.__vector: Vector2 = Vector2(direction)
        if self.__vector.length_squared() > 0:
            self.__vector.normalize_ip()

    def started(self) -> bool:
        return super().started() and self.__vector.length_squared() > 0

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable = self.transformable
        direction = self.__vector.xy
        speed = self.speed
        direction.scale_to_length(speed)
        transformable.translate(direction)

    def default(self) -> None:
        self.__vector = Vector2(0, 0)


class _AnimationSetRotation(_AbstractAnimationClass):

    __slots__ = ("__angle", "__pivot", "__counter_clockwise")

    def __init__(
        self,
        transformable: Transformable,
        angle: float,
        speed: float,
        pivot: Vector2 | tuple[float, float] | str | None,
        counter_clockwise: bool,
    ) -> None:
        super().__init__(transformable, speed)
        angle %= 360
        self.__angle: float = angle
        self.__pivot: Vector2 | None
        if isinstance(pivot, str):
            pivot = transformable.get_pivot_from_attribute(pivot)
        self.__pivot = Vector2(pivot) if pivot is not None else None
        self.__counter_clockwise: bool = counter_clockwise

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable = self.transformable
        actual_angle: float = transformable.angle
        speed: float = self.speed
        offset: float = speed
        remaining: float
        requested_angle: float = self.__angle
        if not self.__counter_clockwise:
            offset = -offset
            remaining = actual_angle - requested_angle
        else:
            remaining = requested_angle - actual_angle
        if remaining < 0:
            remaining += 360
        if remaining > speed:
            transformable.rotate(offset, self.__pivot, apply=apply_rotation_scale)
        else:
            self.stop()

    def default(self) -> None:
        self.transformable.set_rotation(self.__angle, self.__pivot)


class _AnimationRotation(_AbstractAnimationClass):

    __slots__ = ("__angle", "__orientation", "__actual_angle")

    def __init__(
        self,
        transformable: Transformable,
        angle: float,
        speed: float,
    ) -> None:
        super().__init__(transformable, speed)
        self.__angle: float = abs(angle)
        self.__orientation: int = int(angle // abs(angle)) if angle != 0 and speed > 0 else 0
        self.__actual_angle: float = 0

    def started(self) -> bool:
        return super().started() and self.__angle != 0

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable: Transformable = self.transformable
        actual_angle: float = self.__actual_angle
        angle: float = self.__angle
        speed: float = self.speed
        offset: float = min(angle - actual_angle, speed) * self.__orientation
        if offset == 0:
            return self.stop()
        transformable.rotate(offset, apply=apply_rotation_scale)
        self.__actual_angle += abs(offset)

    def default(self) -> None:
        if self.__angle:
            self.__actual_angle = self.__angle
            self.__angle = 0


class _AnimationInfiniteRotate(_AbstractAnimationClass):

    __slots__ = ("__orientation",)

    def __init__(
        self,
        transformable: Transformable,
        speed: float,
        counter_clockwise: bool,
    ) -> None:
        super().__init__(transformable, speed)
        self.__orientation: int = 1 if counter_clockwise else -1

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable = self.transformable
        offset: float = self.speed * self.__orientation
        transformable.rotate(offset, apply=apply_rotation_scale)

    def default(self) -> None:
        pass


class _AnimationRotationAroundPoint(_AbstractAnimationClass):

    __slots__ = (
        "__angle",
        "__orientation",
        "__actual_angle",
        "__pivot",
        "__rotate_object",
    )

    def __init__(
        self,
        transformable: Transformable,
        angle: float,
        speed: float,
        pivot: Vector2 | tuple[float, float] | str,
        rotate_object: bool,
    ) -> None:
        super().__init__(transformable, speed)
        self.__angle: float = abs(angle)
        self.__orientation: int = int(angle // abs(angle)) if angle != 0 and speed > 0 else 0
        self.__actual_angle: float = 0
        self.__pivot: Vector2
        if isinstance(pivot, str):
            pivot = transformable.get_pivot_from_attribute(pivot)
        self.__pivot = Vector2(pivot)
        self.__rotate_object: bool = rotate_object

    def started(self) -> bool:
        return super().started() and self.__angle != 0

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable: Transformable = self.transformable
        actual_angle: float = self.__actual_angle
        angle: float = self.__angle
        speed: float = self.speed
        offset: float = min(angle - actual_angle, speed) * self.__orientation
        if offset == 0:
            return self.stop()
        if self.__rotate_object:
            transformable.rotate(offset, self.__pivot, apply=apply_rotation_scale)
        else:
            transformable.rotate_around_point(offset, self.__pivot)
        self.__actual_angle += abs(offset)

    def default(self) -> None:
        if self.__angle:
            self.__actual_angle = self.__angle
            self.__angle = 0


class _AnimationInfiniteRotateAroundPoint(_AbstractAnimationClass):

    __slots__ = ("__pivot", "__orientation", "__rotate_object")

    def __init__(
        self,
        transformable: Transformable,
        speed: float,
        pivot: Vector2 | tuple[float, float] | str,
        counter_clockwise: bool,
        rotate_object: bool,
    ) -> None:
        super().__init__(transformable, speed)
        self.__pivot: Vector2
        if isinstance(pivot, str):
            pivot = transformable.get_pivot_from_attribute(pivot)
        self.__pivot = Vector2(pivot)
        self.__orientation: int = 1 if counter_clockwise else -1
        self.__rotate_object: bool = rotate_object

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        transformable = self.transformable
        offset: float = self.speed * self.__orientation
        if self.__rotate_object:
            transformable.rotate(offset, self.__pivot, apply=apply_rotation_scale)
        else:
            transformable.rotate_around_point(offset, self.__pivot)

    def default(self) -> None:
        pass


class _AbstractAnimationScale(_AbstractAnimationClass):

    __slots__ = ("__field",)

    def __init__(self, transformable: Transformable, speed: float, field: Literal["width", "height"]) -> None:
        super().__init__(transformable, speed)
        if field not in ("width", "height"):
            raise ValueError("Invalid arguments")
        self.__field: Literal["width", "height"] = field

    def get_transformable_size(self) -> float:
        area: tuple[float, float] = self.transformable.get_area_size(apply_rotation=False)
        if self.__field == "width":
            return area[0]
        return area[1]

    def set_transformable_size(self, value: float, *, apply_scale: float = True) -> None:
        getattr(self.transformable, f"scale_to_{self.__field}")(value, apply=apply_scale)


class _AnimationSetSize(_AbstractAnimationScale):

    __slots__ = ("__value",)

    def __init__(self, transformable: Transformable, value: float, speed: float, field: Literal["width", "height"]) -> None:
        super().__init__(transformable, speed, field)
        self.__value: float = value

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        speed: float = self.speed
        actual_size: float = self.get_transformable_size()
        requested_size: float = self.__value
        offset: float = speed
        remaining: float
        if actual_size > requested_size:
            offset = -offset
            remaining = actual_size - requested_size
        else:
            remaining = requested_size - actual_size
        if remaining > speed:
            self.set_transformable_size(actual_size + offset, apply_scale=apply_rotation_scale)
        else:
            self.stop()

    def default(self) -> None:
        self.set_transformable_size(self.__value)


class _AnimationSizeGrowth(_AbstractAnimationScale):

    __slots__ = ("__value", "__orientation", "__actual_value")

    def __init__(self, transformable: Transformable, offset: float, speed: float, field: Literal["width", "height"]) -> None:
        super().__init__(transformable, speed, field)
        self.__value: float = abs(offset)
        self.__orientation: int = int(offset // abs(offset)) if offset != 0 and speed > 0 else 0
        self.__actual_value: float = 0

    def started(self) -> bool:
        return super().started() and self.__value != 0

    def fixed_update(self, *, apply_rotation_scale: bool) -> None:
        actual_value: float = self.__actual_value
        value: float = self.__value
        speed: float = self.speed
        offset: float = min(value - actual_value, speed) * self.__orientation
        if offset == 0:
            return self.stop()
        actual_size: float = self.get_transformable_size()
        self.set_transformable_size(actual_size + offset, apply_scale=apply_rotation_scale)
        self.__actual_value += abs(offset)

    def default(self) -> None:
        if self.__value:
            self.__actual_value = self.__value
            self.__value = 0
