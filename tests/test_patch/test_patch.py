# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pydiamond._patch._base import BasePatch


@pytest.mark.functional
class TestPatchCommon:
    ALL_PATCHES = [
        "fix_typing.OverrideFinalFunctionsPatch",
        "environment.ArrangePygameEnvironmentBeforeImport",
        "environment.VerifyBooleanEnvironmentVariables",
        "pygame_patch.PygamePatch",
    ]
    EXPECTED_CONTEXT = {
        "fix_typing.OverrideFinalFunctionsPatch": "BEFORE_ALL",
        "environment.ArrangePygameEnvironmentBeforeImport": "BEFORE_IMPORTING_PYGAME",
        "environment.VerifyBooleanEnvironmentVariables": "BEFORE_IMPORTING_SUBMODULES",
        "pygame_patch.PygamePatch": "AFTER_IMPORTING_PYGAME",
    }

    @pytest.fixture(params=ALL_PATCHES)
    @staticmethod
    def patch_qualname(request: Any) -> str:
        patch_qualname: str = request.param
        return patch_qualname

    @pytest.fixture
    @staticmethod
    def patch_cls(patch_qualname: str) -> type[BasePatch]:
        module_path, _, patch_name = patch_qualname.rpartition(".")
        module_path = f"pydiamond._patch.plugins.{module_path}"
        patch_cls: type[BasePatch] = getattr(importlib.import_module(module_path), patch_name)
        return patch_cls

    # @pytest.fixture
    # @staticmethod
    # def patch(patch_cls: type[BasePatch]) -> BasePatch:
    #     return patch_cls()

    def test__patch__get_name(self, patch_cls: type[BasePatch], patch_qualname: str) -> None:
        assert patch_cls.get_name() == f"plugins.{patch_qualname}"

    def test__patch__required_context(self, patch_cls: type[BasePatch], patch_qualname: str) -> None:
        from pydiamond._patch._base import PatchContext

        expected_context = PatchContext[self.EXPECTED_CONTEXT[patch_qualname]]

        assert patch_cls.get_required_context() is expected_context
