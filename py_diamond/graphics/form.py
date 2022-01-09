# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Form module"""

from __future__ import annotations

__all__ = ["Form"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING, Any, Callable, Dict, Mapping, Optional, Tuple, Type, Union, overload

from ..system.configuration import Configuration, OptionAttribute, initializer
from ..system.utils import valid_integer
from .color import BLACK, TRANSPARENT, Color
from .drawable import Drawable, MDrawable
from .entry import Entry
from .grid import Grid
from .renderer import Renderer

if TYPE_CHECKING:
    from ..window.gui import GUIScene


class Form(MDrawable):
    Justify: Type[Grid.Justify] = Grid.Justify
    Padding: Type[Grid.Padding] = Grid.Padding

    config: Configuration = Configuration(
        "bg_color", "outline", "outline_color", "label_justify", "entry_justify", "padx", "pady"
    )

    bg_color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    label_justify: OptionAttribute[Grid.Justify] = OptionAttribute()
    entry_justify: OptionAttribute[Grid.Justify] = OptionAttribute()
    padx: OptionAttribute[int] = OptionAttribute()
    pady: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: Optional[GUIScene] = None,
        *,
        on_submit: Callable[[Mapping[str, str]], None],
        bg_color: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        label_justify: Grid.Justify = Justify.RIGHT,
        entry_justify: Grid.Justify = Justify.LEFT,
        padx: int = 10,
        pady: int = 10,
    ) -> None:
        super().__init__()
        self.__on_submit: Callable[[Mapping[str, str]], None] = on_submit
        self.__grid: Grid = Grid(master=master, bg_color=bg_color, outline=outline, outline_color=outline_color)
        self.label_justify = label_justify
        self.entry_justify = entry_justify
        self.padx = padx
        self.pady = pady
        self.__entry_dict: Dict[str, Entry] = {}

    def get_size(self) -> Tuple[float, float]:
        return self.__grid.get_size()

    def draw_onto(self, target: Renderer) -> None:
        grid: Grid = self.__grid
        grid.topleft = self.topleft
        grid.draw_onto(target)

    def add_entry(
        self,
        name: str,
        entry: Entry,
        label: Optional[Drawable] = None,
    ) -> Entry:
        if not isinstance(name, str) or not isinstance(entry, Entry) or (label is not None and not isinstance(label, Drawable)):
            raise TypeError("Invalid arguments")
        if not name:
            raise ValueError("Empty name")
        entry_dict: Dict[str, Entry] = self.__entry_dict
        if name in entry_dict:
            raise ValueError(f"{name!r} already set")
        grid: Grid = self.__grid
        last_row: int = grid.nb_rows
        padx: int = self.padx
        pady: int = self.pady
        if label is not None:
            grid.place(label, row=last_row, column=0, padx=padx, pady=pady, justify=self.label_justify)
        grid.place(entry, row=last_row, column=1, padx=padx, pady=pady, justify=self.entry_justify)
        entry_dict[name] = entry
        return entry

    def remove_entry(self, name: str) -> None:
        entry_dict: Dict[str, Entry] = self.__entry_dict
        entry: Entry = entry_dict.pop(name)
        grid: Grid = self.__grid
        grid.remove(entry)
        grid.unify()

    @overload
    def get(self) -> Mapping[str, str]:
        ...

    @overload
    def get(self, name: str) -> str:
        ...

    def get(self, name: Optional[str] = None) -> Union[str, Mapping[str, str]]:
        entry_dict: Dict[str, Entry] = self.__entry_dict
        if name is not None:
            return entry_dict[name].get()
        return {n: e.get() for n, e in entry_dict.items()}

    def submit(self) -> None:
        on_submit: Callable[[Mapping[str, str]], None] = self.__on_submit
        return on_submit(self.get())

    def set_visibility(self, status: bool) -> None:
        super().set_visibility(status)
        self.__grid.set_visibility(self.is_shown())

    @config.getter_key("bg_color")
    @config.getter_key("outline")
    @config.getter_key("outline_color")
    def __get_grid_option(self, option: str) -> Any:
        return self.__grid.config.get(option)

    @config.setter_key("bg_color")
    @config.setter_key("outline")
    @config.setter_key("outline_color")
    def __set_grid_option(self, option: str, value: Any) -> None:
        return self.__grid.config.set(option, value)

    config.enum("label_justify", Justify)
    config.enum("entry_justify", Justify)

    @config.on_update_key_value("label_justify")
    @config.on_update_key_value("entry_justify")
    def __update_grid_justify(self, option: str, justify: Grid.Justify) -> None:
        grid: Grid = self.__grid
        column: int = {"label_justify": 0, "entry_justify": 1}[option]
        for row in range(grid.nb_rows):
            grid.modify(row=row, column=column, justify=justify)

    config.value_converter_static("padx", valid_integer(min_value=0))
    config.value_converter_static("pady", valid_integer(min_value=0))

    @config.on_update_key_value("padx")
    @config.on_update_key_value("pady")
    def __upgrade_grid_padding(self, option: str, value: int) -> None:
        grid: Grid = self.__grid
        for row in range(grid.nb_rows):
            for column in range(grid.nb_columns):
                grid.modify(row=row, column=column, **{option: value})  # type: ignore

    @property
    def master(self) -> Optional[GUIScene]:
        return self.__grid.master
