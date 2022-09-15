# -*- coding: Utf-8 -*-

from __future__ import annotations

from functools import cache
from importlib import import_module
from itertools import combinations
from typing import TYPE_CHECKING, no_type_check

import pytest

from .mock.sys import MockVersionInfo, unload_module

if TYPE_CHECKING:
    from pkgutil import ModuleInfo

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@cache
def _catch_all_py_diamond_packages_and_modules() -> list[ModuleInfo]:
    from pkgutil import walk_packages

    py_diamond_spec = import_module("pydiamond").__spec__

    assert py_diamond_spec is not None

    py_diamond_paths = py_diamond_spec.submodule_search_locations or import_module("pydiamond").__path__

    return list(walk_packages(py_diamond_paths, prefix=f"{py_diamond_spec.name}."))


ALL_PYDIAMOND_PACKAGES = [info.name for info in _catch_all_py_diamond_packages_and_modules() if info.ispkg]
ALL_PYDIAMOND_MODULES = [info.name for info in _catch_all_py_diamond_packages_and_modules()]


@cache
def _catch_star_imports_within_packages() -> dict[str, list[str]]:
    import ast
    import inspect

    all_packages: dict[str, list[str]] = {}
    for package_name in ALL_PYDIAMOND_PACKAGES:
        package_file = inspect.getfile(import_module(package_name))
        with open(package_file, "r") as package_fp:
            package_source = package_fp.read()
        tree = ast.parse(package_source, package_file)
        start_import_modules: list[str] = []

        for node in tree.body:
            match node:
                case ast.ImportFrom(module=module, names=[ast.alias(name="*")], level=level):
                    module = "." * level + (module or "")
                    start_import_modules.append(module)
                case _:
                    continue

        if start_import_modules:
            all_packages[package_name] = start_import_modules

    return all_packages


@pytest.mark.functional
class TestGlobalImport:
    @pytest.fixture(autouse=True)
    @staticmethod
    def arrange_environment(monkeypatch: MonkeyPatch) -> None:
        monkeypatch.setenv("PYDIAMOND_TEST_STRICT_FINAL", "1")

    @pytest.fixture(autouse=True)
    @staticmethod
    def unload_pygame(monkeypatch: MonkeyPatch) -> None:
        return unload_module("pygame", include_submodules=True, monkeypatch=monkeypatch)

    @pytest.fixture(autouse=True)
    @staticmethod
    def unload_py_diamond(monkeypatch: MonkeyPatch) -> None:
        return unload_module("pydiamond", include_submodules=True, monkeypatch=monkeypatch)

    @pytest.mark.parametrize("module_name", ALL_PYDIAMOND_MODULES)
    def test__import__successful_import_module_without_circular_import(self, module_name: str) -> None:
        import sys

        # Simple check to ensure the unload_* fixtures do their jobs
        assert not any(n == "pydiamond" or n.startswith(module_name) for n in tuple(sys.modules))

        import_module(module_name)

        assert module_name in sys.modules

    def test__import__raise_custom_message_if_pygame_is_not_installed(self, mocker: MockerFixture) -> None:
        # Forbid import of pygame
        original_import = __import__

        @no_type_check
        def import_mock(name: str, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("pygame"):
                raise ModuleNotFoundError(name)
            return original_import(name, globals, locals, fromlist, level)

        mocker.patch("builtins.__import__", import_mock)

        # Begin test
        with pytest.raises(ModuleNotFoundError, match=r"'pygame' package must be installed in order to use the PyDiamond engine"):
            import pydiamond

            del pydiamond

    def test__import__raise_warning_if_pygame_is_already_imported(self) -> None:
        import pygame

        expected_message = (
            r"'pygame' module already imported, this can cause unwanted behavior\. Consider importing pydiamond first\."
        )
        with pytest.warns(UserWarning, match=expected_message):
            import pydiamond

            del pydiamond

        del pygame

    def test__import__do_not_raise_warning_if_environment_variable_is_set(
        self,
        monkeypatch: MonkeyPatch,
    ) -> None:
        import warnings

        import pygame

        monkeypatch.setenv("PYDIAMOND_IMPORT_WARNINGS", "0")

        with warnings.catch_warnings():
            warnings.simplefilter("error", category=UserWarning)

            import pydiamond

            del pydiamond

        del pygame

    def test__import__raise_error_for_incompatible_python_version(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.version_info", MockVersionInfo(3, 9, 5, "final", 0))

        with pytest.raises(ImportError, match=r"This framework must be run with python >= 3\.10 \(actual=3\.9\.5\)"):
            import pydiamond

            del pydiamond


@pytest.mark.functional
class TestStarImports:
    AUTO_IMPORTED_MODULES: dict[str, list[str]] = _catch_star_imports_within_packages()

    @pytest.mark.parametrize(
        ["module_name", "imported_module_name"],
        sorted(
            (module, imported_module)
            for module, imported_module_list in AUTO_IMPORTED_MODULES.items()
            for imported_module in imported_module_list
        ),
    )
    def test__all__values_from_imported_module_retrieved_in_main_module(
        self,
        module_name: str,
        imported_module_name: str,
    ) -> None:
        # Arrange
        module = import_module(module_name)
        imported_module = import_module(imported_module_name, package=module_name)
        module_namespace = vars(module)
        __all_module__: list[str] = module.__all__
        __all_submodule__: list[str] = imported_module.__all__

        # Act
        missing_names_in_declaration = set(__all_submodule__) - set(__all_module__)
        missing_names_in_namespace = set(__all_submodule__) - set(module_namespace)

        # Assert
        assert not missing_names_in_namespace
        assert not missing_names_in_declaration

    @pytest.mark.parametrize("module_name", ALL_PYDIAMOND_MODULES)
    def test__all__values_declared_exists_in_namespace(self, module_name: str) -> None:
        # Arrange
        module = import_module(module_name)
        module_namespace = vars(module)
        try:
            __all_module__: list[str] = module.__all__
        except AttributeError:
            pytest.fail(f"{module_name!r} does not define __all__ variable")
        if sorted(set(__all_module__)) != sorted(__all_module__):
            pytest.fail(f"{module_name!r}: Duplicates found in __all__")

        # Act
        unknown_names = set(__all_module__) - set(module_namespace)

        # Assert
        assert not unknown_names

    @pytest.mark.parametrize("module_name", sorted(AUTO_IMPORTED_MODULES))
    def test__all__no_conflict_between_submodules(self, module_name: str) -> None:
        # Arrange

        # Act & Assert
        for imported_module_name_lhs, imported_module_name_rhs in combinations(self.AUTO_IMPORTED_MODULES[module_name], r=2):
            imported_module_lhs = import_module(imported_module_name_lhs, package=module_name)
            imported_module_rhs = import_module(imported_module_name_rhs, package=module_name)
            imported_module_all_lhs: list[str] = imported_module_lhs.__all__
            imported_module_all_rhs: list[str] = imported_module_rhs.__all__
            conflicts = set(imported_module_all_lhs) & set(imported_module_all_rhs)
            for name in conflicts:
                assert getattr(imported_module_lhs, name) is getattr(imported_module_rhs, name)
