# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch collector module"""

from __future__ import annotations

if not __package__:
    raise ImportError("There is no package name. Perhaps you should import the module instead of run the script file")

__all__ = ["PatchCollector"]  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import contextlib
import importlib
import importlib.machinery
import importlib.util
import inspect
import itertools
import os.path
import pkgutil
from typing import TYPE_CHECKING, Final, Iterable, Iterator, no_type_check

from ._base import BasePatch

if TYPE_CHECKING:
    from types import ModuleType

    from _typeshed import Self


class _PatchCollectorType:
    __initialized: bool = False

    def __new__(cls: type[Self]) -> Self:
        try:
            return getattr(cls, "_PatchCollectorType__instance")  # type: ignore[no-any-return]
        except AttributeError:
            instance = object.__new__(cls)
            setattr(cls, "_PatchCollectorType__instance", instance)
            return instance

    def __init__(self) -> None:
        if self.__initialized:
            return

        self.__initialized = True
        self.__all_patches: Iterable[BasePatch]

        with self._mock_import():
            self.__all_patches = tuple(itertools.chain.from_iterable(self.walk_in_plugins_module(".plugins")))

    def run_patches(self) -> None:
        with self._mock_import():
            for patch in (p for p in self.__all_patches if p.must_be_run()):
                patch.setup()
                try:
                    patch.run()
                finally:
                    patch.teardown()

    def walk_in_plugins_module(self, plugins_module_name: str) -> Iterator[list[BasePatch]]:
        plugins_module_name = importlib.util.resolve_name(plugins_module_name, __package__)
        plugins_module = importlib.import_module(plugins_module_name)

        plugins_file: str | None = getattr(plugins_module, "__file__", None)
        if not plugins_file:  # Namespace package
            return

        if os.path.splitext(os.path.basename(plugins_file))[0] != "__init__":  # Module
            yield self._load_patches_from_module(plugins_module)
            return

        plugins_path: Iterable[str] = getattr(plugins_module, "__path__", None) or [os.path.dirname(plugins_file)]
        for submodule_info in pkgutil.walk_packages(plugins_path):
            submodule_fullname = f"{plugins_module_name}.{submodule_info.name}"
            if submodule_info.ispkg:
                yield from self.walk_in_plugins_module(submodule_fullname)
            else:
                yield self._load_patches_from_module(importlib.import_module(submodule_fullname))

    def _load_patches_from_module(self, plugin_module: ModuleType) -> list[BasePatch]:
        return [
            obj()
            for obj in vars(plugin_module).values()
            if isinstance(obj, type) and issubclass(obj, BasePatch) and not inspect.isabstract(obj)
        ]

    @staticmethod
    @contextlib.contextmanager
    def _mock_import() -> Iterator[None]:
        from unittest.mock import patch

        original_import = __import__
        patch_package = __package__
        main_package = patch_package.rpartition(".")[0]

        @no_type_check
        def import_mock(name, globals=None, locals=None, fromlist=(), level=0):
            if globals is not None:
                importer_name = globals.get("__name__", None)
                importer_path = globals.get("__file__", None)
                resolved_name = name
                if level > 0 and "__package__" in globals:
                    actual_package = str(globals["__package__"])
                    for _ in range(level - 1):
                        actual_package = actual_package.rpartition(".")[0]
                    resolved_name = f"{actual_package}.{name}"
                if main_package in resolved_name and patch_package not in resolved_name:
                    msg = f"{main_package} sub-modules must not be imported during patch import/run"
                    raise ImportError(msg, name=importer_name, path=importer_path)
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", import_mock), patch("importlib.__import__", import_mock):
            yield


PatchCollector: Final[_PatchCollectorType] = _PatchCollectorType()
