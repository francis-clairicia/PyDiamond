# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Drawable objects module"""

from __future__ import annotations

__all__ = [
    "Drawable",
    "DrawableGroup",
    "LayeredDrawableGroup",
    "SupportsDrawableGroups",
    "SupportsDrawing",
]

from abc import abstractmethod
from bisect import insort_left, insort_right
from collections import deque
from collections.abc import Iterator, Sequence
from itertools import dropwhile, filterfalse, islice, takewhile
from typing import TYPE_CHECKING, Any, Generic, Protocol, SupportsIndex, TypeVar, overload, runtime_checkable
from weakref import WeakKeyDictionary, WeakSet

from ..system.object import Object

if TYPE_CHECKING:
    from .renderer import AbstractRenderer


@runtime_checkable
class SupportsDrawing(Protocol):
    @abstractmethod
    def draw_onto(self, target: AbstractRenderer) -> None:
        raise NotImplementedError


@SupportsDrawing.register
class Drawable(Object):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.__groups: WeakSet[DrawableGroup[Any]] = WeakSet()

    @abstractmethod
    def draw_onto(self, target: AbstractRenderer) -> None:
        raise NotImplementedError

    def add_to_group(self, *groups: DrawableGroup[Any]) -> None:
        # TODO (3.11): Exception groups
        actual_groups: WeakSet[DrawableGroup[Any]] = self.__groups
        for g in groups:
            actual_groups.add(g)
            if self not in g:
                try:
                    g.add(self)
                except Exception:
                    if self not in g:
                        actual_groups.remove(g)
                    raise

    def remove_from_group(self, *groups: DrawableGroup[Any]) -> None:
        # TODO (3.11): Exception groups
        if not groups:
            return

        failed_to_remove: list[DrawableGroup[Any]] = []
        actual_groups: WeakSet[DrawableGroup[Any]] = self.__groups

        for g in dict.fromkeys(groups):
            try:
                actual_groups.remove(g)
            except KeyError:
                failed_to_remove.append(g)
                continue
            if self in g:
                try:
                    g.remove(self)
                except Exception:
                    if self in g:
                        actual_groups.add(g)
                    failed_to_remove.append(g)
        if failed_to_remove:
            raise ValueError("Failed to remove from several groups", failed_to_remove)

    def has_group(self, group: DrawableGroup[Any]) -> bool:
        return group in self.__groups

    def kill(self) -> None:
        # TODO (3.11): Exception groups
        actual_groups: WeakSet[DrawableGroup[Any]] = self.__groups
        self.__groups = WeakSet()
        failed_to_remove: list[DrawableGroup[Any]] = []
        for g in actual_groups:
            if self in g:
                try:
                    g.remove(self)
                except Exception:
                    if self in g:
                        self.__groups.add(g)
                    failed_to_remove.append(g)
        del actual_groups
        if failed_to_remove:
            raise ValueError("Failed to remove from several groups", failed_to_remove)

    def is_alive(self) -> bool:
        return len(self.__groups) > 0

    def get_groups(self) -> frozenset[DrawableGroup[Any]]:
        return frozenset(self.__groups)


@runtime_checkable
class SupportsDrawableGroups(SupportsDrawing, Protocol):
    @abstractmethod
    def add_to_group(self, *groups: DrawableGroup[Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def remove_from_group(self, *groups: DrawableGroup[Any]) -> None:
        raise NotImplementedError

    @abstractmethod
    def has_group(self, group: DrawableGroup[Any]) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_groups(self) -> frozenset[DrawableGroup[Any]]:
        raise NotImplementedError


_D = TypeVar("_D", bound=SupportsDrawableGroups)


@Sequence.register
class DrawableGroup(Generic[_D]):
    __slots__ = ("data", "__weakref__")

    def __init__(self, *objects: _D, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.data: list[_D] = []
        if objects:
            self.add(*objects)

    def __iter__(self) -> Iterator[_D]:
        return self.data.__iter__()

    def __len__(self) -> int:
        return self.data.__len__()

    def __contains__(self, value: object) -> bool:
        return self.data.__contains__(value)

    @overload
    def __getitem__(self, index: SupportsIndex, /) -> _D: ...

    @overload
    def __getitem__(self, index: slice, /) -> list[_D]: ...

    def __getitem__(self, index: SupportsIndex | slice, /) -> _D | list[_D]:
        return self.data[index]

    def __delitem__(self, index: SupportsIndex | slice, /) -> None:
        if isinstance(index, slice):
            self.remove(*islice(self.data, index.start, index.stop, index.step))
        else:
            self.pop(index)

    def __bool__(self) -> bool:
        return bool(self.data)

    def __reversed__(self) -> Iterator[_D]:
        return self.data.__reversed__()

    def index(self, obj: _D, start: SupportsIndex = 0, stop: SupportsIndex | None = None) -> int:
        if stop is not None:
            return self.data.index(obj, start, stop)
        return self.data.index(obj, start)

    def count(self, obj: _D) -> int:
        return self.data.count(obj)  # Should be 0 or 1 but who knows...

    def draw_onto(self, target: AbstractRenderer) -> None:
        for drawable in self.data:
            drawable.draw_onto(target)

    def add(self, *objects: _D) -> None:
        # TODO (3.11): Exception groups
        drawable_list: list[_D] = self.data
        for d in filterfalse(drawable_list.__contains__, objects):
            drawable_list.append(d)
            if not d.has_group(self):
                try:
                    d.add_to_group(self)
                except BaseException:
                    if not d.has_group(self):
                        drawable_list.remove(d)
                    raise

    def remove(self, *objects: _D) -> None:
        # TODO (3.11): Exception groups
        if not objects:
            return
        drawable_list: list[_D] = self.data
        failed_to_remove: list[_D] = []
        for d in objects:
            try:
                d_idx = drawable_list.index(d)
            except ValueError:
                failed_to_remove.append(d)
                continue
            else:
                del drawable_list[d_idx]
            if d.has_group(self):
                try:
                    d.remove_from_group(self)
                except Exception:
                    if d.has_group(self):
                        drawable_list.insert(d_idx, d)
                    failed_to_remove.append(d)
        if failed_to_remove:
            raise ValueError("Failed to remove self from several objects", failed_to_remove)

    def pop(self, index: SupportsIndex = -1) -> _D:
        index = int(index)
        drawable_list: list[_D] = self.data
        d: _D = drawable_list.pop(index)
        if d.has_group(self):
            try:
                d.remove_from_group(self)
            except Exception:
                if d.has_group(self):
                    if index == -1:
                        drawable_list.append(d)
                    else:
                        if index < 0:
                            index += 1
                        drawable_list.insert(index, d)
                raise
        return d

    def clear(self) -> None:
        # TODO (3.11): Exception groups
        drawable_list: list[_D] = self.data
        failed_to_remove: list[_D] = []
        self.data = []
        for d in drawable_list:
            if d.has_group(self):
                try:
                    d.remove_from_group(self)
                except Exception:
                    if d.has_group(self):
                        self.data.append(d)
                    failed_to_remove.append(d)
        if failed_to_remove:
            raise ValueError("Failed to remove self from several objects", failed_to_remove)


class LayeredDrawableGroup(DrawableGroup[_D]):
    __slots__ = ("__default_layer", "__layer_dict")

    def __init__(self, *objects: _D, default_layer: int = 0, **kwargs: Any) -> None:
        self.__default_layer: int = int(default_layer)
        self.__layer_dict: WeakKeyDictionary[_D, int] = WeakKeyDictionary()
        super().__init__(*objects, **kwargs)

    def add(self, *objects: _D, layer: int | None = None, top_of_layer: bool = True) -> None:
        if not objects:
            return
        insort = insort_right if top_of_layer else insort_left
        layer_dict: WeakKeyDictionary[_D, int] = self.__layer_dict
        drawable_list: list[_D] = self.data
        if layer is None:
            layer = self.__default_layer
        else:
            layer = int(layer)
        for d in filterfalse(drawable_list.__contains__, objects):
            layer_dict.setdefault(d, layer)
            insort(drawable_list, d, key=layer_dict.__getitem__)
            if not d.has_group(self):
                try:
                    d.add_to_group(self)
                except BaseException:
                    if not d.has_group(self):
                        drawable_list.remove(d)
                        layer_dict.pop(d, None)
                    raise
        super().add(*objects)

    def remove(self, *objects: _D) -> None:
        valid_objects = [d for d in objects if d in self.data]
        try:
            super().remove(*objects)
        finally:
            for d in valid_objects:
                if d not in self.data:
                    try:
                        self.__layer_dict.pop(d, None)
                    except TypeError:
                        continue

    def pop(self, index: SupportsIndex = -1) -> _D:
        d: _D = super().pop(index=index)
        self.__layer_dict.pop(d, None)
        return d

    def clear(self) -> None:
        objects = list(self.data)
        try:
            super().clear()
        finally:
            for d in objects:
                if d not in self.data:
                    try:
                        self.__layer_dict.pop(d, None)
                    except TypeError:
                        continue

    def get_layer(self, obj: _D) -> int:
        layer_dict: WeakKeyDictionary[_D, int] = self.__layer_dict
        try:
            return layer_dict[obj]
        except KeyError:
            raise ValueError("obj not in group") from None

    def get_layers(self) -> list[int]:
        return sorted(set(self.__layer_dict.values()) | {self.__default_layer})

    def change_layer(self, obj: _D, layer: int, *, top_of_layer: bool = True) -> None:
        layer = int(layer)
        layer_dict: WeakKeyDictionary[_D, int] = self.__layer_dict
        drawable_list: list[_D] = self.data
        try:
            drawable_list.remove(obj)
        except ValueError:
            raise ValueError("obj not in group") from None
        layer_dict[obj] = layer
        insort = insort_right if top_of_layer else insort_left
        insort(drawable_list, obj, key=layer_dict.__getitem__)

    def get_top_layer(self) -> int:
        if not self.data:
            return self.__default_layer
        return self.__layer_dict[self.data[-1]]

    def get_bottom_layer(self) -> int:
        if not self.data:
            return self.__default_layer
        return self.__layer_dict[self.data[0]]

    def get_top(self) -> _D:
        return self.data[-1]

    def get_bottom(self) -> _D:
        return self.data[0]

    def move_to_front(self, obj: _D, *, before_first: bool = False, top_of_layer: bool = True) -> None:
        if not before_first:
            top_of_layer = True
        self.change_layer(obj, self.get_top_layer() + bool(before_first), top_of_layer=top_of_layer)

    def move_to_back(self, obj: _D, *, after_last: bool = False, top_of_layer: bool = False) -> None:
        if not after_last:
            top_of_layer = False
        self.change_layer(obj, self.get_bottom_layer() - bool(after_last), top_of_layer=top_of_layer)

    def iter_in_layer(self, layer: int) -> Iterator[_D]:
        layer_dict = self.__layer_dict
        return takewhile(
            lambda item: layer_dict[item] == layer,
            dropwhile(
                lambda item: layer_dict[item] < layer,
                self.data,
            ),
        )

    def get_from_layer(self, layer: int) -> Sequence[_D]:
        return list(self.iter_in_layer(layer))

    def remove_layer(self, layer: int) -> Sequence[_D]:
        drawable_list: Sequence[_D] = self.get_from_layer(layer)
        self.remove(*drawable_list)
        return drawable_list

    def reset_layers(self) -> None:
        layer_dict = self.__layer_dict
        default_layer = self.__default_layer
        self.data = sorted(set(self.data), key=lambda obj: layer_dict.setdefault(obj, default_layer))
        for obj in [obj for obj in layer_dict.keys() if obj not in self.data]:
            del layer_dict[obj]

    def switch_layer(self, layer1: int, layer2: int) -> None:
        if layer1 == layer2:
            return
        if layer1 > layer2:
            layer1, layer2 = layer2, layer1

        layer_dict = self.__layer_dict
        drawable_list_layer1: deque[_D] = deque()
        drawable_list_layer2: deque[_D] = deque()
        for item in (
            (item, layer)
            for item in dropwhile(lambda item: layer_dict[item] < layer1, self.data)
            if (layer := layer_dict[item]) <= layer2
        ):
            if item[1] == layer1:
                drawable_list_layer1.append(item[0])
            elif item[1] == layer2:
                drawable_list_layer2.append(item[0])

        change_layer = self.change_layer
        for d in drawable_list_layer2:
            change_layer(d, layer1, top_of_layer=True)
        for d in drawable_list_layer1:
            change_layer(d, layer2, top_of_layer=True)

    @property
    def default_layer(self) -> int:
        return self.__default_layer

    @default_layer.setter
    def default_layer(self, value: int) -> None:
        self.__default_layer = int(value)
