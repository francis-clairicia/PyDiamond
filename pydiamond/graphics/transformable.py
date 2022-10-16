# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Transformable objects module"""

from __future__ import annotations

__all__ = ["Transformable", "TransformableProxy"]

from abc import abstractmethod
from typing import Any, Literal, Mapping, overload

from typing_extensions import assert_never

from ..math import Rect, Vector2, compute_rect_from_vertices, compute_size_from_vertices, normalize_points, rotate_points
from ..math.rect import modify_rect_in_place, move_rect_in_place
from ..system.object import final
from ..system.utils.abc import concreteclass
from .movable import Movable, MovableProxy


class Transformable(Movable):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__angle: float = 0
        self.__scale_x: float = 1
        self.__scale_y: float = 1

    @final
    def rotate(self, angle_offset: float, pivot: tuple[float, float] | Vector2 | str | None = None) -> None:
        self.set_rotation(self.__angle + angle_offset, pivot=pivot)

    @final
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
                pivot = Vector2(self._get_point_position(pivot))
            else:
                pivot = Vector2(pivot)
            center = pivot + (center - pivot).rotate(-self.__angle + former_angle)
        self.center = center.x, center.y

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
    def set_scale(self, __scale: float, /) -> None:
        ...

    @overload
    def set_scale(self, __scale: tuple[float, float], /) -> None:
        ...

    @final  # type: ignore[misc]  # mypy will not understand
    def set_scale(
        self,
        __scale: tuple[float, float] | float | None = None,
        /,
        *,
        scale_x: float | None = None,
        scale_y: float | None = None,
    ) -> None:
        if __scale is not None:
            if scale_x is not None or scale_y is not None:
                raise TypeError("Invalid parameters")
            try:
                scale_x, scale_y = __scale  # type: ignore[misc]
            except TypeError:  # Number
                scale_x = scale_y = __scale  # type: ignore[assignment]
        elif scale_x is None and scale_y is None:
            raise TypeError("Invalid parameters")
        del __scale
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

    @final
    def set_rotation_and_scale(self, angle: float, scale: tuple[float, float]) -> None:
        angle = float(angle) % 360
        scale_x, scale_y = scale
        scale_x = max(float(scale_x), 0)
        scale_y = max(float(scale_y), 0)
        del scale
        if self.__angle == angle and self.__scale_x == scale_x and self.__scale_y == scale_y:
            return
        center: tuple[float, float] = self.center
        self.__angle = angle
        self.__scale_x = scale_x
        self.__scale_y = scale_y
        try:
            self._apply_both_rotation_and_scale()
        except NotImplementedError:
            only_scale_exc: NotImplementedError | Literal[True] | None = None
            only_rotation_exc: NotImplementedError | Literal[True] | None = None
            try:
                if (scale_x, scale_y) != (1, 1):
                    try:
                        self._apply_only_scale()
                    except NotImplementedError as exc:
                        self.__scale_x = self.__scale_y = 1
                        only_scale_exc = exc
                    else:
                        only_scale_exc = True
                if angle != 0:
                    try:
                        self._apply_only_rotation()
                    except NotImplementedError as exc:
                        self.__angle = 0
                        only_rotation_exc = exc
                    else:
                        only_rotation_exc = True
                if only_scale_exc is None and only_rotation_exc is None:
                    return
                if only_scale_exc is True and only_rotation_exc is True:
                    raise TypeError(
                        "_apply_only_scale and _apply_only_rotation are implemented, but not _apply_both_rotation_and_scale"
                    )
                # isinstance() is a performance eater X)
                if only_scale_exc not in (None, True):
                    if only_rotation_exc not in (None, True):
                        raise NotImplementedError("Transformation not supported") from None
                    raise NotImplementedError("Scaling not supported") from None
                elif only_rotation_exc not in (None, True):
                    raise NotImplementedError("Rotation not supported") from None
            finally:
                del only_scale_exc, only_rotation_exc
        self.center = center

    @final
    def scale_to_width(self, width: float, *, uniform: bool = True) -> None:
        w: float = self.get_local_size()[0]
        scale = width / w if w > 0 else 0
        if not uniform:
            return self.set_scale(scale_x=scale)
        self.set_scale(scale)

    @final
    def scale_to_height(self, height: float, *, uniform: bool = True) -> None:
        h: float = self.get_local_size()[1]
        scale = height / h if h > 0 else 0
        if not uniform:
            return self.set_scale(scale_y=scale)
        self.set_scale(scale)

    @final
    def scale_to_size(self, size: tuple[float, float], *, strategy: Literal["both", "min", "max"] = "both") -> None:
        w, h = self.get_local_size()
        scale_width: float = size[0] / w if w > 0 else 0
        scale_height: float = size[1] / h if h > 0 else 0
        match strategy:
            case "min" | "max":
                reduce_func = min if strategy == "min" else max
                self.set_scale(reduce_func(scale_width, scale_height))
            case "both":
                self.set_scale((scale_width, scale_height))
            case _:
                assert_never(strategy)

    @final
    def set_min_width(self, width: float, *, uniform: bool = True) -> None:
        if self.width < width:
            self.scale_to_width(width, uniform=uniform)

    @final
    def set_max_width(self, width: float, *, uniform: bool = True) -> None:
        if self.width > width:
            self.scale_to_width(width, uniform=uniform)

    @final
    def set_min_height(self, height: float, *, uniform: bool = True) -> None:
        if self.height < height:
            self.scale_to_height(height, uniform=uniform)

    @final
    def set_max_height(self, height: float, *, uniform: bool = True) -> None:
        if self.height > height:
            self.scale_to_height(height, uniform=uniform)

    @final
    def set_min_size(self, size: tuple[float, float], *, uniform: bool = True) -> None:
        actual_width, actual_height = self.get_size()
        if not (actual_width < size[0] or actual_height < size[1]):
            return
        if not uniform:
            if actual_width > size[0]:
                size = (actual_width, size[1])
            if actual_height > size[1]:
                size = (size[0], actual_height)
            self.scale_to_size(size, strategy="both")
        else:
            local_size = self.get_local_size()
            higher_pair = (size[0], local_size[0])
            lower_pair = (size[1], local_size[1])
            del local_size
            if actual_width < actual_height:
                lower_pair, higher_pair = higher_pair, lower_pair
            scale: float = lower_pair[0] / lower_pair[1] if lower_pair[1] > 0 else 0
            if higher_pair[1] * scale < higher_pair[0]:
                scale = max(scale, higher_pair[0] / higher_pair[1] if higher_pair[1] > 0 else 0)
            self.set_scale(scale)

    @final
    def set_max_size(self, size: tuple[float, float], *, uniform: bool = True) -> None:
        actual_width, actual_height = self.get_size()
        if not (actual_width > size[0] or actual_height > size[1]):
            return
        if not uniform:
            if actual_width < size[0]:
                size = (actual_width, size[1])
            if actual_height < size[1]:
                size = (size[0], actual_height)
            self.scale_to_size(size, strategy="both")
        else:
            local_size = self.get_local_size()
            higher_pair = (size[0], local_size[0])
            lower_pair = (size[1], local_size[1])
            del local_size
            if actual_width < actual_height:
                lower_pair, higher_pair = higher_pair, lower_pair
            scale: float = higher_pair[0] / higher_pair[1] if higher_pair[1] > 0 else 0
            if lower_pair[1] * scale > lower_pair[0]:
                scale = min(scale, lower_pair[0] / lower_pair[1] if lower_pair[1] > 0 else 0)
            self.set_scale(scale)

    @final
    def update_transform(self) -> None:
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
        if w < 1 or h < 1:
            return (0, 0)
        if not apply_rotation or angle == 0 or angle == 180:
            return (w, h)
        if angle == 90 or angle == 270:
            return (h, w)

        center: Vector2 = Vector2((w - 1) / 2, (h - 1) / 2)
        all_points: list[Vector2] = [
            center + (Vector2(point) - center).rotate(-angle) for point in ((0, 0), (w - 1, 0), (w - 1, h - 1), (0, h - 1))
        ]
        return compute_size_from_vertices(all_points)

    @overload
    def get_area_vertices(
        self,
        *,
        apply_scale: bool = True,
        apply_rotation: bool = True,
    ) -> tuple[()] | tuple[Vector2, Vector2, Vector2, Vector2]:
        ...

    @overload
    def get_area_vertices(
        self,
        *,
        apply_scale: bool = True,
        apply_rotation: bool = True,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
    ) -> tuple[()] | tuple[Vector2, Vector2, Vector2, Vector2]:
        ...

    @final
    def get_area_vertices(
        self,
        *,
        apply_scale: bool = True,
        apply_rotation: bool = True,
        **kwargs: Any,
    ) -> tuple[()] | tuple[Vector2, Vector2, Vector2, Vector2]:
        w, h = self.get_local_size()
        scale_x: float = self.__scale_x
        scale_y: float = self.__scale_y
        if apply_scale:
            w *= scale_x
            h *= scale_y
        if w < 1 or h < 1:
            return ()

        vertices: tuple[Vector2, Vector2, Vector2, Vector2] = (
            Vector2(0, 0),
            Vector2(w - 1, 0),
            Vector2(w - 1, h - 1),
            Vector2(0, h - 1),
        )

        if apply_rotation:
            angle: float = self.__angle
            vertices = rotate_points(vertices, angle)  # type: ignore[assignment]
            normalize_points(vertices)

        if kwargs:
            rect = Rect(compute_rect_from_vertices(vertices))
            move_rect_in_place(rect, **kwargs)
            dx = rect.x
            dy = rect.y

            for point in vertices:
                point.x += dx
                point.y += dy

        return vertices

    @overload
    def get_area(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> Rect:
        ...

    @overload
    def get_area(
        self,
        *,
        apply_scale: bool = True,
        apply_rotation: bool = True,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
        size: tuple[float, float] = ...,
        width: float = ...,
        height: float = ...,
        w: float = ...,
        h: float = ...,
    ) -> Rect:
        ...

    @final
    def get_area(self, *, apply_scale: bool = True, apply_rotation: bool = True, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect((0, 0), self.get_area_size(apply_scale=apply_scale, apply_rotation=apply_rotation))
        if kwargs:
            modify_rect_in_place(r, **kwargs)
        return r

    @overload
    def get_local_rect(self) -> Rect:
        ...

    @overload
    def get_local_rect(
        self,
        *,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
        size: tuple[float, float] = ...,
        width: float = ...,
        height: float = ...,
        w: float = ...,
        h: float = ...,
    ) -> Rect:
        ...

    @final
    def get_local_rect(self, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect((0, 0), self.get_local_size())
        if kwargs:
            modify_rect_in_place(r, **kwargs)
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
        scale_x, scale_y = scale
        self.set_scale(scale_x=scale_x, scale_y=scale_y)

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
        self.scale_to_size(size, strategy="both")

    @property
    def width(self) -> float:
        return self.get_size()[0]

    @width.setter
    def width(self, width: float) -> None:
        self.scale_to_width(width, uniform=False)

    @property
    def height(self) -> float:
        return self.get_size()[1]

    @height.setter
    def height(self, height: float) -> None:
        self.scale_to_height(height, uniform=False)


def __prepare_proxy_namespace(mcs: Any, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
    from ..system.utils._mangling import mangle_private_attribute

    for attr in ("angle", "scale_x", "scale_y"):
        attr = mangle_private_attribute(Transformable, attr)

        def getter(self: TransformableProxy, /, *, attr: str = str(attr)) -> Any:
            transformable: Transformable = object.__getattribute__(self, "_object")
            return getattr(transformable, attr)

        def setter(self: TransformableProxy, value: Any, /, *, attr: str = str(attr)) -> None:
            transformable: Transformable = object.__getattribute__(self, "_object")
            return setattr(transformable, attr, value)

        def deleter(self: TransformableProxy, /, *, attr: str = str(attr)) -> None:
            transformable: Transformable = object.__getattribute__(self, "_object")
            return delattr(transformable, attr)

        namespace[attr] = property(fget=getter, fset=setter, fdel=deleter)


@concreteclass
class TransformableProxy(Transformable, MovableProxy, prepare_namespace=__prepare_proxy_namespace):
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

    def _freeze_state(self) -> dict[str, Any] | None:
        transformable: Transformable = object.__getattribute__(self, "_object")
        return transformable._freeze_state()

    def _set_frozen_state(self, angle: float, scale: tuple[float, float], state: Mapping[str, Any] | None) -> bool:
        transformable: Transformable = object.__getattribute__(self, "_object")
        return transformable._set_frozen_state(angle, scale, state)


del __prepare_proxy_namespace
