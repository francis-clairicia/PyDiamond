# -*- coding: Utf-8 -*-

from __future__ import annotations

from importlib import import_module
from itertools import combinations
from types import ModuleType
from typing import TYPE_CHECKING, no_type_check

import pytest

from .mock.sys import MockVersionInfo, unload_module

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestGlobalImport:
    @pytest.fixture(autouse=True)
    @staticmethod
    def unload_pygame(monkeypatch: MonkeyPatch) -> None:
        return unload_module("pygame", include_submodules=True, monkeypatch=monkeypatch)

    @pytest.fixture(autouse=True)
    @staticmethod
    def unload_py_diamond(monkeypatch: MonkeyPatch) -> None:
        return unload_module("py_diamond", include_submodules=True, monkeypatch=monkeypatch)

    @pytest.mark.parametrize(
        "module_name",
        [
            "audio",
            "environ",
            "graphics",
            "math",
            "network",
            "resource",
            "system",
            "window",
        ],
        ids=lambda name: f"py_diamond.{name}",
    )
    def test__import__successful_auto_import_submodule(self, module_name: str) -> None:
        import sys

        module_fullname = f"py_diamond.{module_name}"

        # Simple check to ensure the unload_* fixtures do their jobs
        assert not any(n == "py_diamond" or n.startswith(module_fullname) for n in tuple(sys.modules))

        import py_diamond

        assert hasattr(py_diamond, module_name)
        assert isinstance(getattr(py_diamond, module_name), ModuleType)
        assert module_fullname in sys.modules

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
        with pytest.raises(ImportError, match=r"'pygame' package must be installed in order to use the PyDiamond engine"):
            import py_diamond

            del py_diamond

    def test__import__raise_warning_if_pygame_is_already_imported(self) -> None:
        import pygame

        with pytest.warns(ImportWarning):
            import py_diamond

            del py_diamond

        del pygame

    def test__import__raise_error_for_incompatible_python_version(self, mocker: MockerFixture) -> None:
        mocker.patch("sys.version_info", MockVersionInfo(3, 9, 5, "final", 0))

        with pytest.raises(ImportError, match=r"This framework must be run with python >= 3\.10 \(actual=3\.9\.5\)"):
            import py_diamond

            del py_diamond


@pytest.mark.functional
class TestStarImports:
    AUTO_IMPORTED_MODULES: dict[str, list[str]] = {
        "audio": [
            "mixer",
            "music",
            "sound",
        ],
        "graphics": [
            "animation",
            "button",
            "checkbox",
            "color",
            "drawable",
            "entry",
            "font",
            "form",
            "gradients",
            "grid",
            "image",
            "movable",
            "progress",
            "rect",
            "renderer",
            "scale",
            "scroll",
            "shape",
            "surface",
            "text",
            "theme",
            "transformable",
        ],
        "math": [
            "interpolation",
            "vector2",
        ],
        "network": [
            "client",
            "server",
        ],
        "network.protocol": [
            "base",
            "compressor",
            "encryptor",
            "json",
            "pickle",
            "stream",
        ],
        "network.socket": [
            "base",
            "constants",
            "python",
        ],
        "resource": [
            "loader",
            "manager",
        ],
        "window": [
            "clickable",
            "clock",
            "cursor",
            "dialog",
            "display",
            "event",
            "gui",
            "keyboard",
            "mouse",
            "scene",
            "time",
            "widget",
        ],
    }

    @pytest.mark.parametrize(
        ["module_name", "submodule_name"],
        sorted((module, submodule) for module, submodule_list in AUTO_IMPORTED_MODULES.items() for submodule in submodule_list),
    )
    def test__all__values_from_submodule_retrieved_in_main_module(self, module_name: str, submodule_name: str) -> None:
        # Arrange
        module = import_module(f"py_diamond.{module_name}")
        submodule = import_module(f"py_diamond.{module_name}.{submodule_name}")

        # Act
        __all_module__: list[str] = module.__all__
        __all_submodule__: list[str] = submodule.__all__

        # Assert
        for name in __all_submodule__:
            assert name in __all_module__
            assert name in dir(module)

    @pytest.mark.parametrize("module_name", sorted(AUTO_IMPORTED_MODULES))
    def test__all__values_declared_exists_in_namespace(self, module_name: str) -> None:
        # Arrange
        module = import_module(f"py_diamond.{module_name}")

        # Act
        __all_module__: list[str] = module.__all__

        # Assert
        for name in __all_module__:
            assert name in dir(module)

    @pytest.mark.parametrize("module_name", sorted(AUTO_IMPORTED_MODULES))
    def test__all__no_conflict_between_submodules(self, module_name: str) -> None:
        # Arrange

        # Act & Assert
        for submodule_name_lhs, submodule_name_rhs in combinations(self.AUTO_IMPORTED_MODULES[module_name], r=2):
            submodule_lhs = import_module(f"py_diamond.{module_name}.{submodule_name_lhs}")
            submodule_rhs = import_module(f"py_diamond.{module_name}.{submodule_name_rhs}")
            submodule_all_lhs: list[str] = submodule_lhs.__all__
            submodule_all_rhs: list[str] = submodule_rhs.__all__
            conflicts = set(submodule_all_lhs) & set(submodule_all_rhs)
            for name in conflicts:
                assert getattr(submodule_lhs, name) is getattr(submodule_rhs, name)
