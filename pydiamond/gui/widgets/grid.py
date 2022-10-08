# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Grid widget module"""

from __future__ import annotations

__all__ = ["Grid", "GridElement", "GridJustify"]

from typing import Any, Container, TypeVar, final

from ...graphics.color import BLACK, TRANSPARENT, Color
from .._grid import AbstractGUIGrid as _BaseGrid, GridElement, GridJustify
from ..scene import GUIScene
from .abc import AbstractWidget, WidgetsManager

_E = TypeVar("_E", bound=GridElement)


class Grid(_BaseGrid, AbstractWidget, Container[AbstractWidget | GridElement]):
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        *,
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
            bg_color=bg_color,
            outline=outline,
            outline_color=outline_color,
            padx=padx,
            pady=pady,
            justify=justify,
            # AbstractWidgetContainer
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
