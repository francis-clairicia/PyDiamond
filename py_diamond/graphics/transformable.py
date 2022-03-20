# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Transformable objects module"""

from __future__ import annotations

__all__ = ["Transformable", "TransformableMeta"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from functools import cached_property
from typing import Any, final

from pygame import error as _pg_error

from ..math import Vector2
from .animation import TransformAnimation
from .movable import Movable, MovableMeta
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
        metacls,
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
                    f"{name!r} must be inherits from a {Transformable.__name__} class in order to use {TransformableMeta.__name__} metaclass"
                )
        return super().__new__(metacls, name, bases, namespace, **kwargs)


class Transformable(Movable, metaclass=TransformableMeta):
    def __init__(self) -> None:
        Movable.__init__(self)
        self.__angle: float = 0
        self.__scale: float = 1

    def rotate(
        self, angle_offset: float, pivot: tuple[float, float] | Vector2 | str | None = None, *, apply: bool = True
    ) -> None:
        self.set_rotation(self.__angle + angle_offset, pivot=pivot, apply=apply)

    def set_rotation(
        self,
        angle: float,
        pivot: tuple[float, float] | Vector2 | str | None = None,
        *,
        apply: bool = True,
    ) -> None:
        angle = float(angle)
        angle %= 360
        if self.__angle == angle:
            return
        center: Vector2 = Vector2(self.center)
        former_angle: float = self.__angle
        self.__angle = angle
        if apply:
            try:
                try:
                    self._apply_both_rotation_and_scale()
                except NotImplementedError:
                    self._apply_only_rotation()
            except NotImplementedError:
                self.__angle = 0
                raise NotImplementedError from None
            except _pg_error:
                pass
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
        if pivot not in _ALL_VALID_ROTATION_PIVOTS:
            raise AttributeError(f"Bad pivot attribute: {pivot!r}")
        return Vector2(getattr(self, pivot))

    def set_scale(self, scale: float, *, apply: bool = True) -> None:
        scale = max(float(scale), 0)
        if self.scale == scale:
            return
        self.__scale = scale
        if not apply:
            return
        center: tuple[float, float] = self.center
        try:
            try:
                self._apply_both_rotation_and_scale()
            except NotImplementedError:
                self._apply_only_scale()
        except NotImplementedError:
            self.__scale = 1
            raise NotImplementedError from None
        except _pg_error:
            pass
        self.center = center

    def scale_to_width(self, width: float, *, apply: bool = True) -> None:
        w: float = self.get_local_size()[0]
        self.set_scale(width / w, apply=apply)

    def scale_to_height(self, height: float, *, apply: bool = True) -> None:
        h: float = self.get_local_size()[1]
        self.set_scale(height / h, apply=apply)

    def scale_to_size(self, size: tuple[float, float]) -> None:
        w, h = self.get_local_size()
        scale_width: float = size[0] / w
        scale_height: float = size[1] / h
        self.set_scale(min(scale_width, scale_height))

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
                    raise NotImplementedError
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
        return self.get_area_size()

    @final
    def get_area_size(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> tuple[float, float]:
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
        corners: list[Vector2] = [
            Vector2(0, 0),
            Vector2(w, 0),
            Vector2(w, h),
            Vector2(0, h),
        ]
        all_points: list[Vector2] = [center + (point - center).rotate(-angle) for point in corners]
        left: float = min((point.x for point in all_points), default=0)
        right: float = max((point.x for point in all_points), default=0)
        top: float = min((point.y for point in all_points), default=0)
        bottom: float = max((point.y for point in all_points), default=0)
        return (right - left, bottom - top)

    @final
    def get_area(self, *, apply_scale: bool = True, apply_rotation: bool = True) -> Rect:
        return Rect((0, 0), self.get_area_size(apply_scale=apply_scale, apply_rotation=apply_rotation))

    def get_local_rect(self, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect((0, 0), self.get_local_size())
        for name, value in kwargs.items():
            if not hasattr(r, name):
                raise AttributeError(f"{type(r).__name__!r} has no attribute {name!r}")
            setattr(r, name, value)
        return r

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

    @cached_property
    def animation(self) -> TransformAnimation:
        return TransformAnimation(self)

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
