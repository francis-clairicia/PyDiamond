# isort: dont-add-imports

__all__ = [
    "ChainMapProxy",
    "OrderedSet",
    "OrderedSetIndexError",
    "OrderedWeakSet",
    "SortedDict",
    "SortedDictItemsView",
    "SortedDictKeysView",
    "SortedDictValuesView",
    "WeakKeyDefaultDictionary",
    "WeakValueDefaultDictionary",
]

from collections.abc import Callable, Iterable, Iterator, Mapping, MutableSet, Reversible, Sequence, Set as AbstractSet
from typing import Any, Self, SupportsIndex, final, overload
from weakref import WeakKeyDictionary, WeakSet, WeakValueDictionary

from _collections_abc import dict_items, dict_keys, dict_values
from _typeshed import SupportsRichComparison

@final
class SortedDictKeysView[_KT: SupportsRichComparison, _VT](dict_keys[_KT, _VT], Reversible[_KT]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[_KT]: ...

@final
class SortedDictItemsView[_KT: SupportsRichComparison, _VT](dict_items[_KT, _VT], Reversible[tuple[_KT, _VT]]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[tuple[_KT, _VT]]: ...

@final
class SortedDictValuesView[_KT: SupportsRichComparison, _VT](dict_values[_KT, _VT], Reversible[_VT]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[_VT]: ...

class SortedDict[_KT: SupportsRichComparison, _VT](dict[_KT, _VT]):
    @classmethod  # type: ignore[override]
    @overload
    def fromkeys(cls, __iterable: Iterable[_KT], __value: None = ..., /) -> SortedDict[_KT, Any | None]: ...
    @classmethod
    @overload
    def fromkeys(cls, __iterable: Iterable[_KT], __value: _VT, /) -> Self: ...
    def copy(self) -> Self: ...
    def __copy__(self) -> Self: ...
    def __deepcopy__(self, memo: dict[int, Any]) -> Self: ...
    def keys(self) -> SortedDictKeysView[_KT, _VT]: ...
    def values(self) -> SortedDictValuesView[_KT, _VT]: ...
    def items(self) -> SortedDictItemsView[_KT, _VT]: ...

class ChainMapProxy[_KT, _VT](Mapping[_KT, _VT]):
    maps: list[Mapping[_KT, _VT]]
    def __init__(self, *maps: Mapping[_KT, _VT]) -> None: ...
    def new_child(self, __m: Mapping[_KT, _VT] | None = ..., /, **kwargs: Any) -> Self: ...
    @property
    def parents(self) -> Self: ...
    def __getitem__(self, key: _KT) -> _VT: ...
    def __iter__(self) -> Iterator[_KT]: ...
    def __len__(self) -> int: ...
    def __contains__(self, key: object) -> bool: ...
    def __missing__(self, key: _KT) -> _VT: ...
    def __bool__(self) -> bool: ...
    def copy(self) -> Self: ...
    def __copy__(self) -> Self: ...
    # All arguments to `fromkeys` are passed to `dict.fromkeys` at runtime, so the signature should be kept in line with `dict.fromkeys`.
    @classmethod
    @overload
    def fromkeys(cls, iterable: Iterable[_KT], __value: None = ..., /) -> ChainMapProxy[_KT, Any | None]: ...
    @classmethod
    @overload
    def fromkeys(cls, __iterable: Iterable[_KT], __value: _VT, /) -> ChainMapProxy[_KT, _VT]: ...
    def __or__[_S, _T](self, other: Mapping[_S, _T]) -> dict[_KT | _S, _VT | _T]: ...
    def __ror__[_S, _T](self, other: Mapping[_S, _T]) -> dict[_KT | _S, _VT | _T]: ...

class OrderedSetIndexError(KeyError, IndexError): ...

class OrderedSet[_T](MutableSet[_T], Sequence[_T]):
    def __init__(self, data: Iterable[_T] | None = ..., /) -> None: ...
    @classmethod
    def _from_iterable(cls: type[Self], it: Iterable[_T]) -> Self: ...
    @overload
    def __getitem__(self, index: int, /) -> _T: ...
    @overload
    def __getitem__(self, index: slice, /) -> Self: ...
    def copy(self) -> Self: ...
    def __copy__(self) -> Self: ...
    def __deepcopy__(self, memo: dict[int, Any]) -> Self: ...
    def add(self, value: _T) -> None: ...
    def update(self, sequence: Iterable[_T]) -> None: ...
    def index(self, value: _T, start: int = ..., stop: int = ...) -> int: ...
    def count(self, value: _T) -> int: ...
    def __delitem__(self, index: int) -> None: ...
    def pop(self, index: int = ...) -> _T: ...
    def discard(self, value: _T) -> None: ...
    def remove(self, value: _T) -> None: ...
    def clear(self) -> None: ...
    def reverse(self) -> None: ...
    def sort(self, *, key: Callable[[_T], SupportsRichComparison] | None = ..., reverse: bool = ...) -> None: ...
    def isdisjoint(self, other: Iterable[_T]) -> bool: ...
    def __contains__(self, __x: object, /) -> bool: ...
    def __iter__(self) -> Iterator[_T]: ...
    def __reversed__(self) -> Iterator[_T]: ...
    def __len__(self) -> int: ...
    def __bool__(self) -> bool: ...
    def __reduce_ex__(self, protocol: SupportsIndex, /) -> tuple[Any, ...]: ...
    def __reduce__(self) -> str | tuple[Any, ...]: ...
    def __eq__(self, other: object) -> bool: ...
    def __le__(self, other: Any) -> bool: ...
    def __lt__(self, other: Any) -> bool: ...
    def issubset(self, other: AbstractSet[_T] | Sequence[_T]) -> bool: ...
    def __ge__(self, other: Any) -> bool: ...
    def __gt__(self, other: Any) -> bool: ...
    def issuperset(self, other: AbstractSet[_T] | Sequence[_T]) -> bool: ...
    def __or__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def __ror__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __ior__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def union(self, *others: Iterable[_T]) -> Self: ...
    def __and__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __rand__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __iand__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def intersection(self, *others: Iterable[_T]) -> Self: ...
    def intersection_update(self, *others: Iterable[_T]) -> None: ...
    def __sub__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __rsub__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __isub__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def difference(self, *others: Iterable[_T]) -> Self: ...
    def difference_update(self, *others: Iterable[_T]) -> None: ...
    def __xor__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def __rxor__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __ixor__(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def symmetric_difference(self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def symmetric_difference_update(self, other: AbstractSet[_T] | Sequence[_T]) -> None: ...

class OrderedWeakSet[_T](WeakSet[_T], Sequence[_T]):
    @overload
    def __getitem__(self, index: int, /) -> _T: ...
    @overload
    def __getitem__(self, index: slice, /) -> Self: ...
    def __delitem__(self, index: int) -> None: ...

class WeakKeyDefaultDictionary[_KT, _VT](WeakKeyDictionary[_KT, _VT]):
    @overload
    def __init__(self, __default_factory: Callable[[], _VT] | None = ..., /, dict: None = ...) -> None: ...
    @overload
    def __init__(
        self, __default_factory: Callable[[], _VT] | None, /, dict: Mapping[_KT, _VT] | Iterable[tuple[_KT, _VT]]
    ) -> None: ...
    def __missing__(self, key: _KT) -> _VT: ...
    @property
    def default_factory(self) -> Callable[[], _VT] | None: ...

class WeakValueDefaultDictionary[_KT, _VT](WeakValueDictionary[_KT, _VT]):
    @overload
    def __init__(self, __default_factory: Callable[[], _VT] | None = ..., /) -> None: ...
    @overload
    def __init__(
        self: WeakValueDefaultDictionary[_KT, _VT],
        __default_factory: Callable[[], _VT] | None,
        __other: Mapping[_KT, _VT] | Iterable[tuple[_KT, _VT]],
        /,
    ) -> None: ...
    @overload
    def __init__(
        self: WeakValueDefaultDictionary[str, _VT],
        __default_factory: Callable[[], _VT] | None = ...,
        __other: Mapping[str, _VT] | Iterable[tuple[str, _VT]] = ...,
        /,
        **kwargs: _VT,
    ) -> None: ...
    def __missing__(self, key: _KT) -> _VT: ...
    @property
    def default_factory(self) -> Callable[[], _VT] | None: ...
