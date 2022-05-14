# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#

__all__ = ["SortedDict", "SortedDictItemsView", "SortedDictKeysView", "SortedDictValuesView"]

from typing import Any, Iterable, Iterator, Reversible, TypeVar, final, overload

from _collections_abc import dict_items, dict_keys, dict_values
from _typeshed import Self, SupportsRichComparison, SupportsRichComparisonT

_KT = TypeVar("_KT", bound=SupportsRichComparison)
_VT = TypeVar("_VT")

_KT_co = TypeVar("_KT_co", bound=SupportsRichComparison, covariant=True)
_VT_co = TypeVar("_VT_co", covariant=True)

_S = TypeVar("_S")

@final
class SortedDictKeysView(dict_keys[_KT_co, _VT_co], Reversible[_KT_co]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[_KT_co]: ...

@final
class SortedDictItemsView(dict_items[_KT_co, _VT_co], Reversible[tuple[_KT_co, _VT_co]]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[tuple[_KT_co, _VT_co]]: ...

@final
class SortedDictValuesView(dict_values[_KT_co, _VT_co], Reversible[_VT_co]):  # type: ignore[misc]
    def __reversed__(self) -> Iterator[_VT_co]: ...

class SortedDict(dict[_KT, _VT]):
    @classmethod  # type: ignore[override]
    @overload
    def fromkeys(cls, __iterable: Iterable[SupportsRichComparisonT], __value: None = ...) -> SortedDict[SupportsRichComparisonT, Any | None]: ...
    @classmethod
    @overload
    def fromkeys(cls, __iterable: Iterable[SupportsRichComparisonT], __value: _S) -> SortedDict[SupportsRichComparisonT, _S]: ...
    def copy(self: Self) -> Self: ...
    def __copy__(self: Self) -> Self: ...
    def __deepcopy__(self: Self, memo: dict[int, Any] | None = ...) -> Self: ...
    def keys(self) -> SortedDictKeysView[_KT, _VT]: ...
    def values(self) -> SortedDictValuesView[_KT, _VT]: ...
    def items(self) -> SortedDictItemsView[_KT, _VT]: ...
