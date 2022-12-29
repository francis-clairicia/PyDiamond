# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, no_type_check

from pydiamond._patch.plugins.fix_typing import OverrideFinalFunctionPatch

import pytest

from ...mock.sys import MockVersionInfo, unload_module

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestFixTypingFinal:
    @pytest.fixture(autouse=True)
    @staticmethod
    def unload_typing_module(monkeypatch: pytest.MonkeyPatch) -> None:
        # Unload the modules first
        unload_module("typing", True, monkeypatch)

    @pytest.fixture
    @staticmethod
    def patch() -> Iterator[OverrideFinalFunctionPatch]:
        patch = OverrideFinalFunctionPatch()
        patch.setup()
        yield patch
        patch.teardown()

    @pytest.fixture
    @staticmethod
    def force_sys_version_310(mocker: MockerFixture) -> None:
        mocker.patch("sys.version_info", MockVersionInfo(3, 10, 0, "final", 0))

    @pytest.mark.usefixtures("force_sys_version_310")
    def test____run____apply_typing_extensions_final(
        self,
        patch: OverrideFinalFunctionPatch,
    ) -> None:
        # Arrange
        import typing

        import typing_extensions

        # Act
        patch.run()

        # Assert
        assert typing.final is typing_extensions.final

    @pytest.mark.usefixtures("force_sys_version_310")
    def test____run____apply_static_method_final_patch_if_typing_extensions_does_not_exist(
        self,
        patch: OverrideFinalFunctionPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import typing

        original_import = __import__

        @no_type_check
        def import_mock(name: str, globals=None, locals=None, fromlist=(), level=0):
            if name.startswith("typing_extensions"):
                raise ModuleNotFoundError(name)
            return original_import(name, globals, locals, fromlist, level)

        mocker.patch("builtins.__import__", import_mock)

        # Act
        patch.run()

        # Assert
        assert typing.final is OverrideFinalFunctionPatch.final

    @pytest.mark.parametrize("version_info", [MockVersionInfo(3, 11, 0, "beta", 5), MockVersionInfo(3, 12, 0, "alpha", 1)])
    def test____run____do_not_apply_patch_for_python_311_and_greater(
        self,
        version_info: MockVersionInfo,
        patch: OverrideFinalFunctionPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import typing

        default_final = typing.final

        mocker.patch("sys.version_info", version_info)

        # Act
        patch.run()

        # Assert
        assert typing.final is default_final
