# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Drawable objects module"""

from __future__ import annotations

__all__ = [
    "Drawable",
    "DrawableGroup",
    "DrawableMeta",
    "LayeredGroup",
    "MDrawable",
    "MDrawableMeta",
    "TDrawable",
    "TDrawableMeta",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from bisect import insort_right
from contextlib import suppress
from typing import TYPE_CHECKING, Any, Callable, Iterator, Sequence, TypeVar, overload

from ..system._mangling import getattr_pv
from ..system.utils import wraps
from .movable import Movable, MovableMeta
from .transformable import Transformable, TransformableMeta

if TYPE_CHECKING:
    from .renderer import Renderer

_T = TypeVar("_T")


def _draw_decorator(func: Callable[[Drawable, Renderer], None], /) -> Callable[[Drawable, Renderer], None]:
    @wraps(func)
    def wrapper(self: Drawable, /, target: Renderer) -> None:
        if self.is_shown():
            func(self, target)

    return wrapper


class DrawableMeta(ABCMeta):
    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> DrawableMeta:
        try:
            Drawable
        except NameError:
            pass
        else:
            if not any(issubclass(cls, Drawable) for cls in bases):
                raise TypeError(
                    f"{name!r} must be inherits from a {Drawable.__name__} class in order to use {DrawableMeta.__name__} metaclass"
                )

            draw_method: Callable[[Drawable, Renderer], None] | None = namespace.get("draw_onto")
            if callable(draw_method):
                namespace["draw_onto"] = _draw_decorator(draw_method)

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class Drawable(metaclass=DrawableMeta):
    def __init__(self) -> None:
        self.__shown: bool = True
        self.__groups: set[DrawableGroup] = set()

    @abstractmethod
    def draw_onto(self, target: Renderer) -> None:
        raise NotImplementedError

    def show(self) -> None:
        self.set_visibility(True)

    def hide(self) -> None:
        self.set_visibility(False)

    def set_visibility(self, status: bool) -> None:
        self.__shown = bool(status)

    def is_shown(self) -> bool:
        return self.__shown

    def add_to_group(self, *groups: DrawableGroup) -> None:
        actual_groups: set[DrawableGroup] = self.__groups
        for g in filter(lambda g: g not in actual_groups, groups):
            actual_groups.add(g)
            if self not in g:
                try:
                    g.add(self)
                except:
                    actual_groups.remove(g)
                    raise

    def remove_from_group(self, *groups: DrawableGroup) -> None:
        if not groups:
            return
        actual_groups: set[DrawableGroup] = self.__groups
        for g in groups:
            if g not in actual_groups:
                raise ValueError(f"sprite not in {g!r}")
        for g in groups:
            actual_groups.remove(g)
            if self in g:
                with suppress(ValueError):
                    g.remove(self)

    def kill(self) -> None:
        actual_groups: set[DrawableGroup] = self.__groups.copy()
        self.__groups.clear()
        for g in actual_groups:
            if self in g:
                with suppress(ValueError):
                    g.remove(self)
        del actual_groups

    def is_alive(self) -> bool:
        return len(self.__groups) > 0

    @property
    def groups(self) -> frozenset[DrawableGroup]:
        return frozenset(self.__groups)


class TDrawableMeta(DrawableMeta, TransformableMeta):
    pass


class TDrawable(Drawable, Transformable, metaclass=TDrawableMeta):
    def __init__(self) -> None:
        Drawable.__init__(self)
        Transformable.__init__(self)


class MDrawableMeta(DrawableMeta, MovableMeta):
    pass


class MDrawable(Drawable, Movable, metaclass=MDrawableMeta):
    def __init__(self) -> None:
        Drawable.__init__(self)
        Movable.__init__(self)


class DrawableGroup(Sequence[Drawable]):

    __slots__ = ("__list",)

    def __init__(self, *objects: Drawable, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__list: list[Drawable] = []
        self.add(*objects)

    def __len__(self) -> int:
        drawable_list_length = self.__list.__len__
        return drawable_list_length()

    @overload
    def __getitem__(self, index: int, /) -> Drawable:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[Drawable]:
        ...

    def __getitem__(self, index: int | slice, /) -> Drawable | Sequence[Drawable]:
        drawable_list: list[Drawable] = self.__list
        if isinstance(index, slice):
            return tuple(drawable_list[index])
        return drawable_list[index]

    def __bool__(self) -> bool:
        return self.__len__() > 0

    def draw_onto(self, target: Renderer) -> None:
        for drawable in self.__list:
            drawable.draw_onto(target)

    def add(self, *objects: Drawable) -> None:
        drawable_list: list[Drawable] = self.__list
        for d in filter(lambda d: d not in drawable_list, objects):
            drawable_list.append(d)
            if self not in d.groups:
                try:
                    d.add_to_group(self)
                except:
                    drawable_list.remove(d)
                    raise

    def remove(self, *objects: Drawable) -> None:
        if not objects:
            return
        drawable_list: list[Drawable] = self.__list
        for d in objects:
            if d not in drawable_list:
                raise ValueError(f"{d!r} not in self")
        for d in objects:
            drawable_list.remove(d)
            if self in d.groups:
                with suppress(ValueError):
                    d.remove_from_group(self)

    def pop(self, index: int = -1) -> Drawable:
        drawable_list: list[Drawable] = self.__list
        d: Drawable = drawable_list.pop(index)
        if self in d.groups:
            with suppress(ValueError):
                d.remove_from_group(self)
        return d

    def clear(self) -> None:
        while not self.empty():
            self.pop()

    def empty(self) -> bool:
        return not self

    def find(self, objtype: type[_T]) -> Iterator[_T]:
        for obj in self:
            if isinstance(obj, objtype):
                yield obj


class LayeredGroup(DrawableGroup):

    __slots__ = ("__default_layer", "__layer_dict")

    def __init__(self, *objects: Drawable, default_layer: int = 0, **kwargs: Any) -> None:
        self.__default_layer: int = default_layer
        self.__layer_dict: dict[Drawable, int] = {}
        super().__init__(*objects, **kwargs)

    def add(self, *objects: Drawable, layer: int | None = None) -> None:
        if not objects:
            return
        layer_dict: dict[Drawable, int] = self.__layer_dict
        drawable_list: list[Drawable] = getattr_pv(self, "list", owner=DrawableGroup)
        if layer is None:
            layer = self.__default_layer
        for d in filter(lambda d: d not in drawable_list, objects):
            layer_dict.setdefault(d, layer)
            insort_right(drawable_list, d, key=layer_dict.__getitem__)
            if self not in d.groups:
                try:
                    d.add_to_group(self)
                except:
                    drawable_list.remove(d)
                    raise

    def remove(self, *objects: Drawable) -> None:
        if not objects:
            return
        super().remove(*objects)
        for d in objects:
            self.__layer_dict.pop(d, None)

    def pop(self, index: int = -1) -> Drawable:
        d: Drawable = super().pop(index=index)
        self.__layer_dict.pop(d, None)
        return d

    def get_layer(self, obj: Drawable) -> int:
        layer_dict: dict[Drawable, int] = self.__layer_dict
        try:
            return layer_dict[obj]
        except KeyError:
            raise ValueError("obj not in group") from None

    def change_layer(self, obj: Drawable, layer: int) -> None:
        layer = int(layer)
        layer_dict: dict[Drawable, int] = self.__layer_dict
        actual_layer: int | None = layer_dict.get(obj, None)
        if (actual_layer is None and layer == self.__default_layer) or (actual_layer is not None and actual_layer == layer):
            return
        drawable_list: list[Drawable] = getattr_pv(self, "list", owner=DrawableGroup)
        try:
            drawable_list.remove(obj)
        except ValueError:
            raise ValueError("obj not in group") from None
        layer_dict[obj] = layer
        insort_right(drawable_list, obj, key=layer_dict.__getitem__)

    def get_top_layer(self) -> int:
        layer_dict: dict[Drawable, int] = self.__layer_dict
        return layer_dict[self[-1]]

    def get_bottom_layer(self) -> int:
        layer_dict: dict[Drawable, int] = self.__layer_dict
        return layer_dict[self[0]]

    def get_top_drawable(self) -> Drawable:
        return self[-1]

    def get_bottom_drawable(self) -> Drawable:
        return self[0]

    def move_to_front(self, obj: Drawable) -> None:
        self.change_layer(obj, self.get_top_layer())

    def move_to_back(self, obj: Drawable, after_last: bool = True) -> None:
        self.change_layer(obj, self.get_bottom_layer() - int(bool(after_last)))

    def get_from_layer(self, layer: int) -> Sequence[Drawable]:
        drawable_list: list[Drawable] = []
        add_drawable = drawable_list.append

        for obj, drawable_layer in self.__layer_dict.items():
            if drawable_layer == layer:
                add_drawable(obj)
            elif drawable_layer > layer:
                break

        return drawable_list

    def remove_from_layer(self, layer: int) -> Sequence[Drawable]:
        drawable_list: Sequence[Drawable] = self.get_from_layer(layer)
        self.remove(*drawable_list)
        return drawable_list

    def switch_layer(self, layer1: int, layer2: int) -> None:
        get_from_layer = self.get_from_layer
        change_layer = self.change_layer
        drawable_list_layer1: Sequence[Drawable] = get_from_layer(layer1)
        drawable_list_layer2: Sequence[Drawable] = get_from_layer(layer2)
        for d in drawable_list_layer1:
            change_layer(d, layer2)
        for d in drawable_list_layer2:
            change_layer(d, layer1)

    @property
    def default_layer(self) -> int:
        return self.__default_layer

    @property
    def layers(self) -> Sequence[int]:
        return sorted(set(self.__layer_dict.values()))


del _T
