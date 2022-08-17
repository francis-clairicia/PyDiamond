# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Transformable objects module"""

from __future__ import annotations

__all__ = ["Transformable", "TransformableMeta", "TransformableProxy", "TransformableProxyMeta"]


from abc import abstractmethod
from typing import Any, Callable, Mapping, overload

from ..math import Vector2
from ..system.object import final
from ..system.utils.abc import concreteclass
from ..system.utils.functools import wraps
from .movable import Movable, MovableMeta, MovableProxy, MovableProxyMeta
from .rect import Rect

_ALL_VALID_ROTATION_PIVOTS: tuple[str, ...] = (
    "center",
    "topleft",
    "topright",
    "bottomleft",
    "bottomright",
    "midleft",
    "midright",
    "midtop",
    "midbottom",
)


class TransformableMeta(MovableMeta):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        try:
            Transformable
        except NameError:
            pass
        else:
            if not any(issubclass(cls, Transformable) for cls in bases):
                raise TypeError(
                    f"{name!r} must inherit from a {Transformable.__name__} class in order to use {TransformableMeta.__name__} metaclass"
                )
            frozen_state_methods = ["_set_frozen_state", "_freeze_state"]
            if sum(1 for method in frozen_state_methods if method in namespace) not in (0, len(frozen_state_methods)):
                raise TypeError(
                    f"If you provide one of these methods, you must implements all of the following list: {', '.join(frozen_state_methods)}"
                )
        return super().__new__(mcs, name, bases, namespace, **kwargs)


class Transformable(Movable, metaclass=TransformableMeta):
    def __init__(self) -> None:
        Movable.__init__(self)
        self.__angle: float = 0
        self.__scale_x: float = 1
        self.__scale_y: float = 1

    def rotate(self, angle_offset: float, pivot: tuple[float, float] | Vector2 | str | None = None) -> None:
        self.set_rotation(self.__angle + angle_offset, pivot=pivot)

    def set_rotation(self, angle: float, pivot: tuple[float, float] | Vector2 | str | None = None) -> None:
        angle = float(angle) % 360
        former_angle: float = self.__angle
        if former_angle == angle:
            return
        center: Vector2 = Vector2(self.center)
        self.__angle = angle
        try:
            try:
                self._apply_both_rotation_and_scale()
            except NotImplementedError:
                self._apply_only_rotation()
        except NotImplementedError:
            self.__angle = 0
            raise NotImplementedError from None
        if pivot is not None and pivot != "center" and pivot != (center.x, center.y):
            if isinstance(pivot, str):
                pivot = self.get_pivot_from_attribute(pivot)
            else:
                pivot = Vector2(pivot)
            center = pivot + (center - pivot).rotate(-self.__angle + former_angle)
        self.center = center.x, center.y

    def rotate_around_point(self, angle_offset: float, pivot: tuple[float, float] | Vector2 | str) -> None:
        if angle_offset == 0:
            return
        if isinstance(pivot, str):
            if pivot == "center":
                return
            pivot = self.get_pivot_from_attribute(pivot)
        else:
            pivot = Vector2(pivot)
        center: Vector2 = Vector2(self.center)
        if pivot == center:
            return
        center = pivot + (center - pivot).rotate(-angle_offset)
        self.center = center.x, center.y

    def get_pivot_from_attribute(self, pivot: str) -> Vector2:
        assert pivot in _ALL_VALID_ROTATION_PIVOTS, f"Bad pivot attribute: {pivot!r}"
        return Vector2(getattr(self, pivot))

    @overload
    def set_scale(self, *, scale_x: float) -> None:
        ...

    @overload
    def set_scale(self, *, scale_y: float) -> None:
        ...

    @overload
    def set_scale(self, *, scale_x: float, scale_y: float) -> None:
        ...

    @overload
    def set_scale(self, __scale: tuple[float, float], /) -> None:
        ...

    def set_scale(  # type: ignore[misc]  # mypy will not understand
        self,
        scale: tuple[float, float] | None = None,
        /,
        *,
        scale_x: float | None = None,
        scale_y: float | None = None,
    ) -> None:
        if scale is not None:
            if scale_x is not None or scale_y is not None:
                raise TypeError("Invalid parameters")
            scale_x, scale_y = scale
        elif scale_x is None and scale_y is None:
            raise TypeError("Invalid parameters")
        del scale
        if scale_x is not None:
            scale_x = max(float(scale_x), 0)
        if scale_y is not None:
            scale_y = max(float(scale_y), 0)
        if (scale_x is None or self.__scale_x == scale_x) and (scale_y is None or self.__scale_y == scale_y):
            return
        center: tuple[float, float] = self.center
        if scale_x is not None:
            self.__scale_x = scale_x
        if scale_y is not None:
            self.__scale_y = scale_y
        try:
            try:
                self._apply_both_rotation_and_scale()
            except NotImplementedError:
                self._apply_only_scale()
        except NotImplementedError:
            self.__scale_x = self.__scale_y = 1
            raise NotImplementedError from None
        self.center = center

    def set_rotation_and_scale(self, angle: float, scale: tuple[float, float]) -> None:
        angle = float(angle) % 360
        scale_x, scale_y = scale
        scale_x = max(float(scale_x), 0)
        scale_y = max(float(scale_y), 0)
        if self.__angle == angle and self.__scale_x == scale_x and self.__scale_y == scale_y:
            return
        center: tuple[float, float] = self.center
        self.__angle = angle
        self.__scale_x = scale_x
        self.__scale_y = scale_y
        try:
            self._apply_both_rotation_and_scale()
        except NotImplementedError:
            self.__angle = 0
            self.__scale_x = self.__scale_y = 1
            raise NotImplementedError from None
        self.center = center

    def scale_to_width(self, width: float) -> None:
        w: float = self.get_local_size()[0]
        scale = width / w if w > 0 else 0
        self.set_scale((scale, scale))

    def scale_to_height(self, height: float) -> None:
        h: float = self.get_local_size()[1]
        scale = height / h if h > 0 else 0
        self.set_scale((scale, scale))

    def scale_to_size(self, size: tuple[float, float]) -> None:
        w, h = self.get_local_size()
        scale_width: float = size[0] / w if w > 0 else 0
        scale_height: float = size[1] / h if h > 0 else 0
        scale = min(scale_width, scale_height)
        self.set_scale((scale, scale))

    def set_min_width(self, width: float) -> None:
        if self.width < width:
            self.width = width

    def set_max_width(self, width: float) -> None:
        if self.width > width:
            self.width = width

    def set_min_height(self, height: float) -> None:
        if self.height < height:
            self.height = height

    def set_max_height(self, height: float) -> None:
        if self.height > height:
            self.height = height

    def set_min_size(self, size: tuple[float, float]) -> None:
        if self.width < size[0] or self.height < size[1]:
            self.size = size

    def set_max_size(self, size: tuple[float, float]) -> None:
        if self.width > size[0] or self.height > size[1]:
            self.size = size

    @final
    def apply_rotation_scale(self) -> None:
        try:
            self._apply_both_rotation_and_scale()
        except NotImplementedError:
            only_scale_exc: NotImplementedError | None = None
            only_rotation_exc: NotImplementedError | None = None
            try:
                try:
                    self._apply_only_scale()
                except NotImplementedError as exc:
                    only_scale_exc = exc
                try:
                    self._apply_only_rotation()
                except NotImplementedError as exc:
                    only_rotation_exc = exc
                if only_scale_exc is not None and only_rotation_exc is not None:
                    raise
                if only_scale_exc is None and only_rotation_exc is None:
                    raise TypeError(
                        "_apply_only_scale and _apply_only_rotation are implemented, but not _apply_both_rotation_and_scale"
                    )
            finally:
                del only_scale_exc, only_rotation_exc

    @abstractmethod
    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def _apply_only_scale(self) -> None:
        raise NotImplementedError

    def _freeze_state(self) -> dict[str, Any] | None:
        return None

    def _set_frozen_state(self, angle: float, scale: tuple[float, float], state: Mapping[str, Any] | None) -> bool:
        self.__angle = float(angle) % 360
        scale_x, scale_y = scale
        self.__scale_x = max(float(scale_x), 0)
        self.__scale_y = max(float(scale_y), 0)
        return False

    @abstractmethod
    def get_local_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @final
    def get_local_width(self) -> float:
        return self.get_local_size()[0]

    @final
    def get_local_height(self) -> float:
        return self.get_local_size()[1]

    def get_size(self) -> tuple[float, float]:
        return self.get_area_size(apply_scale=True, apply_rotation=True)

    @final
    def get_area_size(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> tuple[float, float]:
        if not apply_scale and not apply_rotation:
            return self.get_local_size()

        scale_x: float = self.__scale_x
        scale_y: float = self.__scale_y
        angle: float = self.__angle
        w, h = self.get_local_size()
        if apply_scale:
            w *= scale_x
            h *= scale_y
        if not apply_rotation or angle == 0 or angle == 180:
            return (w, h)
        if angle == 90 or angle == 270:
            return (h, w)

        center: Vector2 = Vector2(w / 2, h / 2)
        all_points: list[Vector2] = [
            Vector2(0, 0),
            Vector2(w, 0),
            Vector2(w, h),
            Vector2(0, h),
        ]
        all_points = [center + (point - center).rotate(-angle) for point in all_points]
        left: float = min((point.x for point in all_points), default=0)
        right: float = max((point.x for point in all_points), default=0)
        top: float = min((point.y for point in all_points), default=0)
        bottom: float = max((point.y for point in all_points), default=0)
        return (right - left + 1, bottom - top + 2)

    @final
    def get_area(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> Rect:
        return Rect((0, 0), self.get_area_size(apply_scale=apply_scale, apply_rotation=apply_rotation))

    def get_local_rect(self, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect((0, 0), self.get_local_size())
        for name, value in kwargs.items():
            setattr(r, name, value)
        return r

    @property
    def angle(self) -> float:
        return self.__angle

    @angle.setter
    def angle(self, angle: float) -> None:
        self.set_rotation(angle)

    @property
    def scale(self) -> tuple[float, float]:
        return self.__scale_x, self.__scale_y

    @scale.setter
    def scale(self, scale: tuple[float, float]) -> None:
        self.set_scale(scale)

    @property
    def scale_x(self) -> float:
        return self.__scale_x

    @scale_x.setter
    def scale_x(self, scale: float) -> None:
        self.set_scale(scale_x=scale)

    @property
    def scale_y(self) -> float:
        return self.__scale_y

    @scale_y.setter
    def scale_y(self, scale: float) -> None:
        self.set_scale(scale_y=scale)

    @property
    def size(self) -> tuple[float, float]:
        return self.get_size()

    @size.setter
    def size(self, size: tuple[float, float]) -> None:
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


class TransformableProxyMeta(TransformableMeta, MovableProxyMeta):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> Any:
        if "TransformableProxy" not in globals() and name == "TransformableProxy":
            from ..system.utils._mangling import mangle_private_attribute

            for attr in ("angle", "scale", "scale_x", "scale_y"):
                attr = mangle_private_attribute(Transformable, attr)

                def getter(self: TransformableProxy, /, *, attr: str = str(attr)) -> Any:
                    transformable: Transformable = object.__getattribute__(self, "_object")
                    return getattr(transformable, attr)

                def setter(self: TransformableProxy, value: Any, /, *, attr: str = str(attr)) -> Any:
                    transformable: Transformable = object.__getattribute__(self, "_object")
                    return setattr(transformable, attr, value)

                namespace[attr] = property(fget=getter, fset=setter)

            for method_name in (
                "rotate",
                "set_rotation",
                "rotate_around_point",
                "get_pivot_from_attribute",
                "set_scale",
                "scale_to_width",
                "scale_to_height",
                "scale_to_size",
                "set_min_width",
                "set_max_width",
                "set_min_height",
                "set_max_height",
                "set_min_size",
                "set_max_size",
                "_freeze_state",
                "_set_frozen_state",
                "get_local_rect",
            ):

                @wraps(getattr(Transformable, method_name))  # type: ignore[arg-type]
                def wrapper(self: TransformableProxy, *args: Any, __method_name: str = str(method_name), **kwargs: Any) -> Any:
                    method_name = __method_name
                    transformable: Transformable = object.__getattribute__(self, "_object")
                    method: Callable[..., Any] = getattr(transformable, method_name)
                    return method(*args, **kwargs)

                wrapper.__qualname__ = f"{name}.{wrapper.__name__}"

                namespace[method_name] = wrapper

        return super().__new__(mcs, name, bases, namespace, **kwargs)


@concreteclass
class TransformableProxy(Transformable, MovableProxy, metaclass=TransformableProxyMeta):
    def __init__(self, transformable: Transformable) -> None:
        MovableProxy.__init__(self, transformable)

    def get_local_size(self) -> tuple[float, float]:
        transformable: Transformable = object.__getattribute__(self, "_object")
        return transformable.get_local_size()

    def _apply_both_rotation_and_scale(self) -> None:
        transformable: Transformable = object.__getattribute__(self, "_object")
        return transformable._apply_both_rotation_and_scale()

    def _apply_only_rotation(self) -> None:
        transformable: Transformable = object.__getattribute__(self, "_object")
        return transformable._apply_only_rotation()

    def _apply_only_scale(self) -> None:
        transformable: Transformable = object.__getattribute__(self, "_object")
        return transformable._apply_only_scale()
