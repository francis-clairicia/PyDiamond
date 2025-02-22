# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Movable objects module"""

from __future__ import annotations

__all__ = ["Movable"]

from abc import abstractmethod
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import Any, Literal, final, overload

from ..math import Rect, Vector2
from ..math.rect import modify_rect_in_place
from ..system.object import Object
from ..system.utils.functools import wraps

_SINGLE_COMPONENT_POSITIONS = (
    "x",
    "y",
    "left",
    "right",
    "top",
    "bottom",
    "centerx",
    "centery",
)

_POINT_POSITIONS = (
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

_ALL_VALID_POSITIONS = _SINGLE_COMPONENT_POSITIONS + _POINT_POSITIONS


def _position_decorator(fset: Callable[[Movable, Any], None], fget: Callable[[Movable], Any]) -> Callable[[Movable, Any], None]:
    @wraps(fset)
    def wrapper(self: Movable, /, value: Any) -> None:
        if fget(self) != value:
            fset(self, value)
            self._on_move()

    return wrapper


def __prepare_movable_namespace(mcs: Any, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
    _positions_getter: dict[str, Callable[[Movable], float | tuple[float, float]]] = {}
    _positions_setter: dict[str, Callable[[Movable, float | tuple[float, float]], None]] = {}

    _single_component_positions_getter: dict[str, Callable[[Movable], float]] = {}
    _single_component_positions_setter: dict[str, Callable[[Movable, float], None]] = {}

    _point_positions_getter: dict[str, Callable[[Movable], tuple[float, float]]] = {}
    _point_positions_setter: dict[str, Callable[[Movable, tuple[float, float]], None]] = {}

    for position in _ALL_VALID_POSITIONS:
        if position not in namespace:
            raise AttributeError(f"Missing {position!r} property")
        prop: property = namespace[position]
        assert prop.fget
        assert prop.fset
        fget = prop.fget
        fset = _position_decorator(prop.fset, fget)
        prop = prop.setter(fset)
        for func in filter(callable, (prop.fget, prop.fset, prop.fdel)):
            final(func)
        namespace[position] = prop
        _positions_getter[position] = fget
        _positions_setter[position] = fset
        if position in _SINGLE_COMPONENT_POSITIONS:
            _single_component_positions_getter[position] = fget
            _single_component_positions_setter[position] = fset
        if position in _POINT_POSITIONS:
            _point_positions_getter[position] = fget
            _point_positions_setter[position] = fset

    def wraps_method(name: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(f: Any) -> Any:
            assert f.__name__ == name
            f = wraps(namespace[name])(f)
            namespace[name] = f
            return f

        return decorator

    @wraps_method("get_position")
    def get_position(self: Movable, anchor: str) -> float | tuple[float, float]:
        try:
            fget = _positions_getter[anchor]
        except KeyError:
            raise ValueError(anchor) from None
        return fget(self)

    @wraps_method("_set_position")
    def _set_position(self: Movable, anchor: str, value: float | tuple[float, float]) -> None:
        try:
            fset = _positions_setter[anchor]
        except KeyError:
            raise ValueError(anchor) from None
        return fset(self, value)

    @wraps_method("_get_single_component_position")
    def _get_single_component_position(self: Movable, anchor: str) -> float:
        try:
            fget = _single_component_positions_getter[anchor]
        except KeyError:
            raise ValueError(anchor) from None
        return fget(self)

    @wraps_method("_set_single_component_position")
    def _set_single_component_position(self: Movable, anchor: str, value: float) -> None:
        try:
            fset = _single_component_positions_setter[anchor]
        except KeyError:
            raise ValueError(anchor) from None
        return fset(self, value)

    @wraps_method("_get_point_position")
    def _get_point_position(self: Movable, anchor: str) -> tuple[float, float]:
        try:
            fget = _point_positions_getter[anchor]
        except KeyError:
            raise ValueError(anchor) from None
        return fget(self)

    @wraps_method("_set_point_position")
    def _set_point_position(self: Movable, anchor: str, value: tuple[float, float]) -> None:
        try:
            fset = _point_positions_setter[anchor]
        except KeyError:
            raise ValueError(anchor) from None
        return fset(self, value)


class Movable(Object, prepare_namespace=__prepare_movable_namespace):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__x: float = 0
        self.__y: float = 0

    @overload
    def get_position(self, anchor: Literal["x", "y", "left", "top", "right", "bottom", "centerx", "centery"]) -> float: ...

    @overload
    def get_position(
        self,
        anchor: Literal[
            "center",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
            "midleft",
            "midright",
            "midtop",
            "midbottom",
        ],
    ) -> tuple[float, float]: ...

    @overload
    def get_position(self, anchor: str) -> float | tuple[float, float]: ...

    @final
    def get_position(self, anchor: str) -> float | tuple[float, float]:
        raise AssertionError("Should not be called")

    @final
    def _get_single_component_position(self, anchor: str) -> float:
        raise AssertionError("Should not be called")

    @final
    def _get_point_position(self, anchor: str) -> tuple[float, float]:
        raise AssertionError("Should not be called")

    @overload
    def set_position(
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
    ) -> None: ...

    @overload
    def set_position(
        self,
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
    ) -> None: ...

    @final
    def set_position(self, **kwargs: Any) -> None:
        if not kwargs:
            return

        if len(kwargs) == 1:
            attr_name, attr_value = next(iter(kwargs.items()))
            return self._set_position(attr_name, attr_value)

        if len(kwargs) != 2:
            raise TypeError("Bad parameters")

        if "x" in kwargs:
            kwargs["left"] = kwargs.pop("x")
        if "y" in kwargs:
            kwargs["top"] = kwargs.pop("y")

        match kwargs:
            case {"left": left, "top": top}:
                self._set_position("topleft", (left, top))
            case {"left": left, "centery": centery}:
                self._set_position("midleft", (left, centery))
            case {"left": left, "bottom": bottom}:
                self._set_position("bottomleft", (left, bottom))
            case {"centerx": centerx, "top": top}:
                self._set_position("midtop", (centerx, top))
            case {"centerx": centerx, "centery": centery}:
                self._set_position("center", (centerx, centery))
            case {"centerx": centerx, "bottom": bottom}:
                self._set_position("midbottom", (centerx, bottom))
            case {"right": right, "top": top}:
                self._set_position("topright", (right, top))
            case {"right": right, "centery": centery}:
                self._set_position("midright", (right, centery))
            case {"right": right, "bottom": bottom}:
                self._set_position("bottomright", (right, bottom))
            case _:
                raise TypeError("Bad parameters")

    @overload
    def _set_position(
        self,
        anchor: Literal["x", "y", "left", "top", "right", "bottom", "centerx", "centery"],
        value: float,
    ) -> None: ...

    @overload
    def _set_position(
        self,
        anchor: Literal[
            "center",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
            "midleft",
            "midright",
            "midtop",
            "midbottom",
        ],
        value: tuple[float, float],
    ) -> None: ...

    @overload
    def _set_position(self, anchor: str, value: float | tuple[float, float]) -> None: ...

    @final
    def _set_position(self, anchor: str, value: float | tuple[float, float]) -> None:
        raise AssertionError("Should not be called")

    @final
    def _set_single_component_position(self, anchor: str, value: float) -> None:
        raise AssertionError("Should not be called")

    @final
    def _set_point_position(self, anchor: str, value: tuple[float, float]) -> None:
        raise AssertionError("Should not be called")

    @final
    def move(self, dx: float, dy: float) -> None:
        if dx == 0 and dy == 0:
            return
        self.__x += dx
        self.__y += dy
        self._on_move()

    @final
    def translate(self, vector: Vector2 | tuple[float, float]) -> None:
        if vector[0] == 0 and vector[1] == 0:
            return
        self.__x += vector[0]
        self.__y += vector[1]
        self._on_move()

    @final
    def rotate_around_point(self, angle_offset: float, pivot: tuple[float, float] | Vector2 | str) -> None:
        if angle_offset == 0:
            return
        if isinstance(pivot, str):
            if pivot == "center":
                return
            pivot = Vector2(self._get_point_position(pivot))
        else:
            pivot = Vector2(pivot)
        center: Vector2 = Vector2(self.center)
        if pivot == center:
            return
        center = pivot + (center - pivot).rotate(-angle_offset)
        self.center = center.x, center.y

    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @final
    def get_width(self) -> float:
        return self.get_size()[0]

    @final
    def get_height(self) -> float:
        return self.get_size()[1]

    @overload
    def get_rect(self) -> Rect: ...

    @overload
    def get_rect(
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
    ) -> Rect: ...

    @final
    def get_rect(self, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect((self.__x, self.__y), self.get_size())
        if kwargs:
            modify_rect_in_place(r, **kwargs)
        return r

    @final
    def get_rect_relative_to(self, point: tuple[float, float] | Vector2) -> Rect:
        return Rect((self.__x - point[0], self.__y - point[1]), self.get_size())

    @final
    @contextmanager
    def temporary_position(self) -> Iterator[None]:
        x, y = self.topleft
        try:
            yield
        finally:
            self.topleft = (x, y)

    @final
    def clamp(self, rect: Rect) -> None:
        r: Rect = Rect((self.__x, self.__y), self.get_size())
        r.clamp_ip(rect)
        self.topleft = r.topleft

    def _on_move(self) -> None:
        pass

    @property
    def size(self) -> tuple[float, float]:
        return self.get_size()

    @property
    def width(self) -> float:
        return self.get_size()[0]

    @property
    def height(self) -> float:
        return self.get_size()[1]

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
    def left(self) -> float:
        return self.__x

    @left.setter
    def left(self, left: float) -> None:
        self.__x = left

    @property
    def right(self) -> float:
        return self.__x + self.get_size()[0]

    @right.setter
    def right(self, right: float) -> None:
        self.__x = right - self.get_size()[0]

    @property
    def top(self) -> float:
        return self.__y

    @top.setter
    def top(self, top: float) -> None:
        self.__y = top

    @property
    def bottom(self) -> float:
        return self.__y + self.get_size()[1]

    @bottom.setter
    def bottom(self, bottom: float) -> None:
        self.__y = bottom - self.get_size()[1]

    @property
    def center(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + (w / 2), self.__y + (h / 2))

    @center.setter
    def center(self, center: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = center[0] - (w / 2)
        self.__y = center[1] - (h / 2)

    @property
    def centerx(self) -> float:
        return self.__x + (self.get_size()[0] / 2)

    @centerx.setter
    def centerx(self, centerx: float) -> None:
        self.__x = centerx - (self.get_size()[0] / 2)

    @property
    def centery(self) -> float:
        return self.__y + (self.get_size()[1] / 2)

    @centery.setter
    def centery(self, centery: float) -> None:
        self.__y = centery - (self.get_size()[1] / 2)

    @property
    def topleft(self) -> tuple[float, float]:
        return (self.__x, self.__y)

    @topleft.setter
    def topleft(self, topleft: tuple[float, float]) -> None:
        self.__x = topleft[0]
        self.__y = topleft[1]

    @property
    def topright(self) -> tuple[float, float]:
        return (self.__x + self.get_size()[0], self.__y)

    @topright.setter
    def topright(self, topright: tuple[float, float]) -> None:
        self.__x = topright[0] - self.get_size()[0]
        self.__y = topright[1]

    @property
    def bottomleft(self) -> tuple[float, float]:
        return (self.__x, self.__y + self.get_size()[1])

    @bottomleft.setter
    def bottomleft(self, bottomleft: tuple[float, float]) -> None:
        self.__x = bottomleft[0]
        self.__y = bottomleft[1] - self.get_size()[1]

    @property
    def bottomright(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + h)

    @bottomright.setter
    def bottomright(self, bottomright: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = bottomright[0] - w
        self.__y = bottomright[1] - h

    @property
    def midtop(self) -> tuple[float, float]:
        return (self.__x + (self.get_size()[0] / 2), self.__y)

    @midtop.setter
    def midtop(self, midtop: tuple[float, float]) -> None:
        self.__x = midtop[0] - (self.get_size()[0] / 2)
        self.__y = midtop[1]

    @property
    def midbottom(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + (w / 2), self.__y + h)

    @midbottom.setter
    def midbottom(self, midbottom: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midbottom[0] - (w / 2)
        self.__y = midbottom[1] - h

    @property
    def midleft(self) -> tuple[float, float]:
        return (self.__x, self.__y + (self.get_size()[1] / 2))

    @midleft.setter
    def midleft(self, midleft: tuple[float, float]) -> None:
        self.__x = midleft[0]
        self.__y = midleft[1] - (self.get_size()[1] / 2)

    @property
    def midright(self) -> tuple[float, float]:
        w, h = self.get_size()
        return (self.__x + w, self.__y + (h / 2))

    @midright.setter
    def midright(self, midright: tuple[float, float]) -> None:
        w, h = self.get_size()
        self.__x = midright[0] - w
        self.__y = midright[1] - (h / 2)


del __prepare_movable_namespace
