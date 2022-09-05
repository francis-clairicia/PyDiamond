# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Animation module"""

from __future__ import annotations

__all__ = ["AnimationInterpolator", "AnimationInterpolatorPool", "BaseAnimation", "MoveAnimation", "TransformAnimation"]

from abc import ABCMeta, abstractmethod
from contextlib import ExitStack, contextmanager
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    Iterator,
    Literal,
    NamedTuple,
    Protocol,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)
from weakref import WeakKeyDictionary, ref as weakref

from ..math import Vector2, angle_interpolation, linear_interpolation
from ..system.object import Object, final
from ..system.time import Time
from ..system.utils.weakref import weakref_unwrap
from .movable import Movable, MovableProxy
from .transformable import Transformable, TransformableProxy

if TYPE_CHECKING:
    from ..window.scene import Scene, SceneWindow


@final
class AnimationInterpolator(Object):
    __slots__ = (
        "__obj",
        "__actual_state",
        "__previous_state",
        "__state_update",
        "__state_factory",
    )

    __cache: WeakKeyDictionary[Movable | Transformable, AnimationInterpolator] = WeakKeyDictionary()

    def __new__(cls, obj: Movable | Transformable) -> AnimationInterpolator:
        if isinstance(obj, (MovableProxy, TransformableProxy)):
            obj = object.__getattribute__(obj, "_object")
        try:
            self = cls.__cache[obj]
        except KeyError:
            cls.__cache[obj] = self = super().__new__(cls)
            self.__internal_init(obj)
        return self

    def __internal_init(self, obj: Movable | Transformable) -> None:
        self.__obj: weakref[Movable | Transformable] = weakref(obj)
        self.__state_factory: type[_ObjectStateProtocol] = _TransformState if isinstance(obj, Transformable) else _MoveState
        self.__actual_state: _ObjectStateProtocol | None = None
        self.__previous_state: _ObjectStateProtocol | None = None
        self.__state_update: bool = False

    @contextmanager
    def fixed_update(self) -> Iterator[None]:
        if self.__state_update:
            yield
            return
        self.__state_update = True
        try:
            obj: Movable | Transformable = weakref_unwrap(self.__obj)
            self.__previous_state = state = self.__actual_state
            if state is not None:
                state.apply_on(obj)
                self.__actual_state = None
            else:
                self.__previous_state = self.__state_factory.from_object(obj)
            yield
            if self.__previous_state is not None:  # reset() was not called
                self.__actual_state = self.__state_factory.from_object(obj)
        finally:
            self.__state_update = False

    def update(self, interpolation: float) -> None:
        if self.__state_update:
            raise RuntimeError("update() during state update")
        previous: _ObjectStateProtocol | None = self.__previous_state
        actual: _ObjectStateProtocol | None = self.__actual_state
        if not previous or not actual:
            return
        interpolation = min(max(interpolation, 0), 1)
        obj: Movable | Transformable = weakref_unwrap(self.__obj)
        previous.interpolate(actual, interpolation, obj)

    def reset(self) -> None:
        self.__actual_state = self.__previous_state = None

    @property
    def object(self) -> Movable:
        return weakref_unwrap(self.__obj)


@final
class AnimationInterpolatorPool(Object):
    __slots__ = ("__interpolators",)

    def __init__(self, *objects: Movable | Transformable) -> None:
        super().__init__()
        self.__interpolators: WeakKeyDictionary[Movable | Transformable, AnimationInterpolator] = WeakKeyDictionary()
        self.add(*objects)

    @contextmanager
    def fixed_update(self) -> Iterator[None]:
        with ExitStack() as stack:
            for interpolator in self.__interpolators.values():
                stack.enter_context(interpolator.fixed_update())
            yield

    def update(self, interpolation: float) -> None:
        for interpolator in self.__interpolators.values():
            interpolator.update(interpolation)

    def reset_all(self) -> None:
        for interpolator in self.__interpolators.values():
            interpolator.reset()

    def add(self, *objects: Movable | Transformable) -> None:
        if not objects:
            return
        interpolators = (AnimationInterpolator(obj) for obj in objects)
        self.__interpolators.update({interpolator.object: interpolator for interpolator in interpolators})

    def remove(self, obj: Movable | Transformable) -> None:
        obj = AnimationInterpolator(obj).object
        del self.__interpolators[obj]


class BaseAnimation(Object):
    __slots__ = (
        "__object",
        "__interpolator",
        "__on_stop",
        "__wait",
    )

    def __init__(self, obj: Any) -> None:
        super().__init__()
        self.__interpolator = AnimationInterpolator(obj)
        self.__object: weakref[Any] = weakref(self.__interpolator.object)
        self.__on_stop: Callable[[], None] | None = None
        self.__wait: bool = True

    @property
    def interpolator(self) -> AnimationInterpolator:
        return self.__interpolator

    @property
    def object(self) -> Any:
        return weakref_unwrap(self.__object)

    @abstractmethod
    def has_animation_started(self) -> bool:
        raise NotImplementedError

    def started(self) -> bool:
        return not self.__wait and self.has_animation_started()

    def on_stop(self, callback: Callable[[], None] | None) -> None:
        if not (callback is None or callable(callback)):
            raise TypeError("Invalid arguments")
        self.__on_stop = callback

    def fixed_update(self) -> None:
        if not self.started():
            return
        with self.__interpolator.fixed_update():
            self._launch_animations()
        if not self.has_animation_started():
            self.clear(pause=False)
            self.__wait = True
            if on_stop := self.__on_stop:
                on_stop()
                self.__on_stop = None

    def update(self, interpolation: float) -> None:
        if not self.started():
            return
        self.__interpolator.update(interpolation)

    def start(self) -> None:
        self.__wait = False

    def pause(self) -> None:
        self.__wait = True

    def clear(self, *, pause: bool = False) -> None:
        self.__wait = bool(pause)
        self.interpolator.reset()

    @abstractmethod
    def _launch_animations(self) -> None:
        raise NotImplementedError

    def wait_until_finish(self, scene: Scene) -> None:
        if not scene.looping() or not self.has_animation_started():
            return
        window: SceneWindow = scene.window
        self.__on_stop = None
        self.start()
        with window.stuck():
            while window.loop() and self.has_animation_started():
                window._fixed_updates_call(self.fixed_update)
                window._interpolation_updates_call(self.update)
                scene.update()
                window.render_scene()
                window.refresh()


@final
class MoveAnimation(BaseAnimation):
    __slots__ = ("__animation",)

    def __init__(self, movable: Movable) -> None:
        assert isinstance(movable, Movable), "Expected a Movable object"
        super().__init__(movable)
        self.__animation: _AbstractAnimationClass | None = None

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="MoveAnimation")

        @property
        def object(self) -> Movable:
            ...

    @overload
    def smooth_set_position(
        self: __Self,
        speed: float = 100,
        *,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
    ) -> __Self:
        ...

    @overload
    def smooth_set_position(
        self: __Self,
        speed: float = 100,
        *,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
    ) -> __Self:
        ...

    def smooth_set_position(self: __Self, speed: float = 100, **position: float | tuple[float, float]) -> __Self:
        self.__animation = _AnimationSetPosition(self.object, speed, position)
        return self

    def smooth_translation(self: __Self, translation: Vector2 | tuple[float, float], speed: float = 100) -> __Self:
        self.__animation = _AnimationMove(self.object, speed, translation)
        return self

    def infinite_translation(self: __Self, direction: Vector2 | tuple[float, float], speed: float = 100) -> __Self:
        self.__animation = _AnimationInfiniteMove(self.object, speed, direction)
        return self

    def has_animation_started(self) -> bool:
        animation = self.__animation
        return animation is not None and animation.started()

    def clear(self, *, pause: bool = False) -> None:
        super().clear(pause=pause)
        self.__animation = None

    def _launch_animations(self) -> None:
        animation = cast(_AbstractAnimationClass, self.__animation)
        if animation.started():
            animation.fixed_update()
        else:
            animation.default()


_AnimationType: TypeAlias = Literal["move", "rotate", "rotate_point", "scale_x", "scale_y"]


@final
class TransformAnimation(BaseAnimation):

    __slots__ = ("__animations",)

    __animations_order: Final[tuple[_AnimationType, ...]] = ("scale_x", "scale_y", "rotate", "rotate_point", "move")

    def __init__(self, transformable: Transformable) -> None:
        assert isinstance(transformable, Transformable), "Expected a Transformable object"
        super().__init__(transformable)
        self.__animations: dict[_AnimationType, _AbstractAnimationClass] = {}

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="TransformAnimation")

        @property
        def object(self) -> Transformable:
            ...

    @overload
    def smooth_set_position(
        self: __Self,
        speed: float = 100,
        *,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
    ) -> __Self:
        ...

    @overload
    def smooth_set_position(
        self: __Self,
        speed: float = 100,
        *,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
    ) -> __Self:
        ...

    def smooth_set_position(self: __Self, speed: float = 100, **position: float | tuple[float, float]) -> __Self:
        transformable: Transformable = self.object
        self.__animations["move"] = _AnimationSetPosition(transformable, speed, position)
        return self

    def smooth_translation(self: __Self, translation: Vector2 | tuple[float, float], speed: float = 100) -> __Self:
        transformable: Transformable = self.object
        self.__animations["move"] = _AnimationMove(transformable, speed, translation)
        return self

    def infinite_translation(self: __Self, direction: Vector2 | tuple[float, float], speed: float = 100) -> __Self:
        transformable: Transformable = self.object
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
        transformable: Transformable = self.object
        if pivot is not None:
            self.__animations.pop("rotate_point", None)
        self.__animations["rotate"] = _AnimationSetRotation(transformable, angle, speed, pivot, counter_clockwise)
        return self

    def smooth_rotation(
        self: __Self,
        angle: float,
        speed: float = 100,
    ) -> __Self:
        transformable: Transformable = self.object
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
        transformable: Transformable = self.object
        if rotate_object:
            self.__animations.pop("rotate", None)
        self.__animations["rotate_point"] = _AnimationRotationAroundPoint(transformable, angle, speed, pivot, rotate_object)
        return self

    def infinite_rotation(self: __Self, speed: float = 100, *, counter_clockwise: bool = True) -> __Self:
        transformable: Transformable = self.object
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
        transformable: Transformable = self.object
        if rotate_object:
            self.__animations.pop("rotate", None)
        self.__animations["rotate_point"] = _AnimationInfiniteRotateAroundPoint(
            transformable, speed, pivot, counter_clockwise, rotate_object
        )
        return self

    def smooth_scale_to_width(self: __Self, width: float, speed: float = 100, *, uniform: bool = True) -> __Self:
        transformable: Transformable = self.object
        if uniform:
            self.__animations.pop("scale_y", None)
        self.__animations["scale_x"] = _AnimationSetSize(transformable, width, speed, "width", uniform)
        return self

    def smooth_scale_to_height(self: __Self, height: float, speed: float = 100, *, uniform: bool = True) -> __Self:
        transformable: Transformable = self.object
        if uniform:
            self.__animations.pop("scale_x", None)
        self.__animations["scale_y"] = _AnimationSetSize(transformable, height, speed, "height", uniform)
        return self

    def smooth_width_growth(self: __Self, width_offset: float, speed: float = 100, *, uniform: bool = True) -> __Self:
        transformable: Transformable = self.object
        if uniform:
            self.__animations.pop("scale_y", None)
        self.__animations["scale_x"] = _AnimationSizeGrowth(transformable, width_offset, speed, "width", uniform)
        return self

    def smooth_height_growth(self: __Self, height_offset: float, speed: float = 100, *, uniform: bool = True) -> __Self:
        transformable: Transformable = self.object
        if uniform:
            self.__animations.pop("scale_x", None)
        self.__animations["scale_y"] = _AnimationSizeGrowth(transformable, height_offset, speed, "height", uniform)
        return self

    def has_animation_started(self) -> bool:
        return any(animation.started() for animation in self.__animations.values())

    def clear(self, *, pause: bool = False) -> None:
        super().clear(pause=pause)
        self.__animations.clear()

    def _launch_animations(self) -> None:
        for animation in filter(None, map(self.__animations.get, self.__animations_order)):
            if animation.started():
                animation.fixed_update()
            else:
                animation.default()


class _ObjectStateProtocol(Protocol):
    @staticmethod
    @abstractmethod
    def from_object(__obj: Any, /) -> _ObjectStateProtocol:
        raise NotImplementedError

    @abstractmethod
    def interpolate(self, other: _ObjectStateProtocol, alpha: float, __obj: Any, /) -> None:
        raise NotImplementedError

    @abstractmethod
    def apply_on(self, __obj: Any, /) -> None:
        raise NotImplementedError


@final
class _MoveState(NamedTuple):
    center: Vector2

    @staticmethod
    def from_object(m: Movable) -> _MoveState:
        return _MoveState(Vector2(m.center))

    def interpolate(self, other: _MoveState, alpha: float, m: Movable) -> None:
        center = self.center.lerp(other.center, alpha)
        m.center = (center.x, center.y)

    def apply_on(self, m: Movable) -> None:
        center = self.center
        m.center = (center.x, center.y)


@final
class _TransformState(NamedTuple):
    angle: float
    scale: tuple[float, float]
    center: Vector2
    data: MappingProxyType[str, Any] | None

    @staticmethod
    def from_object(t: Transformable) -> _TransformState:
        data: MappingProxyType[str, Any] | None = None
        state = t._freeze_state()
        if state is not None:
            data = MappingProxyType(state)
        return _TransformState(t.angle, t.scale, Vector2(t.center), data)

    def interpolate(self, other: _TransformState, alpha: float, t: Transformable) -> None:
        angle = angle_interpolation(self.angle, other.angle, alpha)
        scale = (
            linear_interpolation(self.scale[0], other.scale[0], alpha),
            linear_interpolation(self.scale[1], other.scale[1], alpha),
        )
        center = self.center.lerp(other.center, alpha)
        t.set_rotation_and_scale(angle, scale)
        t.center = (center.x, center.y)

    def apply_on(self, t: Transformable) -> None:
        if not t._set_frozen_state(self.angle, self.scale, self.data):
            t.update_transform()
        center = self.center
        t.center = (center.x, center.y)


class _AbstractAnimationClass(metaclass=ABCMeta):

    __slots__ = (
        "__object",
        "__animation_started",
        "__speed",
        "__delta",
    )

    def __init__(self, obj: Movable, speed: float) -> None:
        self.__object: Movable = obj
        self.__animation_started: bool = True
        self.__speed: float = speed
        self.__delta: Callable[[], float] = Time.fixed_delta

    def started(self) -> bool:
        return self.__animation_started and self.__speed > 0

    def stop(self) -> None:
        self.__animation_started = False
        self.__speed = 0
        self.default()

    @abstractmethod
    def fixed_update(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def default(self) -> None:
        raise NotImplementedError

    @property
    def object(self) -> Movable:
        return self.__object

    @property
    def speed(self) -> float:
        return self.__speed * self.__delta()


class _AbstractTransformableAnimationClass(_AbstractAnimationClass):

    __slots__ = ()

    if TYPE_CHECKING:

        def __init__(self, obj: Transformable, speed: float) -> None:
            ...

        @property
        def object(self) -> Transformable:
            ...


class _AnimationSetPosition(_AbstractAnimationClass):

    __slots__ = ("__position",)

    def __init__(self, movable: Movable, speed: float, position: dict[str, float | tuple[float, float]]) -> None:
        assert len(position) > 0, "Please give position parameter"
        super().__init__(movable, speed)
        self.__position: dict[str, float | tuple[float, float]] = position

    def started(self) -> bool:
        return super().started() and len(self.__position) > 0

    def fixed_update(self) -> None:
        movable: Movable = self.object
        actual_position = Vector2(movable.center)
        projection = movable.get_rect(**self.__position)
        direction = Vector2(projection.center) - actual_position
        speed = self.speed
        length = direction.length()
        if length > 0 and length > speed:
            direction.scale_to_length(speed)
            movable.translate(direction)
        else:
            self.stop()

    def default(self) -> None:
        if self.__position:
            self.object.set_position(**self.__position)  # type: ignore[arg-type]
            self.__position.clear()


class _AnimationMove(_AbstractAnimationClass):

    __slots__ = ("__vector", "__traveled")

    def __init__(self, movable: Movable, speed: float, translation: Vector2 | tuple[float, float]) -> None:
        super().__init__(movable, speed)
        self.__vector: Vector2 = Vector2(translation)
        self.__traveled: float = 0

    def started(self) -> bool:
        return super().started() and self.__vector.length_squared() > 0

    def fixed_update(self) -> None:
        movable: Movable = self.object
        direction = self.__vector.xy
        length: float = direction.length()
        speed: float = self.speed
        traveled: float = self.__traveled
        offset: float = min(length - traveled, speed)
        if offset == 0:
            return self.stop()
        direction.scale_to_length(offset)
        movable.translate(direction)
        self.__traveled += offset

    def default(self) -> None:
        length: float = self.__vector.length()
        if length:
            self.__traveled = length
            self.__vector = Vector2(0, 0)


class _AnimationInfiniteMove(_AbstractAnimationClass):

    __slots__ = ("__vector",)

    def __init__(self, movable: Movable, speed: float, direction: Vector2 | tuple[float, float]) -> None:
        super().__init__(movable, speed)
        self.__vector: Vector2 = Vector2(direction)
        if self.__vector.length_squared() > 0:
            self.__vector.normalize_ip()

    def started(self) -> bool:
        return super().started() and self.__vector.length_squared() > 0

    def fixed_update(self) -> None:
        movable: Movable = self.object
        direction = self.__vector.xy
        speed = self.speed
        direction.scale_to_length(speed)
        movable.translate(direction)

    def default(self) -> None:
        self.__vector = Vector2(0, 0)


class _AnimationSetRotation(_AbstractTransformableAnimationClass):

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
            pivot = transformable._get_pivot_from_attribute(pivot)
        self.__pivot = Vector2(pivot) if pivot is not None else None
        self.__counter_clockwise: bool = counter_clockwise

    def fixed_update(self) -> None:
        transformable = self.object
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
            transformable.rotate(offset, self.__pivot)
        else:
            self.stop()

    def default(self) -> None:
        self.object.set_rotation(self.__angle, self.__pivot)


class _AnimationRotation(_AbstractTransformableAnimationClass):

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

    def fixed_update(self) -> None:
        transformable: Transformable = self.object
        actual_angle: float = self.__actual_angle
        angle: float = self.__angle
        speed: float = self.speed
        offset: float = min(angle - actual_angle, speed) * self.__orientation
        if offset == 0:
            return self.stop()
        transformable.rotate(offset)
        self.__actual_angle += abs(offset)

    def default(self) -> None:
        if self.__angle:
            self.__actual_angle = self.__angle
            self.__angle = 0


class _AnimationInfiniteRotate(_AbstractTransformableAnimationClass):

    __slots__ = ("__orientation",)

    def __init__(
        self,
        transformable: Transformable,
        speed: float,
        counter_clockwise: bool,
    ) -> None:
        super().__init__(transformable, speed)
        self.__orientation: int = 1 if counter_clockwise else -1

    def fixed_update(self) -> None:
        transformable = self.object
        offset: float = self.speed * self.__orientation
        transformable.rotate(offset)

    def default(self) -> None:
        pass


# TODO: Make it available for Movable (non Transformable) objects
class _AnimationRotationAroundPoint(_AbstractTransformableAnimationClass):

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
            pivot = transformable._get_pivot_from_attribute(pivot)
        self.__pivot = Vector2(pivot)
        self.__rotate_object: bool = rotate_object

    def started(self) -> bool:
        return super().started() and self.__angle != 0

    def fixed_update(self) -> None:
        transformable: Transformable = self.object
        actual_angle: float = self.__actual_angle
        angle: float = self.__angle
        speed: float = self.speed
        offset: float = min(angle - actual_angle, speed) * self.__orientation
        if offset == 0:
            return self.stop()
        if self.__rotate_object:
            transformable.rotate(offset, self.__pivot)
        else:
            transformable.rotate_around_point(offset, self.__pivot)
        self.__actual_angle += abs(offset)

    def default(self) -> None:
        if self.__angle:
            self.__actual_angle = self.__angle
            self.__angle = 0


# TODO: Make it available for Movable (non Transformable) objects
class _AnimationInfiniteRotateAroundPoint(_AbstractTransformableAnimationClass):

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
            pivot = transformable._get_pivot_from_attribute(pivot)
        self.__pivot = Vector2(pivot)
        self.__orientation: int = 1 if counter_clockwise else -1
        self.__rotate_object: bool = rotate_object

    def fixed_update(self) -> None:
        transformable = self.object
        offset: float = self.speed * self.__orientation
        if self.__rotate_object:
            transformable.rotate(offset, self.__pivot)
        else:
            transformable.rotate_around_point(offset, self.__pivot)

    def default(self) -> None:
        pass


class _AbstractAnimationScale(_AbstractTransformableAnimationClass):

    __slots__ = ("__field", "__uniform")

    def __init__(self, transformable: Transformable, speed: float, field: Literal["width", "height"], uniform: bool) -> None:
        super().__init__(transformable, speed)
        if field not in ("width", "height"):
            raise ValueError("Invalid arguments")
        self.__field: Literal["width", "height"] = field
        self.__uniform: bool = bool(uniform)

    def get_transformable_size(self) -> float:
        area: tuple[float, float] = self.object.get_area_size(apply_rotation=False)
        if self.__field == "width":
            return area[0]
        return area[1]

    def set_transformable_size(self, value: float) -> None:
        getattr(self.object, f"scale_to_{self.__field}")(value, uniform=self.__uniform)


class _AnimationSetSize(_AbstractAnimationScale):

    __slots__ = ("__value",)

    def __init__(
        self,
        transformable: Transformable,
        value: float,
        speed: float,
        field: Literal["width", "height"],
        uniform: bool,
    ) -> None:
        super().__init__(transformable, speed, field, uniform)
        self.__value: float = value

    def fixed_update(self) -> None:
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
            self.set_transformable_size(actual_size + offset)
        else:
            self.stop()

    def default(self) -> None:
        self.set_transformable_size(self.__value)


class _AnimationSizeGrowth(_AbstractAnimationScale):

    __slots__ = ("__value", "__orientation", "__actual_value")

    def __init__(
        self,
        transformable: Transformable,
        offset: float,
        speed: float,
        field: Literal["width", "height"],
        uniform: bool,
    ) -> None:
        super().__init__(transformable, speed, field, uniform)
        self.__value: float = abs(offset)
        self.__orientation: int = int(offset // abs(offset)) if offset != 0 and speed > 0 else 0
        self.__actual_value: float = 0

    def started(self) -> bool:
        return super().started() and self.__value != 0

    def fixed_update(self) -> None:
        actual_value: float = self.__actual_value
        value: float = self.__value
        speed: float = self.speed
        offset: float = min(value - actual_value, speed) * self.__orientation
        if offset == 0:
            return self.stop()
        actual_size: float = self.get_transformable_size()
        self.set_transformable_size(actual_size + offset)
        self.__actual_value += abs(offset)

    def default(self) -> None:
        if self.__value:
            self.__actual_value = self.__value
            self.__value = 0
