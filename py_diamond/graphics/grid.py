# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Grid module"""

from __future__ import annotations

__all__ = ["Grid"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import suppress
from dataclasses import dataclass
from enum import auto, unique
from itertools import chain
from typing import (
    Any,
    Callable,
    Container,
    Dict,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

from ..system.configuration import Configuration, OptionAttribute
from ..system.enum import AutoLowerNameEnum
from ..system.utils import valid_integer
from ..window.gui import BoundFocus, GUIScene, SupportsFocus
from .color import BLACK, TRANSPARENT, Color
from .drawable import Drawable, MDrawable
from .movable import Movable
from .renderer import Renderer
from .shape import RectangleShape
from .theme import NoTheme

_D = TypeVar("_D", bound=Drawable)


class Grid(MDrawable, Container[Drawable]):
    @unique
    class Justify(AutoLowerNameEnum):
        LEFT = auto()
        RIGHT = auto()
        TOP = auto()
        BOTTOM = auto()
        CENTER = auto()

    @dataclass
    class Padding:
        x: int = 0
        y: int = 0

    config: Configuration = Configuration("bg_color", "outline", "outline_color", "justify")

    bg_color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    justify: OptionAttribute[Justify] = OptionAttribute()

    def __init__(
        self,
        /,
        master: Optional[GUIScene] = None,
        *,
        bg_color: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        justify: Justify = Justify.CENTER,
    ) -> None:
        super().__init__()
        self.__rows: Dict[int, _GridRow] = dict()
        self.__master: Optional[GUIScene] = master
        self.__max_width_columns: Dict[int, float] = dict()
        self.__max_height_rows: Dict[int, float] = dict()
        self.__bg: RectangleShape = RectangleShape(0, 0, bg_color, theme=NoTheme)
        self.__outline: RectangleShape = RectangleShape(0, 0, TRANSPARENT, outline=outline, outline_color=outline_color)
        self.__padding: Grid.Padding = Grid.Padding()
        self.justify = justify

    def __contains__(self, __x: object, /) -> bool:
        if not isinstance(__x, Drawable):
            return False
        for cell in chain.from_iterable(row.iter_cells() for row in self.__rows.values()):
            if cell.get_object() is __x:
                return True
        return False

    def get_size(self, /) -> Tuple[float, float]:
        max_width_columns: Dict[int, float] = self.__max_width_columns
        max_height_rows: Dict[int, float] = self.__max_height_rows
        return (sum(max_width_columns.values()), sum(max_height_rows.values()))

    def get_cell_size(self, row: int, column: int) -> Tuple[float, float]:
        max_width_columns: Dict[int, float] = self.__max_width_columns
        max_height_rows: Dict[int, float] = self.__max_height_rows
        return (max_width_columns.get(column, 0), max_height_rows.get(row, 0))

    def draw_onto(self, /, target: Renderer) -> None:
        bg: RectangleShape = self.__bg
        outline: RectangleShape = self.__outline
        outline.local_size = bg.local_size = self.get_size()
        outline.center = bg.center = self.center
        bg.draw_onto(target)
        for cell in chain.from_iterable(row.iter_cells() for row in self.__rows.values()):
            cell.draw_onto(target)
        outline.draw_onto(target)

    def place(
        self,
        /,
        obj: _D,
        row: int,
        column: int,
        *,
        padx: Optional[int] = None,
        pady: Optional[int] = None,
        justify: Optional[str] = None,
    ) -> _D:
        try:
            cell: _GridCell = self.__find_cell(obj)
        except ValueError:
            pass
        else:
            if cell.row == row and cell.column == 0:
                return obj
            cell.set_object(None)

        grid_row: _GridRow
        try:
            grid_row = self.__rows[row]
        except KeyError:
            self.__rows[row] = grid_row = _GridRow(self, row)
            self.__rows = dict(sorted(self.__rows.items(), key=lambda e: e[0]))
        grid_row.place(obj, column, padx=padx, pady=pady, justify=justify)
        self._update()
        self.__set_obj_on_side_internal()
        return obj

    def pop(self, /, row: int, column: int) -> Drawable:
        for cell in chain.from_iterable(row.iter_cells() for row in self.__rows.values()):
            if cell.row == row and cell.column == column:
                drawable: Optional[Drawable] = cell.get_object()
                cell.set_object(None)
                self._update()
                self.__set_obj_on_side_internal()
                if drawable is None:
                    break
                return drawable
        raise IndexError(f"{(row, column)} does not exists")

    def remove(self, /, obj: Drawable) -> None:
        cell: _GridCell = self.__find_cell(obj)
        cell.set_object(None)
        self._update()
        self.__set_obj_on_side_internal()

    def _update(self, /) -> None:
        max_width_columns: Dict[int, float] = self.__max_width_columns
        max_height_rows: Dict[int, float] = self.__max_height_rows
        all_rows: Dict[int, _GridRow] = self.__rows

        topleft: Tuple[float, float] = self.topleft
        max_width_columns.clear()
        max_height_rows.clear()
        for cell in chain.from_iterable(row.iter_cells() for row in all_rows.values()):
            cell_w, cell_h = cell.get_local_size()
            max_width_columns[cell.column] = max(max_width_columns.get(cell.column, 0), cell_w)
            max_height_rows[cell.row] = max(max_height_rows.get(cell.row, 0), cell_h)
        self.topleft = topleft

    def _on_move(self, /) -> None:
        super()._on_move()
        default_left, top = self.topleft
        all_rows: Dict[int, _GridRow] = self.__rows
        nb_rows: int = self.nb_rows
        nb_columns: int = self.nb_columns
        max_width_columns: Dict[int, float] = self.__max_width_columns
        max_height_rows: Dict[int, float] = self.__max_height_rows

        def get_cell(row: int, column: int) -> Optional[_GridCell]:
            try:
                return all_rows[row].get_cell(column)
            except KeyError:
                return None

        for row in range(nb_rows):
            left: float = default_left
            for col in range(nb_columns):
                cell: Optional[_GridCell] = get_cell(row, col)
                if cell is not None:
                    cell.topleft = (left, top)
                left += max_width_columns.get(col, 0)
            top += max_height_rows.get(row, 0)

    def __find_cell(self, /, obj: Drawable) -> _GridCell:
        for cell in chain.from_iterable(row.iter_cells() for row in self.__rows.values()):
            if cell.get_object() is obj:
                return cell
        raise ValueError(f"'obj' not in grid")

    def __set_obj_on_side_internal(self, /) -> None:
        if self.master is None:
            return

        all_grid_rows: Dict[int, _GridRow] = self.__rows
        all_rows: Dict[int, List[_GridCell]] = {}
        all_columns: Dict[int, List[_GridCell]] = {}
        for grid_row in tuple(all_grid_rows.values()):
            grid_row.remove_useless_cells()
            cells: Sequence[_GridCell] = tuple(grid_row.iter_cells())
            if not cells:
                all_grid_rows.pop(grid_row.row, None)
                continue
            for cell in cells:
                all_rows.setdefault(cell.row, []).append(cell)
                all_columns.setdefault(cell.column, []).append(cell)

        def find_closest(cells: Sequence[_GridCell], attr: Literal["row", "column"], cell_to_link: _GridCell) -> _GridCell:
            closest: _GridCell = cells[0]
            value: int = getattr(cell_to_link, attr)
            for cell in cells[1:]:
                cell_value: int = int(getattr(cell, attr))
                if cell_value == value:
                    return cell
                closest_value: int = int(getattr(cell, attr))
                closest_diff: int = abs(closest_value - value)
                actual_diff: int = abs(cell_value - value)
                if actual_diff < closest_diff or (actual_diff == closest_diff and cell_value < closest_value):
                    closest = cell
            return closest

        all_column_indexes: Sequence[int] = sorted(all_columns)
        for index, column in enumerate(all_column_indexes):
            for cell in all_columns[column]:
                left_cell: Optional[_GridCell] = None
                right_cell: Optional[_GridCell] = None
                if index > 0:
                    left_cell = find_closest(all_columns[all_column_indexes[index - 1]], "row", cell)
                with suppress(IndexError):
                    right_cell = find_closest(all_columns[all_column_indexes[index + 1]], "row", cell)
                if left_cell is not None:
                    cell.focus.set_obj_on_side(on_left=left_cell)
                if right_cell is not None:
                    cell.focus.set_obj_on_side(on_right=right_cell)

        all_row_indexes: Sequence[int] = sorted(all_rows)
        for index, row in enumerate(all_row_indexes):
            for cell in all_rows[row]:
                top_cell: Optional[_GridCell] = None
                bottom_cell: Optional[_GridCell] = None
                if index > 0:
                    top_cell = find_closest(all_rows[all_row_indexes[index - 1]], "column", cell)
                with suppress(IndexError):
                    bottom_cell = find_closest(all_rows[all_row_indexes[index + 1]], "column", cell)
                if top_cell is not None:
                    cell.focus.set_obj_on_side(on_top=top_cell)
                if bottom_cell is not None:
                    cell.focus.set_obj_on_side(on_bottom=bottom_cell)

    @config.getter_key("bg_color", use_key="color")
    def __get_bg_option(self, /, option: str) -> Any:
        return self.__bg.config.get(option)

    @config.setter_key("bg_color", use_key="color")
    def __set_bg_option(self, /, option: str, value: Any) -> None:
        return self.__bg.config.set(option, value)

    @config.getter_key("outline")
    @config.getter_key("outline_color")
    def __get_outline_option(self, /, option: str) -> Any:
        return self.__outline.config.get(option)

    @config.setter_key("outline")
    @config.setter_key("outline_color")
    def __set_outline_option(self, /, option: str, value: Any) -> None:
        return self.__outline.config.set(option, value)

    config.enum("justify", Justify)

    @property
    def master(self, /) -> Optional[GUIScene]:
        return self.__master

    @property
    def padding(self, /) -> Padding:
        return self.__padding

    @property
    def nb_rows(self, /) -> int:
        all_rows: Dict[int, _GridRow] = self.__rows
        if not all_rows:
            return 0
        return max(all_rows) + 1

    @property
    def nb_columns(self, /) -> int:
        all_rows: Dict[int, _GridRow] = self.__rows
        return max((row.nb_columns for row in all_rows.values()), default=0)


class _GridRow:
    def __init__(self, /, master: Grid, row: int) -> None:
        if row < 0:
            raise ValueError(f"'row' value cannot be negative, got {row!r}")
        self.__master: Grid = master
        self.__row: int = row
        self.__cells: Dict[int, _GridCell] = dict()

    def __repr__(self, /) -> str:
        return f"<{self.__class__.__name__} row={self.row}>"

    def iter_cells(self, /) -> Iterator[_GridCell]:
        yield from self.__cells.values()

    def get_cell(self, /, column: int) -> Optional[_GridCell]:
        return self.__cells.get(column, None)

    def get_cell_size(self, /, column: int) -> Tuple[float, float]:
        master: Grid = self.grid
        return master.get_cell_size(self.row, column)

    def place(self, /, obj: Drawable, column: int, *, padx: Optional[int], pady: Optional[int], justify: Optional[str]) -> None:
        cell: _GridCell
        try:
            cell = self.__cells[column]
        except KeyError:
            self.__cells[column] = cell = _GridCell(self, column)
            self.__cells = dict(sorted(self.__cells.items(), key=lambda e: e[0]))
        cell.set_object(obj, padx=padx, pady=pady, justify=justify)

    def remove_useless_cells(self, /) -> None:
        master: Optional[GUIScene] = self.master
        if master is not None:
            for cell in filter(lambda c: c.get_object() is None, self.__cells.values()):
                if cell in master.focus_container:
                    master.focus_container.remove(cell)
        self.__cells = {k: v for k, v in self.__cells.items() if v.get_object() is not None}

    @property
    def master(self, /) -> Optional[GUIScene]:
        grid: Grid = self.grid
        return grid.master

    @property
    def grid(self, /) -> Grid:
        return self.__master

    @property
    def row(self, /) -> int:
        return self.__row

    @property
    def nb_columns(self, /) -> int:
        cells: Dict[int, _GridCell] = self.__cells
        if not cells:
            return 0
        return max(cells) + 1


class _GridCell(MDrawable):
    def __init__(self, /, master: _GridRow, column: int) -> None:
        if column < 0:
            raise ValueError(f"'column' value cannot be negative, got {column!r}")
        super().__init__()
        self.__master: _GridRow = master
        self.__column: int = column
        self.__object: Optional[MDrawable] = None
        self.__padx: int = 0
        self.__pady: int = 0
        self.__justify: Grid.Justify = Grid.Justify.CENTER
        self.__obj_size: Tuple[float, float] = (0, 0)
        if self.master is not None:
            self.master.focus_container.add(self)
            BoundFocus(self, self.master).take(False)

    def __repr__(self, /) -> str:
        return f"<{self.__class__.__name__} row={self.row}, column={self.column}>"

    def get_size(self, /) -> Tuple[float, float]:
        master: _GridRow = self.__master
        cell_w, cell_h = master.get_cell_size(self.column)
        local_w, local_h = self.get_local_size()
        return max(cell_w, local_w), max(cell_h, local_h)

    def get_local_size(self, /) -> Tuple[float, float]:
        obj: Optional[MDrawable] = self.__object
        if obj is None:
            return (0, 0)
        width: float
        height: float
        width, height = obj.get_size()
        self.__obj_size = (width, height)
        width += self.__padx * 2
        height += self.__pady * 2
        return (width, height)

    def draw_onto(self, /, target: Renderer) -> None:
        obj: Optional[MDrawable] = self.__object
        if obj is None:
            return
        if obj.get_size() != self.__obj_size:
            self.grid._update()
        return obj.draw_onto(target)

    def get_object(self, /) -> Optional[Drawable]:
        return self.__object

    @overload
    def set_object(
        self, /, drawable: Drawable, *, padx: Optional[int] = None, pady: Optional[int] = None, justify: Optional[str] = None
    ) -> None:
        ...

    @overload
    def set_object(self, /, drawable: None) -> None:
        ...

    def set_object(
        self,
        /,
        drawable: Optional[Drawable],
        *,
        padx: Optional[int] = None,
        pady: Optional[int] = None,
        justify: Optional[str] = None,
    ) -> None:
        master: Optional[GUIScene] = self.master
        obj: Any
        if drawable is None:
            obj = self.__object
            if obj is None:
                return
            self.__object = None
            self.__obj_size = (0, 0)
            if master is not None and isinstance(obj, SupportsFocus) and obj in master.focus_container:
                master.focus_container.remove(obj)
        else:
            ismovable: Callable[[object], bool] = lambda o: isinstance(o, Movable)
            if not ismovable(drawable):
                raise TypeError("'drawable' must be Movable too")
            obj = movable = cast(MDrawable, drawable)
            if self.__object is not drawable:
                self.set_object(None)
                self.__object = obj
                if master is not None and isinstance(obj, SupportsFocus):
                    master.focus_container.add(obj)
            if padx is None:
                padx = self.grid.padding.x
            if pady is None:
                pady = self.grid.padding.y
            if justify is None:
                justify = self.grid.justify
            self.__padx = valid_integer(value=padx, min_value=0)
            self.__pady = valid_integer(value=pady, min_value=0)
            self.__justify = Grid.Justify(justify)
            self.__obj_size = movable.get_size()

    def _on_move(self, /) -> None:
        super()._on_move()
        obj: Optional[MDrawable] = self.__object
        if obj is None:
            return
        move: Dict[Grid.Justify, Dict[str, Union[float, Tuple[float, float]]]] = {
            Grid.Justify.LEFT: {"left": self.left + self.__padx, "centery": self.centery},
            Grid.Justify.RIGHT: {"right": self.right - self.__padx, "centery": self.centery},
            Grid.Justify.TOP: {"top": self.top + self.__pady, "centerx": self.centerx},
            Grid.Justify.BOTTOM: {"bottom": self.bottom - self.__pady, "centerx": self.centerx},
            Grid.Justify.CENTER: {"center": self.center},
        }
        obj.set_position(**move[self.__justify])

    def _on_focus_set(self, /) -> None:
        master: Optional[GUIScene] = self.master
        if master is None:
            return
        obj: Optional[Any] = self.__object
        if isinstance(obj, SupportsFocus) and obj.focus.is_bound_to(master):
            obj.focus.set()

    def _on_focus_leave(self, /) -> None:
        pass

    @property
    def master(self, /) -> Optional[GUIScene]:
        grid_row: _GridRow = self.__master
        return grid_row.master

    @property
    def grid(self, /) -> Grid:
        grid_row: _GridRow = self.__master
        return grid_row.grid

    @property
    def row(self, /) -> int:
        grid_row: _GridRow = self.__master
        return grid_row.row

    @property
    def column(self, /) -> int:
        return self.__column

    @property
    def focus(self, /) -> BoundFocus:
        master: Optional[GUIScene] = self.master
        if master is None:
            return BoundFocus(self, None)
        focus: Optional[BoundFocus] = getattr(self.__object, "focus", None)
        if not isinstance(focus, BoundFocus) or not focus.is_bound_to(master):
            return BoundFocus(self, master)
        return focus
