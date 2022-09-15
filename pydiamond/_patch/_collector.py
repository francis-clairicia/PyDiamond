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
from typing import TYPE_CHECKING, Any, Final, Iterable, Iterator, Mapping, Sequence, no_type_check

from ._base import BasePatch, PatchContext

if TYPE_CHECKING:
    from types import ModuleType

    from _typeshed import Self


if not __package__:
    raise ImportError("There is no package name. Perhaps you should import the module instead of run the script file")


__main_package__ = __package__.rpartition(".")[0]


class _PatchCollectorType:
    __initialized: bool = False
    __forbidden_imports_until_context: Mapping[str, PatchContext] = {
        "pygame": PatchContext.AFTER_IMPORTING_PYGAME,
        __main_package__: PatchContext.PATCH_SUBMODULES,
    }

    def __new__(cls: type[Self]) -> Self:
        try:
            return getattr(cls, "_PatchCollectorType__instance")
        except AttributeError:
            instance = object.__new__(cls)
            setattr(cls, "_PatchCollectorType__instance", instance)
            return instance

    def __init__(self) -> None:
        if self.__initialized:
            return

        self.__initialized = True
        self.__all_patches: Mapping[PatchContext, Sequence[BasePatch]]
        self.__record: set[str] | None = None

        all_patches: defaultdict[PatchContext, deque[BasePatch]] = defaultdict(deque)
        with self.mock_import("import", forbidden_imports=list(self.__forbidden_imports_until_context)):
            for patch_cls in self.find_patches(".plugins", package=__package__):
                all_patches[patch_cls.get_required_context()].append(patch_cls())

        self.__all_patches = MappingProxyType({k: tuple(v) for k, v in all_patches.items()})

    def has_any_patch_to_run(self, *contexts: PatchContext) -> bool:
        if not contexts:
            contexts = tuple(PatchContext)
        return any(patch.__class__.enabled() for ctx in contexts for patch in self.__all_patches.get(ctx, ()))

    def run_patches(self, context: PatchContext) -> None:
        forbidden_imports = [
            module for module, context_ceiling in self.__forbidden_imports_until_context.items() if context < context_ceiling
        ]
        with self.mock_import(f"run ({context.name.replace('_', ' ').lower()})", forbidden_imports=forbidden_imports):
            # TODO (3.11): Exception groups
            for patch in self.__all_patches.get(context, ()):
                if not patch.__class__.enabled():
                    continue
                patch.setup()
                try:
                    patch.run()
                    if self.__record is not None:
                        self.__record.add(patch.__class__.get_name())
                finally:
                    patch.teardown()

    def start_record(self) -> None:
        if self.__record is None:
            self.__record = set()

    def stop_record(self) -> frozenset[str]:
        record = self.__record
        self.__record = None
        return frozenset(record or ())

    @classmethod
    def find_patches(cls, plugins_module_name: str, *, package: str | None = None) -> Iterator[type[BasePatch]]:
        plugins_module_name = importlib.util.resolve_name(plugins_module_name, package=package)
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
            yield from cls._load_patches_from_module(plugins_module)
            return

        _cache: set[type[BasePatch]] = set()

        def seen(patch_cls: type[BasePatch]) -> bool:
            _seen = patch_cls in _cache
            _cache.add(patch_cls)
            return _seen

        for submodule_info in pkgutil.walk_packages(plugins_path, prefix=f"{plugins_module_name}."):
            if not submodule_info.ispkg:
                for patch_cls in cls._load_patches_from_module(importlib.import_module(submodule_info.name)):
                    if not seen(patch_cls):
                        yield patch_cls

    @staticmethod
    def _load_patches_from_module(plugin_module: ModuleType) -> list[type[BasePatch]]:
        return [
            obj
            for obj in vars(plugin_module).values()
            if isinstance(obj, type) and issubclass(obj, BasePatch) and not inspect.isabstract(obj)
        ]

    @staticmethod
    @contextlib.contextmanager
    def mock_import(context: str, *, forbidden_imports: Iterable[str] = ()) -> Iterator[None]:
        import re

        if isinstance(forbidden_imports, str):
            forbidden_imports = (forbidden_imports,)

        forbidden_modules = {module: re.compile(r"{}(?:\.\w+)*".format(module)) for module in set(forbidden_imports) if module}

        if not forbidden_modules:  # Do not need to mock then
            yield
            return

        def is_forbidden_module(resolved_name: str) -> str | None:
            return next((module_name for module_name, pattern in forbidden_modules.items() if pattern.match(resolved_name)), None)

        patch = _PatchCollectorType._patch

        original_import = __import__
        patch_package = __package__

        @no_type_check
        def import_mock(name, globals=None, locals=None, fromlist=(), level=0):
            if globals is not None:
                importer_name = globals.get("__name__", None)
                importer_path = globals.get("__file__", None)
            else:
                importer_name = importer_path = None
            resolved_name = name
            if level > 0:
                actual_package = str(globals["__name__"])
                for _ in range(level):
                    actual_package = actual_package.rpartition(".")[0]
                resolved_name = f"{actual_package}.{name}"
            if patch_package not in resolved_name and (forbidden_module := is_forbidden_module(resolved_name)):
                msg = f"{forbidden_module!r} must not be imported during patch {context}"
                raise ImportError(msg, name=importer_name, path=importer_path)
            return original_import(name, globals, locals, fromlist, level)

        with patch("builtins.__import__", import_mock), patch("importlib.__import__", import_mock):
            yield

    @staticmethod
    @contextlib.contextmanager
    def _patch(target: str, new: Any) -> Iterator[None]:
        module_name, _, target_name = target.rpartition(".")
        module = importlib.import_module(module_name)
        default_value: Any = getattr(module, target_name)
        setattr(module, target_name, new)
        try:
            yield
        finally:
            setattr(module, target_name, default_value)


PatchCollector: Final[_PatchCollectorType] = _PatchCollectorType()
