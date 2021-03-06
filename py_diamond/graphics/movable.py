# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Movable objects module"""

from __future__ import annotations

__all__ = ["Movable", "MovableMeta", "MovableProxy", "MovableProxyMeta"]


from abc import abstractmethod
from typing import Any, Callable, overload

from ..math import Vector2
from ..system.object import Object, ObjectMeta, final
from ..system.utils.abc import concreteclass
from ..system.utils.functools import wraps
from .rect import Rect

_ALL_VALID_POSITIONS: tuple[str, ...] = (
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
    "midleft",
    "midright",
    "midtop",
    "midbottom",
)


def _position_decorator(fset: Callable[[Movable, Any], None], fget: Callable[[Movable], Any]) -> Callable[[Movable, Any], None]:
    @wraps(fset)
    def wrapper(self: Movable, /, value: Any) -> None:
        if fget(self) != value:
            fset(self, value)
            self._on_move()

    return wrapper


class MovableMeta(ObjectMeta):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> MovableMeta:
        try:
            Movable
        except NameError:
            pass
        else:
            if not any(issubclass(cls, Movable) for cls in bases):
                raise TypeError(
                    f"{name!r} must inherit from a {Movable.__name__} class in order to use {MovableMeta.__name__} metaclass"
                )

        for position in _ALL_VALID_POSITIONS:
            if position not in namespace:
                continue
            if any(hasattr(cls, position) for cls in bases):
                raise TypeError("Override of position attributes is not allowed")
            prop: property = namespace[position]
            assert prop.fget
            assert prop.fset
            namespace[position] = final(prop.setter(_position_decorator(prop.fset, prop.fget)))  # type: ignore[type-var]

        return super().__new__(mcs, name, bases, namespace, **kwargs)


class Movable(Object, metaclass=MovableMeta):
    def __init__(self) -> None:
        self.__x: float = 0
        self.__y: float = 0

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
    ) -> None:
        ...

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
    ) -> None:
        ...

    def set_position(self, **position: float | tuple[float, float]) -> None:
        assert all(name in _ALL_VALID_POSITIONS for name in position), f"Unknown position attribute caught"
        for name, value in position.items():
            setattr(self, name, value)

    def move(self, dx: float, dy: float) -> None:
        if (dx, dy) == (0, 0):
            return
        self.__x += dx
        self.__y += dy
        self._on_move()

    def translate(self, vector: Vector2 | tuple[float, float]) -> None:
        if (vector[0], vector[1]) == (0, 0):
            return
        self.__x += vector[0]
        self.__y += vector[1]
        self._on_move()

    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @final
    def get_width(self) -> float:
        return self.get_size()[0]

    @final
    def get_height(self) -> float:
        return self.get_size()[1]

    def get_rect(self, **kwargs: float | tuple[float, float]) -> Rect:
        r: Rect = Rect(self.topleft, self.get_size())
        for name, value in kwargs.items():
            setattr(r, name, value)
        return r

    def _on_move(self) -> None:
        pass

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


class MovableProxyMeta(MovableMeta):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> MovableMeta:
        if "MovableProxy" not in globals() and name == "MovableProxy":
            from ..system.utils._mangling import mangle_private_attribute

            for attr in ("x", "y"):
                attr = mangle_private_attribute(Movable, attr)

                def getter(self: MovableProxy, /, *, attr: str = str(attr)) -> Any:
                    movable: Movable = object.__getattribute__(self, "_object")
                    return getattr(movable, attr)

                def setter(self: MovableProxy, value: Any, /, *, attr: str = str(attr)) -> Any:
                    movable: Movable = object.__getattribute__(self, "_object")
                    return setattr(movable, attr, value)

                namespace[attr] = property(fget=getter, fset=setter)

            for method_name in (
                "set_position",
                "move",
                "translate",
                "get_rect",
            ):

                @wraps(getattr(Movable, method_name))  # type: ignore[arg-type]
                def wrapper(self: MovableProxy, *args: Any, __method_name: str = str(method_name), **kwargs: Any) -> Any:
                    method_name = __method_name
                    movable: Movable = object.__getattribute__(self, "_object")
                    method: Callable[..., Any] = getattr(movable, method_name)
                    return method(*args, **kwargs)

                wrapper.__qualname__ = f"{name}.{wrapper.__name__}"

                namespace[method_name] = wrapper

        return super().__new__(mcs, name, bases, namespace, **kwargs)


@concreteclass
class MovableProxy(Movable, metaclass=MovableProxyMeta):
    def __init__(self, movable: Movable) -> None:
        object.__setattr__(self, "_object", movable)

    def get_size(self) -> tuple[float, float]:
        movable: Movable = object.__getattribute__(self, "_object")
        return movable.get_size()

    def _on_move(self) -> None:
        movable: Movable = object.__getattribute__(self, "_object")
        movable._on_move()
        return super()._on_move()
