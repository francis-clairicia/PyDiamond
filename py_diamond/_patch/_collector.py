# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch collector module"""

from __future__ import annotations

if not __package__:
    raise ImportError("There is no package name. Perhaps you should import the module instead of run the script file")

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import contextlib
import importlib
import importlib.machinery
import importlib.util
import itertools
import os.path
import pkgutil
import re
import sys
from typing import TYPE_CHECKING, Callable, Final, Iterable, Iterator, TypeAlias

from ..system.singleton import Singleton

if TYPE_CHECKING:
    from types import ModuleType


PLUGIN_NAME_PATTERN = re.compile(r"^plugin__\w+$")


Plugin: TypeAlias = Callable[[], None]


class PatchCollectorType(Singleton):
    def __init__(self) -> None:
        super().__init__()
        with self._dont_write_bytecode_on_import():
            self.__all_patches: tuple[Plugin, ...] = tuple(itertools.chain.from_iterable(self.walk_in_plugins_module(".plugins")))

    def run_patches(self) -> None:
        for patch in self.__all_patches:
            patch()

    def walk_in_plugins_module(self, plugins_module_name: str) -> Iterator[list[Plugin]]:
        plugins_module_name = importlib.util.resolve_name(plugins_module_name, __package__)
        plugins_module = importlib.import_module(plugins_module_name)

        plugins_file: str | None = getattr(plugins_module, "__file__", None)
        if not plugins_file:  # Namespace package
            return

        if os.path.splitext(os.path.basename(plugins_file))[0] != "__init__":  # Module
            yield self._load_plugin_from_module(plugins_module)
            return

        plugins_path: Iterable[str] = getattr(plugins_module, "__path__", None) or [os.path.dirname(plugins_file)]
        for submodule_info in pkgutil.walk_packages(plugins_path):
            submodule_fullname = f"{plugins_module_name}.{submodule_info.name}"
            if submodule_info.ispkg:
                yield from self.walk_in_plugins_module(submodule_fullname)
            else:
                yield self._load_plugin_from_module(importlib.import_module(submodule_fullname))

    def _load_plugin_from_module(self, plugin_module: ModuleType) -> list[Plugin]:
        return [obj for name, obj in vars(plugin_module).items() if PLUGIN_NAME_PATTERN.fullmatch(name) and callable(obj)]

    @staticmethod
    @contextlib.contextmanager
    def _dont_write_bytecode_on_import() -> Iterator[None]:
        with contextlib.ExitStack() as stack:
            if not sys.dont_write_bytecode:
                sys.dont_write_bytecode = True
                stack.callback(object.__setattr__, sys, "dont_write_bytecode", False)
            yield


PatchCollector: Final[PatchCollectorType] = PatchCollectorType.instance
