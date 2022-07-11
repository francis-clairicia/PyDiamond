# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from py_diamond._patch._base import BasePatch


@pytest.mark.functional
class TestPatch:
    ALL_PATCHES = [
        "fix_enum.IntEnumMonkeyPatch",
        "fix_typing.OverrideFinalFunctionsPatch",
        "environment.ArrangePygameEnvironmentBeforeImport",
        "environment.VerifyBooleanEnvironmentVariables",
        "pygame_patch.PygamePatch",
        "pygame_patch.PyDiamondEventPatch",
    ]

    @pytest.fixture(params=ALL_PATCHES)
    @staticmethod
    def patch_qualname(request: Any) -> str:
        patch_qualname: str = request.param
        return patch_qualname

    @pytest.fixture
    @staticmethod
    def patch_cls(patch_qualname: str) -> type[BasePatch]:
        module_path, _, patch_name = patch_qualname.rpartition(".")
        module_path = f"py_diamond._patch.plugins.{module_path}"
        patch_cls: type[BasePatch] = getattr(importlib.import_module(module_path), patch_name)
        return patch_cls

    @pytest.fixture
    @staticmethod
    def patch(patch_cls: type[BasePatch]) -> BasePatch:
        return patch_cls()

    def test__patch__get_name(self, patch_cls: type[BasePatch], patch_qualname: str) -> None:
        assert patch_cls.get_name() == f"plugins.{patch_qualname}"
