# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""SortedDict module"""

from __future__ import annotations

__all__ = ["SortedDict", "SortedDictItemsView", "SortedDictKeysView", "SortedDictValuesView"]


import reprlib
from bisect import insort_right as insort
from collections.abc import ItemsView, KeysView, Reversible, ValuesView
from copy import deepcopy
from typing import Any, Iterator


class SortedDictKeysView(KeysView, Reversible):  # type: ignore[type-arg]
    __slots__ = ()
    _mapping: dict[Any, Any]

    def __init_subclass__(cls) -> None:
        raise TypeError("Cannot be subclassed")

    def __reversed__(self) -> Iterator[Any]:
        return reversed(self._mapping)


class SortedDictValuesView(ValuesView, Reversible):  # type: ignore[type-arg]
    __slots__ = ()
    _mapping: dict[Any, Any]

    def __init_subclass__(cls) -> None:
        raise TypeError("Cannot be subclassed")

    def __reversed__(self) -> Iterator[Any]:
        mapping = self._mapping
        return (mapping[key] for key in reversed(mapping))


class SortedDictItemsView(ItemsView, Reversible):  # type: ignore[type-arg]
    __slots__ = ()
    _mapping: dict[Any, Any]

    def __init_subclass__(cls) -> None:
        raise TypeError("Cannot be subclassed")

    def __reversed__(self) -> Iterator[tuple[Any, Any]]:
        mapping = self._mapping
        return ((key, mapping[key]) for key in reversed(mapping))


class SortedDict(dict):  # type: ignore[type-arg]
    __slots__ = ("__list",)  # No weakref support like the built-in base class

    __list: list[Any]

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        self = super().__new__(cls, *args, **kwargs)
        self.__list = []
        return self

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.__list[:] = sorted(super().__iter__())

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({{{', '.join(f'{key!r}: {self[key]!r}' for key in self)}}})"

    def __iter__(self) -> Iterator[Any]:
        yield from self.__list

    def __reversed__(self) -> Iterator[Any]:
        yield from reversed(self.__list)

    def __setitem__(self, __k: Any, __v: Any, /) -> None:
        super().__setitem__(__k, __v)
        if __k not in self.__list:
            try:
                insort(self.__list, __k)
            except BaseException:
                super().__delitem__(__k)
                raise

    def __delitem__(self, __k: Any, /) -> None:
        super().__delitem__(__k)
        self.__list.remove(__k)

    def clear(self) -> None:
        super().clear()
        self.__list.clear()

    def copy(self) -> SortedDict:
        return self.__class__(self)

    def pop(self, __key: Any, /, *__default: Any) -> Any:
        value = super().pop(__key, *__default)
        try:
            self.__list.remove(__key)
        except ValueError:
            pass
        return value

    def popitem(self) -> tuple[Any, Any]:
        if not self:
            return super().popitem()  # keep default behavior (raise an Exception)
        key = self.__list.pop()
        return key, super().pop(key)

    def setdefault(self, __key: Any, /, *__default: Any) -> Any:
        value = super().setdefault(__key, *__default)
        if __key not in self.__list:
            try:
                insort(self.__list, __key)
            except BaseException:
                super().__delitem__(__key)
                raise
        return value

    def update(self, *__m: Any, **kwargs: Any) -> None:
        payload = super().copy()
        payload.update(*__m, **kwargs)  # Check unhasable keys
        keys = sorted(payload)  # Check support of comparison
        # All validated, proceed
        super().update(payload)
        self.__list = keys

    def __ior__(self, __value: Any) -> SortedDict:  # type: ignore[misc]
        self.update(__value)
        return self

    __copy__ = copy  # Force use copy() method for 'copy' module, in order not to reduce the object

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> SortedDict:  # deep copy optimization
        if memo is None:
            memo = {}
        copy_self = self.__class__()
        memo[id(self)] = copy_self
        for key in self:
            copy_self[deepcopy(key, memo)] = deepcopy(self[key], memo)
        return copy_self

    def keys(self) -> SortedDictKeysView:  # type: ignore[override]
        return SortedDictKeysView(self)

    def values(self) -> SortedDictValuesView:  # type: ignore[override]
        return SortedDictValuesView(self)

    def items(self) -> SortedDictItemsView:  # type: ignore[override]
        return SortedDictItemsView(self)
