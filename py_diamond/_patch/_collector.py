# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch collector module"""

from __future__ import annotations

__all__ = ["PatchCollector"]  # type: list[str]

import contextlib
import importlib
import importlib.machinery
import importlib.util
import inspect
import os.path
import pkgutil
from collections import defaultdict, deque
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Iterable, Iterator, Mapping, Sequence, no_type_check

from ._base import BasePatch, PatchContext

if TYPE_CHECKING:
    from types import ModuleType

    from _typeshed import Self


if not __package__:
    raise ImportError("There is no package name. Perhaps you should import the module instead of run the script file")


class _PatchCollectorType:
    __initialized: bool = False
    __forbidden_imports_by_context: Mapping[PatchContext, set[str]] = {
        PatchContext.BEFORE_ALL: {"pygame"},
        PatchContext.BEFORE_IMPORTING_PYGAME: {"pygame"},
    }

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
        self.__all_patches: Mapping[PatchContext, Sequence[BasePatch]]

        all_patches: defaultdict[PatchContext, deque[BasePatch]] = defaultdict(deque)
        forbidden_imports: set[str] = set().union(*self.__forbidden_imports_by_context.values())
        with self._mock_import("import", forbidden_imports=forbidden_imports):
            for patch_cls in set(self.walk_in_plugins_module(".plugins")):
                patch = patch_cls()
                all_patches[patch.get_required_context()].append(patch)

        self.__all_patches = MappingProxyType({k: tuple(v) for k, v in all_patches.items()})

    def run_patches(self, context: PatchContext) -> None:
        forbidden_imports = self.__forbidden_imports_by_context.get(context, set())
        with self._mock_import(f"run ({context.name.replace('_', ' ').lower()})", forbidden_imports=forbidden_imports):
            # TODO (3.11): Exception groups
            for patch in (p for p in self.__all_patches.get(context, ()) if p.must_be_run()):
                patch.run_context = context
                patch.setup()
                try:
                    patch.run()
                finally:
                    patch.teardown()
                    del patch.run_context

    def walk_in_plugins_module(self, plugins_module_name: str) -> Iterator[type[BasePatch]]:
        plugins_module_name = importlib.util.resolve_name(plugins_module_name, __package__)
        plugins_module = importlib.import_module(plugins_module_name)
        plugins_module_spec = plugins_module.__spec__

        plugins_file: str | None
        if plugins_module_spec and plugins_module_spec.origin:
            plugins_file = os.path.realpath(plugins_module_spec.origin)
        else:
            plugins_file = getattr(plugins_module, "__file__", None)
        if not plugins_file:  # Namespace package
            return

        plugins_path: Iterable[str] | None
        if plugins_module_spec and plugins_module_spec.submodule_search_locations is not None:
            plugins_path = plugins_module_spec.submodule_search_locations
        else:
            plugins_path = getattr(plugins_module, "__path__", None)
        if plugins_path is None:  # Module
            yield from self._load_patches_from_module(plugins_module)
            return

        for submodule_info in pkgutil.walk_packages(plugins_path):
            submodule_fullname = f"{plugins_module_name}.{submodule_info.name}"
            if submodule_info.ispkg:
                yield from self.walk_in_plugins_module(submodule_fullname)
            else:
                yield from self._load_patches_from_module(importlib.import_module(submodule_fullname))

    def _load_patches_from_module(self, plugin_module: ModuleType) -> list[type[BasePatch]]:
        return [
            obj
            for obj in vars(plugin_module).values()
            if isinstance(obj, type) and issubclass(obj, BasePatch) and not inspect.isabstract(obj)
        ]

    @staticmethod
    @contextlib.contextmanager
    def _mock_import(context: str, forbidden_imports: Iterable[str] = ()) -> Iterator[None]:
        import re
        import sys

        unittest_was_imported: bool = any(n == "unittest" or n.startswith("unittest.") for n in tuple(sys.modules))

        forbidden_modules = {
            module: re.compile(r"{}(?:\.\w+)*".format(module))
            for module in set(forbidden_imports)
            if not any(n == module or n.startswith(f"{module}.") for n in tuple(sys.modules))  # If module was not imported
        }

        def is_forbidden_module(resolved_name: str) -> str | None:
            return next((module_name for module_name, pattern in forbidden_modules.items() if pattern.match(resolved_name)), None)

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
                    msg = f"{main_package} sub-modules must not be imported during patch {context}"
                    raise ImportError(msg, name=importer_name, path=importer_path)
                if forbidden_module := is_forbidden_module(resolved_name):
                    msg = f"{forbidden_module!r} must not be imported during patch {context}"
                    raise ImportError(msg, name=importer_name, path=importer_path)
            return original_import(name, globals, locals, fromlist, level)

        try:
            with patch("builtins.__import__", import_mock), patch("importlib.__import__", import_mock):
                yield
        finally:
            del patch
            if not unittest_was_imported:  # Useless for game runtime, unload it
                for module_name in filter(lambda n: n == "unittest" or n.startswith("unittest."), tuple(sys.modules)):
                    sys.modules.pop(module_name, None)


PatchCollector: Final[_PatchCollectorType] = _PatchCollectorType()
