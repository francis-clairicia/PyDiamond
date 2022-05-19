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
    "LayeredDrawableGroup",
    "MDrawable",
    "MDrawableMeta",
    "TDrawable",
    "TDrawableMeta",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from bisect import insort_right
from contextlib import suppress
from itertools import dropwhile, filterfalse, takewhile
from typing import TYPE_CHECKING, Any, Callable, Iterator, Sequence, TypeVar, overload
from weakref import WeakKeyDictionary, WeakSet

from ..system.object import Object, ObjectMeta, final
from ..system.utils._mangling import getattr_pv
from ..system.utils.abc import isabstractmethod
from ..system.utils.functools import wraps
from .movable import Movable, MovableMeta
from .transformable import Transformable, TransformableMeta

if TYPE_CHECKING:
    from .renderer import AbstractRenderer

_T = TypeVar("_T")


def _draw_decorator(func: Callable[[Drawable, AbstractRenderer], None], /) -> Callable[[Drawable, AbstractRenderer], None]:
    @wraps(func)
    def wrapper(self: Drawable, /, target: AbstractRenderer) -> None:
        if self.is_shown():
            func(self, target)

    return wrapper


class DrawableMeta(ObjectMeta):
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

            draw_method: Callable[[Drawable, AbstractRenderer], None] | None = namespace.get("draw_onto")
            if callable(draw_method) and not isabstractmethod(draw_method):
                namespace["draw_onto"] = _draw_decorator(draw_method)

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)

        if not hasattr(cls, "__weakref__"):
            raise TypeError("A Drawable object must be weak-referencable")

        return cls


class Drawable(Object, metaclass=DrawableMeta):
    __slots__ = ("__weakref__", "__dict__")

    def __init__(self) -> None:
        self.__shown: bool = True
        self.__groups: WeakSet[DrawableGroup] = WeakSet()

    @abstractmethod
    def draw_onto(self, target: AbstractRenderer) -> None:
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
        actual_groups: WeakSet[DrawableGroup] = self.__groups
        for g in filterfalse(actual_groups.__contains__, groups):
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
        actual_groups: WeakSet[DrawableGroup] = self.__groups
        for g in groups:
            if g not in actual_groups:
                raise ValueError(f"sprite not in {g!r}")
        for g in groups:
            actual_groups.remove(g)
            if self in g:
                with suppress(ValueError):
                    g.remove(self)

    def kill(self) -> None:
        actual_groups: WeakSet[DrawableGroup] = self.__groups.copy()
        self.__groups.clear()
        for g in actual_groups:
            if self in g:
                with suppress(ValueError):
                    g.remove(self)
        del actual_groups

    def is_alive(self) -> bool:
        return len(self.__groups) > 0

    @final
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


class DrawableGroup(Sequence[Drawable], Drawable):

    __slots__ = ("__list", "__weakref__")

    def __init__(self, *objects: Drawable, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__list: list[Drawable] = []
        self.add(*objects)

    def __len__(self) -> int:
        return self.__list.__len__()

    @overload
    def __getitem__(self, index: int, /) -> Drawable:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[Drawable]:
        ...

    def __getitem__(self, index: int | slice, /) -> Drawable | Sequence[Drawable]:
        drawable_list: list[Drawable] = self.__list
        return drawable_list[index]

    def __bool__(self) -> bool:
        return self.__len__() > 0

    def draw_onto(self, target: AbstractRenderer) -> None:
        for drawable in self.__list:
            drawable.draw_onto(target)

    def add(self, *objects: Drawable) -> None:
        drawable_list: list[Drawable] = self.__list
        for d in filterfalse(drawable_list.__contains__, objects):
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
        while self:
            self.pop()

    def find(self, objtype: type[_T]) -> Iterator[_T]:
        return filter(lambda obj: isinstance(obj, objtype), self)  # type: ignore[arg-type]


class LayeredDrawableGroup(DrawableGroup):

    __slots__ = ("__default_layer", "__layer_dict")

    def __init__(self, *objects: Drawable, default_layer: int = 0, **kwargs: Any) -> None:
        self.__default_layer: int = default_layer
        self.__layer_dict: WeakKeyDictionary[Drawable, int] = WeakKeyDictionary()
        super().__init__(*objects, **kwargs)

    def add(self, *objects: Drawable, layer: int | None = None) -> None:
        if not objects:
            return
        layer_dict: WeakKeyDictionary[Drawable, int] = self.__layer_dict
        drawable_list: list[Drawable] = getattr_pv(self, "list", owner=DrawableGroup)
        if layer is None:
            layer = self.__default_layer
        for d in filterfalse(drawable_list.__contains__, objects):
            layer_dict.setdefault(d, layer)
            insort_right(drawable_list, d, key=layer_dict.__getitem__)
            if self not in d.groups:
                try:
                    d.add_to_group(self)
                except:
                    drawable_list.remove(d)
                    raise

    def remove(self, *objects: Drawable) -> None:
        super().remove(*objects)
        for d in objects:
            self.__layer_dict.pop(d, None)

    def pop(self, index: int = -1) -> Drawable:
        d: Drawable = super().pop(index=index)
        self.__layer_dict.pop(d, None)
        return d

    def get_layer(self, obj: Drawable) -> int:
        layer_dict: WeakKeyDictionary[Drawable, int] = self.__layer_dict
        try:
            return layer_dict[obj]
        except KeyError:
            raise ValueError("obj not in group") from None

    def change_layer(self, obj: Drawable, layer: int) -> None:
        layer = int(layer)
        layer_dict: WeakKeyDictionary[Drawable, int] = self.__layer_dict
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
        return self.__layer_dict[self[-1]]

    def get_bottom_layer(self) -> int:
        return self.__layer_dict[self[0]]

    def get_top_drawable(self) -> Drawable:
        return self[-1]

    def get_bottom_drawable(self) -> Drawable:
        return self[0]

    def move_to_front(self, obj: Drawable) -> None:
        self.change_layer(obj, self.get_top_layer())

    def move_to_back(self, obj: Drawable, after_last: bool = True) -> None:
        self.change_layer(obj, self.get_bottom_layer() - int(bool(after_last)))

    def iter_in_layer(self, layer: int) -> Iterator[Drawable]:
        return map(
            lambda item: item[0],
            takewhile(
                lambda item: item[1] == layer,
                dropwhile(
                    lambda item: item[1] < layer,
                    self.__layer_dict.items(),
                ),
            ),
        )

    def get_from_layer(self, layer: int) -> Sequence[Drawable]:
        return tuple(self.iter_in_layer(layer))

    def remove_from_layer(self, layer: int) -> Sequence[Drawable]:
        drawable_list: Sequence[Drawable] = self.get_from_layer(layer)
        self.remove(*drawable_list)
        return drawable_list

    def switch_layer(self, layer1: int, layer2: int) -> None:
        change_layer = self.change_layer
        drawable_list_layer1: Sequence[Drawable] = self.remove_from_layer(layer1)
        for d in self.get_from_layer(layer2):
            change_layer(d, layer2)
        self.add(*drawable_list_layer1, layer=layer2)

    @property
    def default_layer(self) -> int:
        return self.__default_layer

    @property
    def layers(self) -> Sequence[int]:
        return sorted(set(self.__layer_dict.values()))
