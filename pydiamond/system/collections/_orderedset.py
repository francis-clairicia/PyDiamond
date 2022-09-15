# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""OrderedSet module

Credits:
Inspired by the 'ordered-set' project: https://github.com/rspeer/ordered-set

This implementation is a slim copy avoiding features such as Sequence indexing
"""

from __future__ import annotations

__all__ = ["OrderedSet", "OrderedSetIndexError"]


from collections.abc import MutableSet, Sequence, Set
from copy import deepcopy
from threading import RLock
from types import GenericAlias
from typing import Any, Callable, Iterable, Iterator, SupportsIndex


class OrderedSetIndexError(KeyError, IndexError):
    """
    Exception raised when it must be both a KeyError and an IndexError,
    since OrderedSet implements collection.abc.Sequence and collection.abc.MutableSet
    """


class OrderedSet(MutableSet, Sequence):  # type: ignore[type-arg]
    """
    An OrderedSet is a custom MutableSet that remembers its order, so that
    every entry has an index that can be looked up.
    Example:
        >>> OrderedSet([1, 1, 2, 3, 2])
        OrderedSet([1, 2, 3])
    """

    def __init__(self, data: Iterable[object] | None = None, /) -> None:
        self._items: list[object] = []
        self._map: dict[object, int] = {}
        self._lock = RLock()
        if data is not None:
            self.update(data)

    @classmethod
    def _from_iterable(cls, it: Iterable[object]) -> OrderedSet:
        """
        Construct an instance of the class from any iterable input.
        Must override this method if the class constructor signature
        does not accept an iterable for an input.
        """
        return cls(it)

    def __getitem__(self, index: int | slice, /) -> object | OrderedSet:  # type: ignore[override]
        with self._lock:
            if isinstance(index, slice):
                return self._from_iterable(self._items[index])
            return self._items[index]

    def copy(self) -> OrderedSet:
        """
        Return a shallow copy of this object.

        Example:
            >>> this = OrderedSet([1, 2, 3])
            >>> other = this.copy()
            >>> this == other
            True
            >>> this is other
            False
        """
        return self._from_iterable(self)

    __copy__ = copy  # Built-in module 'copy' compatibility

    def __deepcopy__(self, memo: dict[int, Any] | None = None) -> OrderedSet:  # Built-in module 'copy' compatibility
        if memo is None:
            memo = {}
        copy_self = self._from_iterable([])
        memo[id(self)] = copy_self
        copy_self.update(deepcopy(item, memo) for item in self)
        return copy_self

    def add(self, value: object) -> None:
        """
        Add `value` as an item to this OrderedSet.

        If `value` is already in the OrderedSet, does nothing.

        Example:
            >>> oset = OrderedSet()
            >>> oset.add(3)
            >>> oset.add(3)
            >>> print(oset)
            OrderedSet([3])
        """
        with self._lock:
            try:
                self._map[value]  # If the value is not hashable, this will raise a TypeError instead.
            except KeyError:  # Not already here, proceed
                self._map[value] = len(self._items)
                self._items.append(value)

    def update(self, sequence: Iterable[object]) -> None:
        """
        Update the set with the given iterable sequence.

        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset.update([3, 1, 5, 1, 4])
            >>> print(oset)
            OrderedSet([1, 2, 3, 5, 4])
        """
        with self._lock:
            add = self.add
            for item in sequence:
                add(item)

    def index(self, value: object, start: int | None = None, stop: int | None = None) -> int:
        """
        Get the index of a given entry, raising a ValueError if it's not
        present.

        `value` can be an iterable of entries that is not a string, in which case
        this returns a list of indices.

        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset.index(2)
            1
        """
        with self._lock:
            try:
                real_index = self._map[value]
            except KeyError:
                raise ValueError(f"{value!r} not in set") from None

            if start is not None or stop is not None:
                if start is None:
                    start = 0
                elif start < 0:
                    start = max(len(self._items) + start, 0)
                if stop is None:
                    stop = len(self._items)
                elif stop < 0:
                    stop += len(self._items)
                if real_index not in range(start, stop):
                    raise ValueError(f"{value!r} not in set")

            return real_index

    def count(self, value: object) -> int:
        """
        Returns the number of occurrences of `value`

        Optimized version: a Set cannot have more than one occurence
        """
        return 1 if value in self else 0

    def __delitem__(self, index: int) -> None:
        with self._lock:
            if not self._items:
                raise IndexError("index out of range")
            self.pop(index)

    def pop(self, index: int = -1) -> object:
        """
        Remove and return item at index (default last).

        Raises KeyError and IndexError if the set is empty.
        Raises IndexError if index is out of range.

        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset.pop()
            3
        """
        with self._lock:
            if not self._items:
                raise OrderedSetIndexError("pop from an empty set")
            item: object = self._items.pop(index)
            if index == -1:
                self._map.pop(item)
            else:
                index = self._map.pop(item)
                for k, v in ((k, v) for k, v in self._map.items() if v >= index):
                    self._map[k] = v - 1
            return item

    def discard(self, value: object) -> None:
        """
        Remove an element. Do not raise an exception if absent.

        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset.discard(2)
            >>> print(oset)
            OrderedSet([1, 3])
            >>> oset.discard(2)
            >>> print(oset)
            OrderedSet([1, 3])
        """
        with self._lock:
            try:
                self.remove(value)
            except LookupError:
                pass

    def remove(self, value: object) -> None:
        """
        Remove an element. If not a member, raise a KeyError.
        """
        with self._lock:
            index = self._map.pop(value)
            del self._items[index]
            for k, v in ((k, v) for k, v in self._map.items() if v >= index):
                self._map[k] = v - 1

    def clear(self) -> None:
        """
        Remove all items from this OrderedSet.
        """
        with self._lock:
            del self._items[:]
            self._map.clear()

    def reverse(self) -> None:
        """
        Reverse *IN PLACE* this OrderedSet

        Example:
            >>> oset = OrderedSet([1, 2, 3])
            >>> oset.reverse()
            >>> print(oset)
            OrderedSet([3, 2, 1])
        """
        with self._lock:
            self._items.reverse()
            self._map = {item: index for index, item in enumerate(self._items)}

    def sort(self, *, key: Callable[[object], Any] | None = None, reverse: bool = False) -> None:
        """
        Sort *IN PLACE* this OrderedSet

        Example:
            >>> oset = OrderedSet([1, 5, 3, 12, -4])
            >>> oset.sort()
            >>> print(oset)
            OrderedSet([-4, 1, 3, 5, 12])
        """
        with self._lock:
            self._items.sort(key=key, reverse=reverse)
            self._map = {item: index for index, item in enumerate(self._items)}

    def isdisjoint(self, other: Iterable[Any]) -> bool:
        """
        Returns True if two sets have a null intersection.
        """
        with self._lock:
            return not any(value in self for value in other)

    def __repr__(self) -> str:
        data = list(self)
        if not data:
            return f"{self.__class__.__name__}()"
        return f"{self.__class__.__name__}({data!r})"

    __str__ = __repr__

    def __contains__(self, __x: object, /) -> bool:
        """
        Test if the item is in this ordered set.
        Example:
            >>> 1 in OrderedSet([1, 3, 2])
            True
            >>> 5 in OrderedSet([1, 3, 2])
            False
        """
        with self._lock:
            return __x in self._map

    def __iter__(self) -> Iterator[object]:
        """
        Example:
            >>> list(iter(OrderedSet([1, 2, 3])))
            [1, 2, 3]
        """
        with self._lock:
            yield from self._items

    def __reversed__(self) -> Iterator[object]:
        """
        Example:
            >>> list(reversed(OrderedSet([1, 2, 3])))
            [3, 2, 1]
        """
        with self._lock:
            yield from reversed(self._items)

    def __len__(self) -> int:
        """
        Returns the number of unique elements in the ordered set
        Example:
            >>> len(OrderedSet([]))
            0
            >>> len(OrderedSet([1, 2]))
            2
        """
        with self._lock:
            return len(self._items)

    def __bool__(self) -> bool:
        with self._lock:
            return True if self._items else False

    # Define the gritty details of how an OrderedSet is serialized as a pickle.
    def __reduce_ex__(self, protocol: SupportsIndex, /) -> tuple[Any, ...]:
        return type(self)._from_iterable, (list(self),), None

    def __reduce__(self) -> str | tuple[Any, ...]:  # Backward compatibility
        return type(self)._from_iterable, (list(self),), None

    def __eq__(self, other: Any) -> bool:
        """
        Returns true if the containers have the same items. If `other` is a
        Sequence, then order is checked, otherwise it is ignored.
        Example:
            >>> oset = OrderedSet([1, 3, 2])
            >>> oset == [1, 3, 2]
            True
            >>> oset == [1, 2, 3]
            False
            >>> oset == [2, 3]
            False
            >>> oset == OrderedSet([3, 2, 1])
            False
        """
        if isinstance(other, Sequence):
            # Check that this OrderedSet contains the same elements, in the
            # same order, as the other object.
            return list(self) == list(other)
        try:
            it = iter(other)
        except TypeError:  # Non-iterable object
            return NotImplemented
        try:
            other_as_set = set(it)
        except TypeError:  # Non-hashable values in other's values
            return False
        return set(self) == other_as_set

    def __le__(self, other: Any) -> bool:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        return self.issubset(other)

    def __lt__(self, other: Any) -> bool:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        with self._lock:
            return len(self) < len(other) and self.issubset(other)

    def issubset(self, other: Set[object] | Sequence[object]) -> bool:
        """
        Report whether another set contains this set.
        Example:
            >>> OrderedSet([1, 2, 3]).issubset({1, 2})
            False
            >>> OrderedSet([1, 2, 3]).issubset({1, 2, 3, 4})
            True
            >>> OrderedSet([1, 2, 3]).issubset({1, 4, 3, 5})
            False
        """
        with self._lock:
            if len(self) > len(other):  # Fast check for obvious cases
                return False
            return all(item in other for item in self)

    def __ge__(self, other: Any) -> bool:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        return self.issuperset(other)

    def __gt__(self, other: Any) -> bool:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        with self._lock:
            return len(self) > len(other) and self.issuperset(other)

    def issuperset(self, other: Set[object] | Sequence[object]) -> bool:
        """
        Report whether this set contains another set.
        Example:
            >>> OrderedSet([1, 2]).issuperset([1, 2, 3])
            False
            >>> OrderedSet([1, 2, 3, 4]).issuperset({1, 2, 3})
            True
            >>> OrderedSet([1, 4, 3, 5]).issuperset({1, 2, 3})
            False
        """
        with self._lock:
            if len(self) < len(other):  # Fast check for obvious cases
                return False
            return all(item in self for item in other)

    def __or__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        return self.union(other)

    __ror__ = __or__

    def __ior__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        self.update(other)
        return self

    def union(self, *others: Iterable[object]) -> OrderedSet:
        """
        Combines all unique items.
        Each items order is defined by its first appearance.

        Example:
            >>> oset = OrderedSet.union(OrderedSet([3, 1, 4, 1, 5]), [1, 3], [2, 0])
            >>> print(oset)
            OrderedSet([3, 1, 4, 5, 2, 0])
            >>> oset.union([8, 9])
            OrderedSet([3, 1, 4, 5, 2, 0, 8, 9])
            >>> oset | {10}
            OrderedSet([3, 1, 4, 5, 2, 0, 10])
        """
        return self._from_iterable(e for s in (self, *others) for e in s)

    def __and__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        return self.intersection(other)

    __rand__ = __and__

    def __iand__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        self.intersection_update(other)
        return self

    def intersection(self, *others: Iterable[object]) -> OrderedSet:
        """
        Returns elements in common between all others. Order is defined only
        by the first set.

        Example:
            >>> oset = OrderedSet.intersection(OrderedSet([0, 1, 2, 3]), [1, 2, 3])
            >>> print(oset)
            OrderedSet([1, 2, 3])
            >>> oset.intersection([2, 4, 5], [1, 2, 3, 4])
            OrderedSet([2])
            >>> oset.intersection()
            OrderedSet([1, 2, 3])
        """
        with self._lock:
            items: Iterable[object] = self
            if others:
                common = set.intersection(*map(set, others))  # type: ignore[arg-type]
                items = (item for item in self if item in common)
            return self._from_iterable(items)

    def intersection_update(self, *others: Iterable[object]) -> None:
        """
        Update this OrderedSet to keep only items in another set, preserving
        their order in this set.

        Example:
            >>> this = OrderedSet([1, 4, 3, 5, 7])
            >>> other = OrderedSet([9, 7, 1, 3, 2])
            >>> this.intersection_update(other)
            >>> print(this)
            OrderedSet([1, 3, 7])
        """
        if not others:
            return
        with self._lock:
            common = set.intersection(*map(set, others))  # type: ignore[arg-type]
            self._items = items = [item for item in self._items if item in common]
            self._map = {item: index for index, item in enumerate(items)}

    def __sub__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        return self.difference(other)

    def __rsub__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        diff = self._from_iterable(other)
        diff.difference_update(self)
        return diff

    def __isub__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        self.difference_update(other)
        return self

    def difference(self, *others: Iterable[object]) -> OrderedSet:
        """
        Returns all elements that are in this set but not the others.

        Example:
            >>> OrderedSet([1, 2, 3]).difference(OrderedSet([2]))
            OrderedSet([1, 3])
            >>> OrderedSet([1, 2, 3]).difference(OrderedSet([2]), OrderedSet([3]))
            OrderedSet([1])
            >>> OrderedSet([1, 2, 3]) - OrderedSet([2])
            OrderedSet([1, 3])
            >>> OrderedSet([1, 2, 3]).difference()
            OrderedSet([1, 2, 3])
        """
        with self._lock:
            items: Iterable[object] = self
            if others:
                common = set.union(*map(set, others))  # type: ignore[arg-type]
                items = (item for item in self if item not in common)
            return self._from_iterable(items)

    def difference_update(self, *others: Iterable[object]) -> None:
        """
        Update this OrderedSet to remove items from one or more other others.

        Example:
            >>> this = OrderedSet([1, 2, 3])
            >>> this.difference_update(OrderedSet([2, 4]))
            >>> print(this)
            OrderedSet([1, 3])
            >>> this = OrderedSet([1, 2, 3, 4, 5])
            >>> this.difference_update(OrderedSet([2, 4]), OrderedSet([1, 4, 6]))
            >>> print(this)
            OrderedSet([3, 5])
        """
        if not others:
            return
        with self._lock:
            common = set.union(*map(set, others))  # type: ignore[arg-type]
            self._items = items = [item for item in self._items if item not in common]
            self._map = {item: index for index, item in enumerate(items)}

    def __xor__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        return self.symmetric_difference(other)

    def __rxor__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        diff = self._from_iterable(other)
        diff.symmetric_difference_update(self)
        return diff

    def __ixor__(self, other: Any) -> OrderedSet:
        if not isinstance(other, (Sequence, Set)):
            return NotImplemented
        self.symmetric_difference_update(other)
        return self

    def symmetric_difference(self, other: Set[object] | Sequence[object]) -> OrderedSet:
        """
        Return the symmetric difference of two OrderedSets as a new set.
        That is, the new set will contain all elements that are in exactly
        one of the sets.
        Their order will be preserved, with elements from `self` preceding
        elements from `other`.
        Example:
            >>> this = OrderedSet([1, 4, 3, 5, 7])
            >>> other = OrderedSet([9, 7, 1, 3, 2])
            >>> this.symmetric_difference(other)
            OrderedSet([4, 5, 9, 2])
        """
        with self._lock:
            diff1 = self._from_iterable(self).difference(other)
            diff2 = self._from_iterable(other).difference(self)
            return diff1.union(diff2)

    def symmetric_difference_update(self, other: Set[object] | Sequence[object]) -> None:
        """
        Update this OrderedSet to remove items from another set, then
        add items from the other set that were not present in this set.

        Example:
            >>> this = OrderedSet([1, 4, 3, 5, 7])
            >>> other = OrderedSet([9, 7, 1, 3, 2])
            >>> this.symmetric_difference_update(other)
            >>> print(this)
            OrderedSet([4, 5, 9, 2])
        """
        with self._lock:
            items_to_add = [item for item in other if item not in self]
            items_to_remove = set(other)
            self._items = items = [item for item in self._items if item not in items_to_remove] + items_to_add
            self._map = {item: index for index, item in enumerate(items)}

    __class_getitem__ = classmethod(GenericAlias)


if __name__ == "__main__":
    import doctest

    doctest.testmod()
