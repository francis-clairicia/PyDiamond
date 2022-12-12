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
from typing import Any, SupportsIndex, TypeVar, final, overload
from weakref import WeakKeyDictionary, WeakSet, WeakValueDictionary

from _collections_abc import dict_items, dict_keys, dict_values
from _typeshed import Self, SupportsRichComparison, SupportsRichComparisonT

_C_KT = TypeVar("_C_KT", bound=SupportsRichComparison)
_KT = TypeVar("_KT")
_VT = TypeVar("_VT")

_C_KT_co = TypeVar("_C_KT_co", bound=SupportsRichComparison, covariant=True)
_VT_co = TypeVar("_VT_co", covariant=True)

_S = TypeVar("_S")
_T = TypeVar("_T")

@final
class SortedDictKeysView(dict_keys[_C_KT_co, _VT_co], Reversible[_C_KT_co]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[_C_KT_co]: ...

@final
class SortedDictItemsView(dict_items[_C_KT_co, _VT_co], Reversible[tuple[_C_KT_co, _VT_co]]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[tuple[_C_KT_co, _VT_co]]: ...

@final
class SortedDictValuesView(dict_values[_C_KT_co, _VT_co], Reversible[_VT_co]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[_VT_co]: ...

class SortedDict(dict[_C_KT, _VT]):
    @classmethod  # type: ignore[override]
    @overload
    def fromkeys(
        cls, __iterable: Iterable[SupportsRichComparisonT], __value: None = ...
    ) -> SortedDict[SupportsRichComparisonT, Any | None]: ...
    @classmethod
    @overload
    def fromkeys(cls, __iterable: Iterable[SupportsRichComparisonT], __value: _T) -> SortedDict[SupportsRichComparisonT, _T]: ...
    def copy(self: Self) -> Self: ...
    def __copy__(self: Self) -> Self: ...
    def __deepcopy__(self: Self, memo: dict[int, Any] | None = ...) -> Self: ...
    def keys(self) -> SortedDictKeysView[_C_KT, _VT]: ...
    def values(self) -> SortedDictValuesView[_C_KT, _VT]: ...
    def items(self) -> SortedDictItemsView[_C_KT, _VT]: ...

class ChainMapProxy(Mapping[_KT, _VT]):
    maps: list[Mapping[_KT, _VT]]
    def __init__(self, *maps: Mapping[_KT, _VT]) -> None: ...
    def new_child(self: Self, __m: Mapping[_KT, _VT] | None = ..., /, **kwargs: Any) -> Self: ...
    @property
    def parents(self: Self) -> Self: ...
    def __getitem__(self, key: _KT) -> _VT: ...
    def __iter__(self) -> Iterator[_KT]: ...
    def __len__(self) -> int: ...
    def __contains__(self, key: object) -> bool: ...
    def __missing__(self, key: _KT) -> _VT: ...
    def __bool__(self) -> bool: ...
    def copy(self: Self) -> Self: ...
    def __copy__(self: Self) -> Self: ...
    # All arguments to `fromkeys` are passed to `dict.fromkeys` at runtime, so the signature should be kept in line with `dict.fromkeys`.
    @classmethod
    @overload
    def fromkeys(cls, iterable: Iterable[_T], __value: None = ...) -> ChainMapProxy[_T, Any | None]: ...
    @classmethod
    @overload
    def fromkeys(cls, __iterable: Iterable[_T], __value: _S) -> ChainMapProxy[_T, _S]: ...
    def __or__(self, other: Mapping[_S, _T]) -> dict[_KT | _S, _VT | _T]: ...
    def __ror__(self, other: Mapping[_S, _T]) -> dict[_KT | _S, _VT | _T]: ...

class OrderedSetIndexError(KeyError, IndexError): ...

class OrderedSet(MutableSet[_T], Sequence[_T]):
    def __init__(self, data: Iterable[_T] | None = ..., /) -> None: ...
    @classmethod
    def _from_iterable(cls: type[Self], it: Iterable[_T]) -> Self: ...
    @overload
    def __getitem__(self, index: int, /) -> _T: ...
    @overload
    def __getitem__(self: Self, index: slice, /) -> Self: ...
    def copy(self: Self) -> Self: ...
    def __copy__(self: Self) -> Self: ...
    def __deepcopy__(self: Self, memo: dict[int, Any] | None = ...) -> Self: ...
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
    def __or__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def __ror__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __ior__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def union(self: Self, *others: Iterable[_T]) -> Self: ...
    def __and__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __rand__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __iand__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def intersection(self: Self, *others: Iterable[_T]) -> Self: ...
    def intersection_update(self, *others: Iterable[_T]) -> None: ...
    def __sub__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __rsub__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __isub__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def difference(self: Self, *others: Iterable[_T]) -> Self: ...
    def difference_update(self, *others: Iterable[_T]) -> None: ...
    def __xor__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def __rxor__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def __ixor__(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...  # type: ignore[override]
    def symmetric_difference(self: Self, other: AbstractSet[_T] | Sequence[_T]) -> Self: ...
    def symmetric_difference_update(self, other: AbstractSet[_T] | Sequence[_T]) -> None: ...

class OrderedWeakSet(WeakSet[_T], Sequence[_T]):
    @overload
    def __getitem__(self, index: int, /) -> _T: ...
    @overload
    def __getitem__(self: Self, index: slice, /) -> Self: ...
    def __delitem__(self, index: int) -> None: ...

class WeakKeyDefaultDictionary(WeakKeyDictionary[_KT, _VT]):
    @overload
    def __init__(self, __default_factory: Callable[[], _VT] | None = ..., /, dict: None = ...) -> None: ...
    @overload
    def __init__(
        self, __default_factory: Callable[[], _VT] | None, /, dict: Mapping[_KT, _VT] | Iterable[tuple[_KT, _VT]]
    ) -> None: ...
    def __missing__(self, key: _KT) -> _VT: ...
    @property
    def default_factory(self) -> Callable[[], _VT] | None: ...

class WeakValueDefaultDictionary(WeakValueDictionary[_KT, _VT]):
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
