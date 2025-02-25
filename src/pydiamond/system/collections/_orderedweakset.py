# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""OrderedWeakSet module"""

from __future__ import annotations

__all__ = ["OrderedWeakSet"]

from collections.abc import Iterator, Sequence
from typing import TYPE_CHECKING, Any, Self
from weakref import WeakSet, ref

if TYPE_CHECKING:  # Too many type errors :)

    class _IterationGuard:
        def __init__(self, weakcontainer: WeakSet[Any]) -> None: ...

        def __enter__(self) -> Self: ...

        def __exit__(self, *args: Any) -> None: ...

else:
    from _weakrefset import _IterationGuard

from ._orderedset import OrderedSet


class OrderedWeakSet[_T](WeakSet[_T], Sequence[_T]):
    def __init__(self, data: Any = None):
        super().__init__()
        self.data: OrderedSet[ref[_T]] = OrderedSet()  # Replace underlying set by an OrderedSet instance
        self._pending_removals: list[ref[object]]  # Private attribute from WeakSet
        if data is not None:
            self.update(data)

    if TYPE_CHECKING:

        def _commit_removals(self) -> None:  # Private method from WeakSet
            ...

    def __getitem__(self, index: int | slice) -> Any:
        if self._pending_removals:
            self._commit_removals()
        if isinstance(index, slice):
            with _IterationGuard(self):
                return self.__class__(item for itemref in self.data[index] if (item := itemref()) is not None)
        if not isinstance(index, int):
            raise TypeError(f"indices must be integers or slices, not {type(index).__name__}")
        if index >= 0:
            while (obj := self.data[index]()) is None:
                index += 1
        else:
            while (obj := self.data[index]()) is None:
                index += 1
                if index == 0:
                    raise IndexError("out of range")
        return obj

    def __delitem__(self, index: int | slice) -> None:
        if isinstance(index, slice):
            raise TypeError("Slice are not accepted")
        self.discard(self[index])

    def __reversed__(self) -> Iterator[_T]:
        with _IterationGuard(self):
            for itemref in reversed(self.data):
                item = itemref()
                if item is not None:
                    # Caveat: the iterator will keep a strong reference to
                    # `item` until it is resumed or closed.
                    yield item

    def count(self, value: Any) -> int:
        return 1 if value in self else 0

    def index(self, value: Any, *args: Any, **kwargs: Any) -> int:
        if self._pending_removals:
            self._commit_removals()
        return self.data.index(ref(value), *args, **kwargs)
