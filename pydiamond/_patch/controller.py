# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Controller patch module

Currently, there is a BIG issue with pygame._sdl2.controller module, BUT I want the controller mapping system X)
Therefore, here is a class trying to fix that problem in Python side.
"""

from __future__ import annotations

__all__ = ["Controller"]

from functools import wraps
from typing import TYPE_CHECKING, Any

import pygame._sdl2.controller as _pg_controller
from typing_extensions import final

try:
    Controller: type[_pg_controller.Controller] = _pg_controller._PyDiamondPatchedController  # type: ignore[attr-defined]
except AttributeError:

    @final
    class Controller(_pg_controller.Controller):  # type: ignore[no-redef]
        __qualname__ = _pg_controller.Controller.__qualname__
        __module__ = _pg_controller.Controller.__module__

        @wraps(_pg_controller.Controller.__init_subclass__)
        def __init_subclass__(cls) -> None:
            raise TypeError(f"{cls.__module__}.{cls.__qualname__} cannot be subclassed")

        @wraps(_pg_controller.Controller.__new__)
        def __new__(cls, index: int) -> Any:
            controllers: list[_pg_controller.Controller] = getattr(_pg_controller.Controller, "_controllers")
            try:
                return next(c for c in controllers if getattr(c, "id") == index)
            except StopIteration:
                return super().__new__(cls)

        @wraps(_pg_controller.Controller.__init__)
        def __init__(self, index: int) -> None:
            if index != self.id or not self.get_init():
                super().__init__(index)

        def __eq__(self, other: object, /) -> bool:
            if not isinstance(other, self.__class__):
                return NotImplemented
            return self.id == other.id

        def __ne__(self, other: object, /) -> bool:
            return not (self == other)

        def __hash__(self) -> int:
            return hash((self.__class__, self.id))

        if TYPE_CHECKING:

            @property
            def id(self) -> int:
                ...

    _pg_controller._PyDiamondPatchedController = Controller  # type: ignore[attr-defined]
