# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from py_diamond._patch._base import BasePatch


@pytest.mark.functional
class TestPatchEnvDisable:
    ALL_PATCHES = [
        "fix_enum.IntEnumMonkeyPatch",
        "fix_typing.OverrideFinalFunctionsPatch",
        "environment.ArrangePygameEnvironmentBeforeImport",
        "environment.VerifyBooleanEnvironmentVariables",
    ]

    @pytest.fixture(params=ALL_PATCHES)
    @staticmethod
    def patch_cls(request: Any) -> type[BasePatch]:
        patch_qualname: str = request.param
        module_path, _, patch_name = patch_qualname.rpartition(".")
        module_path = f"py_diamond._patch.plugins.{module_path}"
        patch_cls: type[BasePatch] = getattr(importlib.import_module(module_path), patch_name)
        return patch_cls

    @pytest.fixture
    @staticmethod
    def patch(patch_cls: type[BasePatch]) -> BasePatch:
        return patch_cls()

    def test__patch__must_not_be_run_if_disabled_from_env(
        self,
        patch: BasePatch,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        monkeypatch.setenv("PYDIAMOND_PATCH_DISABLE", patch.__class__.__name__)

        # Act
        must_be_run = patch.must_be_run()

        # Assert
        assert not must_be_run

    def test__patch__must_not_be_run_if_disabled_from_env_using_all(
        self,
        patch: BasePatch,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        monkeypatch.setenv("PYDIAMOND_PATCH_DISABLE", "all")

        # Act
        must_be_run = patch.must_be_run()

        # Assert
        assert not must_be_run
