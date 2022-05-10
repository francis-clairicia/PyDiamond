# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Grid module"""

from __future__ import annotations

__all__ = ["Grid"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import suppress
from dataclasses import dataclass
from enum import auto, unique
from operator import itemgetter
from typing import Any, Container, Iterator, Literal, Sequence, TypeGuard, TypeVar, overload
from weakref import ref as weakref

from ..system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ..system.enum import AutoLowerNameEnum
from ..system.utils import flatten, valid_integer, weakref_unwrap
from ..window.gui import GUIScene, SupportsFocus
from .color import BLACK, TRANSPARENT, Color
from .drawable import Drawable, MDrawable
from .movable import Movable
from .renderer import AbstractRenderer
from .shape import RectangleShape
from .theme import NoTheme

_D = TypeVar("_D", bound=Drawable)
_T = TypeVar("_T")
_MISSING: Any = object()


class Grid(MDrawable, Container[Drawable]):
    @unique
    class Justify(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        TOP = auto()
        BOTTOM = auto()
        CENTER = auto()

    @dataclass(init=False, slots=True)
    class Padding:
        x: int = 0
        y: int = 0

    config: ConfigurationTemplate = ConfigurationTemplate("bg_color", "outline", "outline_color", "justify")

    bg_color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    justify: OptionAttribute[Justify] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: GUIScene | None = None,
        *,
        bg_color: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        justify: Justify = Justify.CENTER,
    ) -> None:
        if master is not None and not isinstance(master, GUIScene):
            raise TypeError("Only GUIScene are accepted")
        super().__init__()
        self.__rows: dict[int, _GridRow] = dict()
        self.__columns: dict[int, _GridColumnPlaceholder] = dict()
        self.__master: GUIScene | None = master
        self.__max_width_columns: dict[int, float] = dict()
        self.__max_height_rows: dict[int, float] = dict()
        self.__bg: RectangleShape = RectangleShape(0, 0, bg_color, theme=NoTheme)
        self.__outline: RectangleShape = RectangleShape(0, 0, TRANSPARENT, outline=outline, outline_color=outline_color)
        self.__padding: Grid.Padding = Grid.Padding()
        self.justify = justify

    def __contains__(self, __x: object, /) -> bool:
        if not isinstance(__x, Drawable):
            return False
        for cell in flatten(row.iter_cells() for row in self.__rows.values()):
            if cell.get_object() is __x:
                return True
        return False

    def get_size(self) -> tuple[float, float]:
        max_width_columns: dict[int, float] = self.__max_width_columns
        max_height_rows: dict[int, float] = self.__max_height_rows
        return (sum(max_width_columns.values()), sum(max_height_rows.values()))

    def get_cell_size(self, row: int, column: int) -> tuple[float, float]:
        max_width_columns: dict[int, float] = self.__max_width_columns
        max_height_rows: dict[int, float] = self.__max_height_rows
        return (max_width_columns.get(column, 0), max_height_rows.get(row, 0))

    def draw_onto(self, target: AbstractRenderer) -> None:
        bg: RectangleShape = self.__bg
        outline: RectangleShape = self.__outline
        outline.local_size = bg.local_size = self.get_size()
        outline.center = bg.center = self.center
        bg.draw_onto(target)
        for cell in flatten(row.iter_cells() for row in self.__rows.values()):
            cell.draw_onto(target)
        outline.draw_onto(target)

    def rows(self, column: int | None = None) -> Iterator[int]:
        all_rows: dict[int, _GridRow] = self.__rows
        if column is None:
            return iter(all_rows.keys())
        if column not in self.__columns:
            raise IndexError("'column' is undefined")
        return map(
            lambda c: c.row,
            filter(lambda c: c.column == column, flatten(row.iter_cells() for row in all_rows.values())),
        )

    def columns(self, row: int | None = None) -> Iterator[int]:
        if row is None:
            all_columns: dict[int, _GridColumnPlaceholder] = self.__columns
            return iter(all_columns.keys())
        all_rows: dict[int, _GridRow] = self.__rows
        try:
            grid_row: _GridRow = all_rows[row]
        except KeyError as exc:
            raise IndexError("'row' is undefined") from exc
        return map(lambda c: c.column, grid_row.iter_cells())

    def cells(self) -> Iterator[tuple[int, int]]:
        return ((row, column) for row in self.rows() for column in self.columns(row))

    def place(
        self,
        obj: _D,
        row: int,
        column: int,
        *,
        padx: int | None = None,
        pady: int | None = None,
        justify: str | None = None,
    ) -> _D:
        try:
            cell: _GridCell | None = self.__find_cell(obj)
        except ValueError:
            cell = None
        if cell is not None:
            if cell.row == row and cell.column == column:
                return obj
            cell.set_object(None)
        elif self.master is not None and isinstance(obj, SupportsFocus) and not obj.focus.is_bound_to(self.master):  # type: ignore[unreachable]
            raise ValueError(f"'obj' do not have the same GUIScene master that self")

        grid_row: _GridRow
        try:
            grid_row = self.__rows[row]
        except KeyError:
            self.__rows[row] = grid_row = _GridRow(self, row, self.__columns)
            self.__rows = dict(sorted(self.__rows.items(), key=itemgetter(0)))
        grid_row.place(obj, column, padx=padx, pady=pady, justify=justify)
        self.__set_obj_on_side_internal()
        self._update()
        return obj

    @overload
    def get(self, row: int, column: int) -> Drawable | None:
        ...

    @overload
    def get(self, row: int, column: int, default: _T) -> Drawable | _T:
        ...

    def get(self, row: int, column: int, default: Any = None) -> Any:
        try:
            grid_row: _GridRow = self.__rows[row]
        except KeyError:
            pass
        else:
            for cell in grid_row.iter_cells():
                if cell.row == row and cell.column == column:
                    drawable: Drawable | None = cell.get_object()
                    if drawable is None:
                        break
                    return drawable
        return default

    @overload
    def pop(self, row: int, column: int) -> Drawable:
        ...

    @overload
    def pop(self, row: int, column: int, default: _T) -> Drawable | _T:
        ...

    def pop(self, row: int, column: int, default: Any = _MISSING) -> Any:
        try:
            grid_row: _GridRow = self.__rows[row]
        except KeyError:
            pass
        else:
            for cell in grid_row.iter_cells():
                if cell.row == row and cell.column == column:
                    drawable: Drawable | None = cell.get_object()
                    if drawable is None:
                        break
                    cell.set_object(None)
                    self.__set_obj_on_side_internal()
                    self._update()
                    return drawable
        if default is not _MISSING:
            return default
        raise IndexError(f"{(row, column)} does not exists")

    def remove(self, obj: Drawable) -> None:
        cell: _GridCell = self.__find_cell(obj)
        cell.set_object(None)
        self.__set_obj_on_side_internal()
        self._update()

    def get_position(self, obj: Drawable) -> tuple[int, int] | None:
        for cell in flatten(row.iter_cells() for row in self.__rows.values()):
            if cell.get_object() is obj:
                return (cell.row, cell.column)
        return None

    def clear(self) -> None:
        for cell in flatten(row.iter_cells() for row in self.__rows.values()):
            cell.set_object(None)
        self.__set_obj_on_side_internal()
        self._update()

    def modify(
        self,
        row: int,
        column: int,
        *,
        padx: int | None = None,
        pady: int | None = None,
        justify: str | None = None,
    ) -> None:
        try:
            grid_row: _GridRow = self.__rows[row]
        except KeyError:
            pass
        else:
            for cell in grid_row.iter_cells():
                if cell.row == row and cell.column == column:
                    cell.update_params(padx=padx, pady=pady, justify=justify)
                    self._update()
                    return
        raise IndexError(f"{(row, column)} does not exists")

    def unify(self) -> None:
        all_grid_rows: dict[int, _GridRow] = self.__rows
        all_grid_columns: dict[int, _GridColumnPlaceholder] = self.__columns
        self.__remove_useless_cells()
        new_grid_rows: Sequence[_GridRow] = sorted(all_grid_rows.values(), key=lambda r: r.row)
        new_grid_columns: Sequence[_GridColumnPlaceholder] = sorted(all_grid_columns.values(), key=lambda c: c.column)
        all_grid_rows.clear()
        all_grid_columns.clear()
        for column, grid_column in enumerate(new_grid_columns):
            grid_column.move_to_column(column)
            all_grid_columns[column] = grid_column
        for row, grid_row in enumerate(new_grid_rows):
            grid_row.move_to_row(row)
            all_grid_rows[row] = grid_row
            grid_row.reset()
        self._update()

    def _update(self) -> None:
        max_width_columns: dict[int, float] = self.__max_width_columns
        max_height_rows: dict[int, float] = self.__max_height_rows
        all_rows: dict[int, _GridRow] = self.__rows

        topleft: tuple[float, float] = self.topleft
        max_width_columns.clear()
        max_height_rows.clear()
        for cell in flatten(row.iter_cells() for row in all_rows.values()):
            cell_w, cell_h = cell.get_local_size(from_grid=True)
            max_width_columns[cell.column] = max(max_width_columns.get(cell.column, 0), cell_w)
            max_height_rows[cell.row] = max(max_height_rows.get(cell.row, 0), cell_h)
        self.topleft = topleft

    def _on_move(self) -> None:
        super()._on_move()
        default_left, top = self.topleft
        all_rows: dict[int, _GridRow] = self.__rows
        nb_rows: int = self.nb_rows
        nb_columns: int = self.nb_columns
        max_width_columns: dict[int, float] = self.__max_width_columns
        max_height_rows: dict[int, float] = self.__max_height_rows

        def get_cell(row: int, column: int) -> _GridCell | None:
            try:
                return all_rows[row].get_cell(column)
            except KeyError:
                return None

        for row in range(nb_rows):
            left: float = default_left
            for col in range(nb_columns):
                if (cell := get_cell(row, col)) is not None:
                    cell.topleft = (left, top)
                left += max_width_columns.get(col, 0)
            top += max_height_rows.get(row, 0)

    def __find_cell(self, obj: Drawable) -> _GridCell:
        for cell in flatten(row.iter_cells() for row in self.__rows.values()):
            if cell.get_object() is obj:
                return cell
        raise ValueError(f"'obj' not in grid")

    def __set_obj_on_side_internal(self) -> None:
        all_rows: dict[int, list[_GridCell]] = {}
        all_columns: dict[int, list[_GridCell]] = {}
        self.__remove_useless_cells(all_rows=all_rows, all_columns=all_columns)

        if self.master is None:
            return

        find_closest = self.__find_closest
        all_column_indexes: Sequence[int] = sorted(all_columns)
        for index, column in enumerate(all_column_indexes):
            for cell in all_columns[column]:
                obj: Any | None = cell.get_object()
                if obj is None or not isinstance(obj, SupportsFocus):
                    continue
                left_obj: SupportsFocus | None = None
                right_obj: SupportsFocus | None = None
                if index > 0:
                    left_obj = find_closest(all_columns[all_column_indexes[index - 1]], "row", cell)
                with suppress(IndexError):
                    right_obj = find_closest(all_columns[all_column_indexes[index + 1]], "row", cell)
                if left_obj is not None:
                    obj.focus.set_obj_on_side(on_left=left_obj)
                if right_obj is not None:
                    obj.focus.set_obj_on_side(on_right=right_obj)

        all_row_indexes: Sequence[int] = sorted(all_rows)
        for index, row in enumerate(all_row_indexes):
            for cell in all_rows[row]:
                obj = cell.get_object()
                if obj is None or not isinstance(obj, SupportsFocus):
                    continue
                top_obj: SupportsFocus | None = None
                bottom_obj: SupportsFocus | None = None
                if index > 0:
                    top_obj = find_closest(all_rows[all_row_indexes[index - 1]], "column", cell)
                with suppress(IndexError):
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
            if not isinstance(obj, SupportsFocus):
                continue
            if (cell_value := int(getattr(cell, attr))) == value:
                return obj
            if closest is None:
                closest = cell
                closest_obj = obj
            closest_value: int = int(getattr(closest, attr))
            closest_diff: int = abs(closest_value - value)
            actual_diff: int = abs(cell_value - value)
            if actual_diff < closest_diff or (actual_diff == closest_diff and cell_value < closest_value):
                closest = cell
                closest_obj = obj
        return closest_obj

    def __remove_useless_cells(
        self,
        *,
        all_rows: dict[int, list[_GridCell]] | None = None,
        all_columns: dict[int, list[_GridCell]] | None = None,
    ) -> None:
        if all_rows is None:
            all_rows = {}
        if all_columns is None:
            all_columns = {}
        all_grid_rows: dict[int, _GridRow] = self.__rows
        all_grid_columns: dict[int, _GridColumnPlaceholder] = self.__columns
        for grid_row in tuple(all_grid_rows.values()):
            grid_row.remove_useless_cells()
            cells: Sequence[_GridCell] = tuple(grid_row.iter_cells())
            if not cells:
                all_grid_rows.pop(grid_row.row, None)
                continue
            for cell in cells:
                all_rows.setdefault(cell.row, []).append(cell)
                all_columns.setdefault(cell.column, []).append(cell)
        for column in tuple(all_grid_columns):
            if column not in all_columns:
                all_grid_columns.pop(column, None)

    @config.getter_key("bg_color", use_key="color")
    def __get_bg_option(self, option: str) -> Any:
        return self.__bg.config.get(option)

    @config.setter_key("bg_color", use_key="color")
    def __set_bg_option(self, option: str, value: Any) -> None:
        return self.__bg.config.set(option, value)

    @config.getter_key("outline")
    @config.getter_key("outline_color")
    def __get_outline_option(self, option: str) -> Any:
        return self.__outline.config.get(option)

    @config.setter_key("outline")
    @config.setter_key("outline_color")
    def __set_outline_option(self, option: str, value: Any) -> None:
        return self.__outline.config.set(option, value)

    config.add_enum_converter("justify", Justify)

    @property
    def master(self) -> GUIScene | None:
        return self.__master

    @property
    def padding(self) -> Padding:
        return self.__padding

    @property
    def nb_rows(self) -> int:
        return max(all_rows) + 1 if (all_rows := self.__rows) else 0

    @property
    def nb_columns(self) -> int:
        all_rows: dict[int, _GridRow] = self.__rows
        return max((row.nb_columns for row in all_rows.values()), default=0)


class _GridRow:

    __slots__ = ("__master", "__cells", "__columns", "__row")

    def __init__(self, master: Grid, row: int, column_dict: dict[int, _GridColumnPlaceholder]) -> None:
        self.__master: weakref[Grid] = weakref(master)
        self.__cells: dict[int, _GridCell] = dict()
        self.__columns: dict[int, _GridColumnPlaceholder] = column_dict
        self.move_to_row(row)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} row={self.row}>"

    def iter_cells(self) -> Iterator[_GridCell]:
        return iter(self.__cells.values())

    def get_cell(self, column: int) -> _GridCell | None:
        return self.__cells.get(column, None)

    def get_cell_size(self, column: int) -> tuple[float, float]:
        master: Grid = self.grid
        return master.get_cell_size(self.row, column)

    def place(self, obj: Drawable, column: int, *, padx: int | None, pady: int | None, justify: str | None) -> None:
        cell: _GridCell
        try:
            cell = self.__cells[column]
        except KeyError:
            grid_column: _GridColumnPlaceholder = self.__columns.setdefault(column, _GridColumnPlaceholder(column))
            self.__cells[column] = cell = _GridCell(self, grid_column)
            self.reset()
        cell.set_object(obj, padx=padx, pady=pady, justify=justify)

    def move_to_row(self, row: int) -> None:
        if row < 0:
            raise ValueError(f"'row' value cannot be negative, got {row!r}")
        self.__row: int = row

    def remove_useless_cells(self) -> None:
        self.__cells = {c.column: c for c in sorted(self.__cells.values(), key=lambda c: c.column) if c.get_object() is not None}

    def reset(self) -> None:
        self.__cells = {c.column: c for c in sorted(self.__cells.values(), key=lambda c: c.column)}

    @property
    def grid(self) -> Grid:
        return weakref_unwrap(self.__master)

    @property
    def row(self) -> int:
        return self.__row

    @property
    def nb_columns(self) -> int:
        return max(cells) + 1 if (cells := self.__cells) else 0


class _GridColumnPlaceholder:

    __slots__ = ("__column",)

    def __init__(self, column: int) -> None:
        self.move_to_column(column)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} column={self.column}>"

    def move_to_column(self, column: int) -> None:
        if column < 0:
            raise ValueError(f"'column' value cannot be negative, got {column!r}")
        self.__column: int = column

    @property
    def column(self) -> int:
        return self.__column


class _GridCell(MDrawable):

    __slots__ = (
        "__master",
        "__column",
        "__object",
        "__padx",
        "__pady",
        "__justify",
        "__obj_size",
    )

    def __init__(self, master: _GridRow, column: _GridColumnPlaceholder) -> None:
        super().__init__()
        self.__master: _GridRow = master
        self.__column: _GridColumnPlaceholder = column
        self.__object: MDrawable | None = None
        self.__padx: int = 0
        self.__pady: int = 0
        self.__justify: Grid.Justify = Grid.Justify.CENTER
        self.__obj_size: tuple[float, float] = (0, 0)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} row={self.row}, column={self.column}>"

    def get_size(self) -> tuple[float, float]:
        master: _GridRow = self.__master
        cell_w, cell_h = master.get_cell_size(self.column)
        local_w, local_h = self.get_local_size()
        return max(cell_w, local_w), max(cell_h, local_h)

    def get_local_size(self, *, from_grid: bool = False) -> tuple[float, float]:
        obj: MDrawable | None = self.__object
        if obj is None:
            if from_grid:
                self.__obj_size = (0, 0)
            return (0, 0)
        width: float
        height: float
        width, height = obj.get_size()
        width += self.__padx * 2
        height += self.__pady * 2
        if from_grid:
            self.__obj_size = (width, height)
        return (width, height)

    def draw_onto(self, target: AbstractRenderer) -> None:
        obj: MDrawable | None = self.__object
        if obj is None:
            return
        if obj.get_size() != self.__obj_size:
            self.grid._update()
        return obj.draw_onto(target)

    def get_object(self) -> Drawable | None:
        return self.__object

    @overload
    def set_object(
        self, drawable: Drawable, *, padx: int | None = None, pady: int | None = None, justify: str | None = None
    ) -> None:
        ...

    @overload
    def set_object(self, drawable: None) -> None:
        ...

    def set_object(
        self,
        drawable: Drawable | None,
        *,
        padx: int | None = None,
        pady: int | None = None,
        justify: str | None = None,
    ) -> None:
        obj: Any
        if drawable is None:
            obj = self.__object
            if obj is None:
                return
            self.__object = None
            self.__obj_size = (0, 0)
        else:
            if not _is_movable(drawable):
                raise TypeError("'drawable' must be Movable too")
            obj = drawable
            if self.__object is not obj:
                self.set_object(None)
                self.__object = obj
            if padx is None:
                padx = self.grid.padding.x
            if pady is None:
                pady = self.grid.padding.y
            if justify is None:
                justify = self.grid.justify
            self.update_params(padx=padx, pady=pady, justify=justify)

    def update_params(
        self,
        *,
        padx: int | None = None,
        pady: int | None = None,
        justify: str | None = None,
    ) -> None:
        if padx is not None:
            self.__padx = valid_integer(value=padx, min_value=0)
        if pady is not None:
            self.__pady = valid_integer(value=pady, min_value=0)
        if justify is not None:
            self.__justify = Grid.Justify(justify)
        if (movable := self.__object) is not None:
            self.__obj_size = movable.get_size()
        else:
            self.__obj_size = (0, 0)

    def _on_move(self) -> None:
        super()._on_move()
        obj: MDrawable | None = self.__object
        if obj is None:
            return
        match self.__justify:
            case Grid.Justify.LEFT:
                obj.midleft = (self.left + self.__padx, self.centery)
            case Grid.Justify.RIGHT:
                obj.midright = (self.right - self.__padx, self.centery)
            case Grid.Justify.TOP:
                obj.midtop = (self.centerx, self.top + self.__pady)
            case Grid.Justify.BOTTOM:
                obj.midbottom = (self.centerx, self.bottom - self.__pady)
            case Grid.Justify.CENTER:
                obj.center = self.center
            case _:
                raise ValueError("Unknown Justify value")

    @property
    def grid(self) -> Grid:
        grid_row: _GridRow = self.__master
        return grid_row.grid

    @property
    def row(self) -> int:
        grid_row: _GridRow = self.__master
        return grid_row.row

    @property
    def column(self) -> int:
        grid_col: _GridColumnPlaceholder = self.__column
        return grid_col.column


def _is_movable(obj: Any) -> TypeGuard[Movable]:
    return isinstance(obj, Movable)
