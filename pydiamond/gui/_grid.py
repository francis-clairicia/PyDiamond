# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI Grid module"""

from __future__ import annotations

__all__ = ["AbstractGUIGrid", "GridElement", "GridJustify"]

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar, Literal, Sequence, TypeVar

from ..graphics.grid import Grid as _Grid, GridElement, GridJustify
from ..system.collections import SortedDict
from ..system.configuration import ConfigurationTemplate
from .focus import supports_focus
from .scene import GUIScene

if TYPE_CHECKING:
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
    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(parent=_Grid.config)
