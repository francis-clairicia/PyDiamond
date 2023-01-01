# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Grid widget module"""

from __future__ import annotations

__all__ = ["Grid", "GridElement", "GridJustify"]

from typing import TYPE_CHECKING, Any, Callable, Container, TypeVar

from typing_extensions import final

from ...graphics.color import BLACK, TRANSPARENT, Color
from ..scene import GUIScene
from ..tools._grid import AbstractGUIGrid as _BaseGrid, AbstractGUIScrollableGrid as _BaseScrollableGrid, GridElement, GridJustify
from .abc import AbstractWidget, WidgetsManager
from .scroll import AbstractScrollableWidget

if TYPE_CHECKING:
    from weakref import WeakMethod

_E = TypeVar("_E", bound=GridElement)


class Grid(_BaseGrid, AbstractWidget, Container[AbstractWidget | GridElement]):
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        *,
        uniform_cell_size: bool = False,
        bg_color: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        padx: int = 0,
        pady: int = 0,
        justify: GridJustify = GridJustify.CENTER,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            # Grid
            uniform_cell_size=uniform_cell_size,
            bg_color=bg_color,
            outline=outline,
            outline_color=outline_color,
            padx=padx,
            pady=pady,
            justify=justify,
            # AbstractWidget
            master=master,
            # Other
            **kwargs,
        )

    def _child_removed(self, child: AbstractWidget) -> None:
        super()._child_removed(child)
        if child in self:
            self.remove(child)

    def place(
        self,
        obj: _E,
        row: int,
        column: int,
        *,
        padx: int | None = None,
        pady: int | None = None,
        justify: str | None = None,
    ) -> _E:
        if isinstance(obj, AbstractWidget):
            self._check_is_child(obj)
        return super().place(obj, row, column, padx=padx, pady=pady, justify=justify)

    @final
    def _get_gui_scene(self) -> GUIScene | None:
        return scene if isinstance((scene := self.scene), GUIScene) else None


class ScrollableGrid(Grid, _BaseScrollableGrid, AbstractScrollableWidget):
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        width: int,
        height: int,
        *,
        uniform_cell_size: bool = False,
        bg_color: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        padx: int = 0,
        pady: int = 0,
        justify: GridJustify = GridJustify.CENTER,
        xscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = None,
        yscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = None,
        wheel_xscroll_increment: int = 10,
        wheel_yscroll_increment: int = 10,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            # Grid
            master=master,
            uniform_cell_size=uniform_cell_size,
            bg_color=bg_color,
            outline=outline,
            outline_color=outline_color,
            padx=padx,
            pady=pady,
            justify=justify,
            # AbstractScrollableWidget
            xscrollcommand=xscrollcommand,
            yscrollcommand=yscrollcommand,
            wheel_xscroll_increment=wheel_xscroll_increment,
            wheel_yscroll_increment=wheel_yscroll_increment,
            # Other
            **kwargs,
        )

        self.__size: tuple[int, int] = int(width), int(height)

    def get_size(self) -> tuple[int, int]:
        return self.__size

    def set_size(self, size: tuple[int, int]) -> None:
        width, height = size
        self.__size = int(width), int(height)
        self.update_view(force=True)
