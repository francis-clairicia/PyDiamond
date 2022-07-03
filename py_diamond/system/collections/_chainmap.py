# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ChainMap-like module"""

from __future__ import annotations

__all__ = ["ChainMapProxy"]

import reprlib
from collections.abc import Mapping
from typing import Any, Iterable, Iterator


class ChainMapProxy(Mapping):  # type: ignore[type-arg]
    """A variant of collections.ChainMap which is a read-only mapping, supporting either mutable or proxy mappings"""

    def __init__(self, *maps: Mapping[Any, Any]) -> None:
        self.maps: list[Mapping[Any, Any]] = list(maps) or [{}]  # always at least one map

    def __missing__(self, key: Any) -> Any:
        raise KeyError(key)

    def __getitem__(self, key: Any) -> Any:
        for mapping in self.maps:
            try:
                return mapping[key]  # can't use 'key in mapping' with defaultdict
            except KeyError:
                pass
        return self.__missing__(key)  # support subclasses that define __missing__

    def get(self, key: Any, default: Any = None) -> Any:
        return self[key] if key in self else default

    def __len__(self) -> int:
        return len(set().union(*self.maps))  # reuses stored hash values if possible

    def __iter__(self) -> Iterator[Any]:
        d = {}
        for mapping in reversed(self.maps):
            d.update(dict.fromkeys(mapping))  # reuses stored hash values if possible
        return iter(d)

    def __contains__(self, key: object) -> bool:
        return any(key in m for m in self.maps)

    def __bool__(self) -> bool:
        return any(self.maps)

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({", ".join(map(repr, self.maps))})'

    @classmethod
    def fromkeys(cls, iterable: Iterable[Any], *args: Any) -> ChainMapProxy:
        """Create a ChainMapProxy with a single dict created from the iterable."""
        return cls(dict.fromkeys(iterable, *args))

    def copy(self) -> ChainMapProxy:
        """New ChainMapProxy or subclass with refs to maps"""
        return self.__class__(*self.maps)

    __copy__ = copy  # Force use copy() method for 'copy' module, in order not to reduce the object

    def new_child(self, __m: Any = None, /, **kwargs: Any) -> ChainMapProxy:
        """New ChainMapProxy with a new map followed by all previous maps.
        If no map is provided, an empty dict is used.
        Keyword arguments update the map or new empty dict.
        """
        if __m is None:
            __m = kwargs
        elif kwargs:
            __m.update(kwargs)
        return self.__class__(__m, *self.maps)

    @property
    def parents(self) -> ChainMapProxy:
        """New ChainMapProxy from maps[1:]."""
        return self.__class__(*self.maps[1:])

    def __or__(self, other: Any) -> dict[Any, Any]:
        if not isinstance(other, Mapping):
            return NotImplemented
        return dict(self) | dict(other)

    def __ror__(self, other: Any) -> dict[Any, Any]:
        if not isinstance(other, Mapping):
            return NotImplemented
        return dict(other) | dict(self)
