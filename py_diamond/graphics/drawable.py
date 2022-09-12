# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Drawable objects module"""

from __future__ import annotations

__all__ = [
    "BaseDrawableGroup",
    "BaseLayeredDrawableGroup",
    "Drawable",
    "DrawableGroup",
    "LayeredDrawableGroup",
    "SupportsDrawableGroups",
    "SupportsDrawing",
]

from abc import abstractmethod
from bisect import insort_left, insort_right
from collections import deque
from itertools import dropwhile, filterfalse, takewhile
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterator,
    MutableSequence,
    Protocol,
    Sequence,
    TypeVar,
    overload,
    runtime_checkable,
)
from weakref import WeakKeyDictionary, WeakSet

from ..system.object import Object, final
from ..system.utils._mangling import getattr_pv
from ..system.utils.abc import isabstractmethod
from ..system.utils.functools import wraps

if TYPE_CHECKING:
    from .renderer import AbstractRenderer

_T = TypeVar("_T")


def _draw_decorator(func: Callable[[Drawable, AbstractRenderer], None], /) -> Callable[[Drawable, AbstractRenderer], None]:
    @wraps(func)
    def wrapper(self: Drawable, /, target: AbstractRenderer) -> None:
        if self.is_shown():
            func(self, target)

    setattr(wrapper, "__draw_onto_decorator__", True)
    if getattr(func, "__final__", False):
        setattr(wrapper, "__final__", True)
    return wrapper


@runtime_checkable
class SupportsDrawing(Protocol):
    @abstractmethod
    def draw_onto(self, target: AbstractRenderer) -> None:
        raise NotImplementedError


class Drawable(Object):
    __slots__ = ("__weakref__", "__dict__")

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        draw_method: Callable[[Drawable, AbstractRenderer], None] = getattr(cls, "draw_onto")
        if not getattr(draw_method, "__draw_onto_decorator__", False) and not isabstractmethod(draw_method):
            type.__setattr__(cls, "draw_onto", _draw_decorator(draw_method))

        if not hasattr(cls, "__weakref__"):
            raise TypeError("A Drawable object must be weak-referencable")

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__shown: bool = True
        self.__groups: WeakSet[BaseDrawableGroup[Any]] = WeakSet()

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

    def add_to_group(self, *groups: BaseDrawableGroup[Any]) -> None:
        actual_groups: WeakSet[BaseDrawableGroup[Any]] = self.__groups
        for g in filterfalse(actual_groups.__contains__, groups):
            actual_groups.add(g)
            if self not in g:
                try:
                    g.add(self)
                except BaseException:
                    actual_groups.remove(g)
                    raise

    def remove_from_group(self, *groups: BaseDrawableGroup[Any]) -> None:
        if not groups:
            return
        actual_groups: WeakSet[BaseDrawableGroup[Any]] = self.__groups
        for g in groups:
            if g not in actual_groups:
                raise ValueError(f"sprite not in {g!r}")
        for g in groups:
            actual_groups.remove(g)
            if self in g:
                g.remove(self)

    def has_group(self, group: BaseDrawableGroup[Any]) -> bool:
        return group in self.__groups

    def kill(self) -> None:
        actual_groups: WeakSet[BaseDrawableGroup[Any]] = self.__groups
        self.__groups = WeakSet()
        for g in actual_groups:
            if self in g:
                g.remove(self)
        del actual_groups

    def is_alive(self) -> bool:
        return len(self.__groups) > 0

    @property
    @final
    def groups(self) -> frozenset[BaseDrawableGroup[Any]]:
        return frozenset(self.__groups)


@runtime_checkable
class SupportsDrawableGroups(SupportsDrawing, Protocol):
    @abstractmethod
    def add_to_group(self, *groups: BaseDrawableGroup[Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove_from_group(self, *groups: BaseDrawableGroup[Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def has_group(self, group: BaseDrawableGroup[Any]) -> bool:
        raise NotImplementedError


_D = TypeVar("_D", bound=SupportsDrawableGroups)


class BaseDrawableGroup(Sequence[_D]):

    __slots__ = ("__list", "__weakref__")

    def __init__(self, *objects: _D, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__list: MutableSequence[_D] = deque()
        if objects:
            self.add(*objects)

    def __iter__(self) -> Iterator[_D]:
        return self.__list.__iter__()

    def __len__(self) -> int:
        return self.__list.__len__()

    @overload
    def __getitem__(self, index: int, /) -> _D:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[_D]:
        ...

    def __getitem__(self, index: int | slice, /) -> _D | Sequence[_D]:
        return self.__list[index]

    def __bool__(self) -> bool:
        return bool(self.__list)

    def draw_onto(self, target: AbstractRenderer) -> None:
        for drawable in self.__list:
            drawable.draw_onto(target)

    def add(self, *objects: _D) -> None:
        drawable_list: MutableSequence[_D] = self.__list
        for d in filterfalse(drawable_list.__contains__, objects):
            drawable_list.append(d)
            if not d.has_group(self):
                try:
                    d.add_to_group(self)
                except BaseException:
                    drawable_list.remove(d)
                    raise

    def remove(self, *objects: _D) -> None:
        if not objects:
            return
        drawable_list: MutableSequence[_D] = self.__list
        for d in objects:
            if d not in drawable_list:
                raise ValueError(f"{d!r} not in self")
        for d in objects:
            drawable_list.remove(d)
            if d.has_group(self):
                d.remove_from_group(self)

    def pop(self, index: int = -1) -> _D:
        assert isinstance(index, int)
        drawable_list: MutableSequence[_D] = self.__list
        d: _D = drawable_list[index]  # deque.pop() does not accept argument
        del drawable_list[index]
        if d.has_group(self):
            d.remove_from_group(self)
        return d

    def clear(self) -> None:
        drawable_list: MutableSequence[_D] = self.__list
        self.__list = deque()
        for d in drawable_list:
            if d.has_group(self):
                d.remove_from_group(self)

    def find(self, objtype: type[_T]) -> Iterator[_T]:
        return (obj for obj in self if isinstance(obj, objtype))


class DrawableGroup(BaseDrawableGroup[Drawable], Drawable):
    __slots__ = ()


class BaseLayeredDrawableGroup(BaseDrawableGroup[_D]):

    __slots__ = ("__default_layer", "__layer_dict")

    def __init__(self, *objects: _D, default_layer: int = 0, **kwargs: Any) -> None:
        self.__default_layer: int = default_layer
        self.__layer_dict: WeakKeyDictionary[_D, int] = WeakKeyDictionary()
        super().__init__(*objects, **kwargs)

    def add(self, *objects: _D, layer: int | None = None) -> None:
        if not objects:
            return
        layer_dict: WeakKeyDictionary[_D, int] = self.__layer_dict
        drawable_list: MutableSequence[_D] = getattr_pv(self, "list", owner=BaseDrawableGroup)
        if layer is None:
            layer = self.__default_layer
        for d in filterfalse(drawable_list.__contains__, objects):
            layer_dict.setdefault(d, layer)
            insort_right(drawable_list, d, key=layer_dict.__getitem__)
            if not d.has_group(self):
                try:
                    d.add_to_group(self)
                except BaseException:
                    drawable_list.remove(d)
                    raise

    def remove(self, *objects: _D) -> None:
        super().remove(*objects)
        for d in objects:
            self.__layer_dict.pop(d, None)

    def pop(self, index: int = -1) -> _D:
        d: _D = super().pop(index=index)
        self.__layer_dict.pop(d, None)
        return d

    def clear(self) -> None:
        super().clear()
        self.__layer_dict.clear()

    def get_layer(self, obj: _D) -> int:
        layer_dict: WeakKeyDictionary[_D, int] = self.__layer_dict
        try:
            return layer_dict[obj]
        except KeyError:
            raise ValueError("obj not in group") from None

    def change_layer(self, obj: _D, layer: int, *, top_of_layer: bool = True) -> None:
        layer = int(layer)
        layer_dict: WeakKeyDictionary[_D, int] = self.__layer_dict
        actual_layer: int | None = layer_dict.get(obj, None)
        if (actual_layer is None and layer == self.__default_layer) or (actual_layer is not None and actual_layer == layer):
            return
        drawable_list: MutableSequence[_D] = getattr_pv(self, "list", owner=BaseDrawableGroup)
        try:
            drawable_list.remove(obj)
        except ValueError:
            raise ValueError("obj not in group") from None
        layer_dict[obj] = layer
        insort = insort_right if top_of_layer else insort_left
        insort(drawable_list, obj, key=layer_dict.__getitem__)

    def get_top_layer(self) -> int:
        return self.__layer_dict[self[-1]]

    def get_bottom_layer(self) -> int:
        return self.__layer_dict[self[0]]

    def get_top_drawable(self) -> _D:
        return self[-1]

    def get_bottom_drawable(self) -> _D:
        return self[0]

    def move_to_front(self, obj: _D, *, top_of_layer: bool = True) -> None:
        self.change_layer(obj, self.get_top_layer(), top_of_layer=top_of_layer)

    def move_to_back(self, obj: _D, *, after_last: bool = True, top_of_layer: bool = False) -> None:
        self.change_layer(obj, self.get_bottom_layer() - int(bool(after_last)), top_of_layer=top_of_layer)

    def iter_in_layer(self, layer: int) -> Iterator[_D]:
        layer_dict = self.__layer_dict
        drawable_list: MutableSequence[_D] = getattr_pv(self, "list", owner=BaseDrawableGroup)
        return takewhile(
            lambda item: layer_dict[item] == layer,
            dropwhile(
                lambda item: layer_dict[item] < layer,
                drawable_list,
            ),
        )

    def get_from_layer(self, layer: int) -> Sequence[_D]:
        return list(self.iter_in_layer(layer))

    def remove_from_layer(self, layer: int) -> Sequence[_D]:
        drawable_list: Sequence[_D] = self.get_from_layer(layer)
        self.remove(*drawable_list)
        return drawable_list

    def switch_layer(self, layer1: int, layer2: int) -> None:
        change_layer = self.change_layer
        drawable_list_layer1: Sequence[_D] = self.remove_from_layer(layer1)
        for d in self.get_from_layer(layer2):
            change_layer(d, layer2, top_of_layer=True)
        self.add(*drawable_list_layer1, layer=layer2)

    @property
    def default_layer(self) -> int:
        return self.__default_layer

    @property
    def layers(self) -> Sequence[int]:
        return sorted(set(self.__layer_dict.values()) | {self.default_layer})


class LayeredDrawableGroup(BaseLayeredDrawableGroup[Drawable], Drawable):
    __slots__ = ()
