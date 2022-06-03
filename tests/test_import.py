# -*- coding: Utf-8 -*-

from __future__ import annotations

from types import ModuleType
from typing import TYPE_CHECKING, no_type_check

import pytest

from .mock.sys import MockVersionInfo, unload_module

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def unload_pygame(monkeypatch: MonkeyPatch) -> None:
    return unload_module("pygame", include_submodules=True, monkeypatch=monkeypatch)


@pytest.fixture(autouse=True)
def unload_py_diamond(monkeypatch: MonkeyPatch) -> None:
    return unload_module("py_diamond", include_submodules=True, monkeypatch=monkeypatch)


@pytest.mark.functional
class TestGlobalImport:
    @pytest.mark.parametrize(
        ["submodule_name"],
        [
            ("audio",),
            ("environ",),
            ("graphics",),
            ("math",),
            ("network",),
            ("resource",),
            ("system",),
            ("window",),
        ],
        ids=lambda name: f"py_diamond.{name}",
    )
    def test__import__successful_auto_import_submodule(self, submodule_name: str) -> None:
        import sys

        submodule_fullname = f"py_diamond.{submodule_name}"

        # Simple check to ensure the unload_* fixtures do their jobs
        assert not any(n == "py_diamond" or n.startswith(submodule_fullname) for n in tuple(sys.modules))

        import py_diamond

        assert hasattr(py_diamond, submodule_name)
        assert isinstance(getattr(py_diamond, submodule_name), ModuleType)
        assert submodule_fullname in sys.modules

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
