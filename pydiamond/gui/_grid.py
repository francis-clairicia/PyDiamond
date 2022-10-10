# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI Grid module"""

from __future__ import annotations

__all__ = ["AbstractGUIGrid", "AbstractGUIScrollableGrid", "GridElement", "GridJustify"]


from abc import abstractmethod
from functools import reduce
from itertools import starmap
from typing import TYPE_CHECKING, Any, Callable, Literal, Sequence, TypeVar

from ..graphics.grid import Grid as _Grid, GridElement, GridJustify
from ..math.rect import Rect
from ..system.collections import SortedDict
from .focus import supports_focus
from .scene import GUIScene
from .tools.view import AbstractScrollableView

if TYPE_CHECKING:
    from weakref import WeakMethod

    from ..graphics.color import Color
    from ..graphics.grid import _GridCell
    from .focus import SupportsFocus


_E = TypeVar("_E", bound=GridElement)


class _Grid(_Grid):  # type: ignore[no-redef]
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
        scene = self._get_gui_scene()
        if scene is not None and supports_focus(obj) and not obj.focus.is_bound_to(scene):
            raise ValueError("'obj' do not have the same GUIScene master that self")
        return super().place(obj, row, column, padx=padx, pady=pady, justify=justify)

    def _update(self) -> None:
        self.__set_obj_on_side_internal()
        self.__update_size()  # Should not work but it's magic

    def __set_obj_on_side_internal(self) -> None:
        all_rows: SortedDict[int, list[_GridCell]] = SortedDict()
        all_columns: SortedDict[int, list[_GridCell]] = SortedDict()
        self.__remove_useless_cells(all_rows=all_rows, all_columns=all_columns)  # Should not work as well X)

        if not all_rows and not all_columns:
            return

        find_closest = self.__find_closest
        all_column_indexes: Sequence[int] = tuple(all_columns)
        for index, column in enumerate(all_column_indexes):
            for cell in all_columns[column]:
                obj: Any | None = cell.get_object()
                if obj is None or not supports_focus(obj):
                    continue
                left_obj: SupportsFocus | None = None
                right_obj: SupportsFocus | None = None
                if index > 0:
                    left_obj = find_closest(all_columns[all_column_indexes[index - 1]], "row", cell)
                if index < len(all_column_indexes) - 1:
                    right_obj = find_closest(all_columns[all_column_indexes[index + 1]], "row", cell)
                if left_obj is not None:
                    obj.focus.set_obj_on_side(on_left=left_obj)
                if right_obj is not None:
                    obj.focus.set_obj_on_side(on_right=right_obj)

        all_row_indexes: Sequence[int] = tuple(all_rows)
        for index, row in enumerate(all_row_indexes):
            for cell in all_rows[row]:
                obj = cell.get_object()
                if obj is None or not supports_focus(obj):
                    continue
                top_obj: SupportsFocus | None = None
                bottom_obj: SupportsFocus | None = None
                if index > 0:
                    top_obj = find_closest(all_rows[all_row_indexes[index - 1]], "column", cell)
                if index < len(all_row_indexes) - 1:
                    bottom_obj = find_closest(all_rows[all_row_indexes[index + 1]], "column", cell)
                if top_obj is not None:
                    obj.focus.set_obj_on_side(on_top=top_obj)
                if bottom_obj is not None:
                    obj.focus.set_obj_on_side(on_bottom=bottom_obj)

    @staticmethod
    def __find_closest(
        cells: Sequence[_GridCell], attr: Literal["row", "column"], cell_to_link: _GridCell
    ) -> SupportsFocus | None:
        closest: _GridCell | None = None
        closest_obj: SupportsFocus | None = None
        value: int = getattr(cell_to_link, attr)
        for cell in cells:
            obj: Any = cell.get_object()
            if obj is None or not supports_focus(obj):
                continue
            if (cell_value := int(getattr(cell, attr))) == value:
                return obj
            if closest is None:
                closest = cell
                closest_obj = obj
                continue
            closest_value: int = int(getattr(closest, attr))
            closest_diff: int = abs(closest_value - value)
            actual_diff: int = abs(cell_value - value)
            if actual_diff < closest_diff or (actual_diff == closest_diff and cell_value < closest_value):
                closest = cell
                closest_obj = obj
        return closest_obj

    @abstractmethod
    def _get_gui_scene(self) -> GUIScene | None:
        raise NotImplementedError


class AbstractGUIGrid(_Grid):
    @abstractmethod
    def _get_gui_scene(self) -> GUIScene | None:
        raise NotImplementedError


class AbstractGUIScrollableGrid(AbstractGUIGrid, AbstractScrollableView):
    if TYPE_CHECKING:

        def __init__(
            self,
            *,
            uniform_cell_size: bool = ...,
            bg_color: Color = ...,
            outline: int = ...,
            outline_color: Color = ...,
            padx: int = ...,
            pady: int = ...,
            justify: GridJustify = ...,
            xscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = ...,
            yscrollcommand: Callable[[float, float], None] | WeakMethod[Callable[[float, float], None]] | None = ...,
            wheel_xscroll_increment: int = ...,
            wheel_yscroll_increment: int = ...,
            **kwargs: Any,
        ) -> None:
            ...

    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    def get_view_rect(self) -> Rect:
        return self.get_rect()

    def get_whole_rect(self) -> Rect:
        nb_rows = self.nb_rows
        nb_columns = self.nb_columns
        all_rects = list(starmap(self.get_cell_rect, ((row, column) for row in range(nb_rows) for column in range(nb_columns))))
        if not all_rects:
            return Rect(self.topleft, (0, 0))
        return reduce(Rect.union, all_rects)

    def _move_view(self, dx: int, dy: int) -> None:
        x, y = self._relative_cell_start
        self._relative_cell_start = x + dx, y + dy
        self._on_move()
