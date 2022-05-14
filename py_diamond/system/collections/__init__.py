# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's collections module"""

__all__ = [
    "OrderedSet",
    "OrderedSetIndexError",
    "OrderedWeakSet",
    "SortedDict",
    "SortedDictItemsView",
    "SortedDictKeysView",
    "SortedDictValuesView",
]

from ._orderedset import OrderedSet, OrderedSetIndexError
from ._orderedweakset import OrderedWeakSet
from ._sorteddict import SortedDict, SortedDictItemsView, SortedDictKeysView, SortedDictValuesView
