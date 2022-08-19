# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Form module"""

from __future__ import annotations

__all__ = ["Form"]


from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Mapping, Sequence, TypeAlias, TypeVar, overload
from weakref import WeakValueDictionary

from ...graphics.color import BLACK, TRANSPARENT, Color
from ...graphics.drawable import Drawable
from ...graphics.movable import Movable
from ...graphics.renderer import AbstractRenderer
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.theme import ThemedObjectMeta, ThemeType
from ...system.validation import valid_integer
from .entry import Entry
from .grid import Grid, GridElement

if TYPE_CHECKING:
    from ..scene import GUIScene


_Label = TypeVar("_Label", bound=GridElement)


class Form(Drawable, Movable, metaclass=ThemedObjectMeta):
    __theme_ignore__: ClassVar[Sequence[str]] = ("on_submit",)

    Justify: TypeAlias = Grid.Justify
    Padding: TypeAlias = Grid.Padding

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "bg_color",
        "outline",
        "outline_color",
        "label_justify",
        "entry_justify",
        "padx",
        "pady",
    )

    bg_color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    label_justify: OptionAttribute[Justify] = OptionAttribute()
    entry_justify: OptionAttribute[Justify] = OptionAttribute()
    padx: OptionAttribute[int] = OptionAttribute()
    pady: OptionAttribute[int] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: GUIScene | None = None,
        *,
        on_submit: Callable[[Mapping[str, str]], None],
        bg_color: Color = TRANSPARENT,
        outline: int = 0,
        outline_color: Color = BLACK,
        label_justify: Justify = Justify.RIGHT,
        entry_justify: Justify = Justify.LEFT,
        padx: int = 10,
        pady: int = 10,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.__on_submit: Callable[[Mapping[str, str]], None] = on_submit
        self.__grid: Grid = Grid(master=master, bg_color=bg_color, outline=outline, outline_color=outline_color)
        self.label_justify = label_justify
        self.entry_justify = entry_justify
        self.padx = padx
        self.pady = pady
        self.__entry_dict: WeakValueDictionary[str, Entry] = WeakValueDictionary()

    def get_size(self) -> tuple[float, float]:
        return self.__grid.get_size()

    def draw_onto(self, target: AbstractRenderer) -> None:
        self.__grid.draw_onto(target)

    def add_entry(
        self,
        name: str,
        entry: Entry,
        label: _Label | None = None,
    ) -> Entry:
        if (
            not isinstance(name, str)
            or not isinstance(entry, Entry)
            or (label is not None and not isinstance(label, GridElement))
        ):
            raise TypeError("Invalid arguments")
        if not name:
            raise ValueError("Empty name")
        entry_dict: WeakValueDictionary[str, Entry] = self.__entry_dict
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
        entry: Entry = self.__entry_dict.pop(name)
        grid: Grid = self.__grid
        entry_pos: tuple[int, int] | None = grid.get_position(entry)
        if entry_pos is not None:
            label_pos = (entry_pos[0], 0)
            grid.pop(*label_pos, None)
            grid.pop(*entry_pos)
            grid.unify()

    @overload
    def get(self) -> MappingProxyType[str, str]:
        ...

    @overload
    def get(self, name: str) -> str:
        ...

    def get(self, name: str | None = None) -> str | MappingProxyType[str, str]:
        entry_dict: WeakValueDictionary[str, Entry] = self.__entry_dict
        if name is not None:
            return entry_dict[name].get()
        return MappingProxyType({n: e.get() for n, e in entry_dict.items()})

    def submit(self) -> None:
        on_submit: Callable[[Mapping[str, str]], None] = self.__on_submit
        return on_submit(self.get())

    def set_visibility(self, status: bool) -> None:
        super().set_visibility(status)
        self.__grid.set_visibility(self.is_shown())

    def _on_move(self) -> None:
        self.__grid.topleft = self.topleft
        return super()._on_move()

    @config.getter_with_key("bg_color")
    @config.getter_with_key("outline")
    @config.getter_with_key("outline_color")
    def __get_grid_option(self, option: str) -> Any:
        return self.__grid.config.get(option)

    @config.setter_with_key("bg_color")
    @config.setter_with_key("outline")
    @config.setter_with_key("outline_color")
    def __set_grid_option(self, option: str, value: Any) -> None:
        return self.__grid.config.set(option, value)

    config.add_enum_converter("label_justify", Justify)
    config.add_enum_converter("entry_justify", Justify)

    @config.on_update_value_with_key("label_justify")
    @config.on_update_value_with_key("entry_justify")
    def __update_grid_justify(self, option: str, justify: Justify) -> None:
        grid: Grid = self.__grid
        column: int = {"label_justify": 0, "entry_justify": 1}[option]
        for row in range(grid.nb_rows):
            grid.modify(row=row, column=column, justify=justify)

    config.add_value_converter_on_set_static("padx", valid_integer(min_value=0))
    config.add_value_converter_on_set_static("pady", valid_integer(min_value=0))

    @config.on_update_value_with_key("padx")
    @config.on_update_value_with_key("pady")
    def __upgrade_grid_padding(self, option: str, value: int) -> None:
        grid: Grid = self.__grid
        padding: dict[str, Any] = {option: value}
        for row in range(grid.nb_rows):
            for column in range(grid.nb_columns):
                grid.modify(row=row, column=column, **padding)

    @property
    def master(self) -> GUIScene | None:
        return self.__grid.master
