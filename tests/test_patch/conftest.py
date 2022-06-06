# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib

import pytest

from ..mock.sys import unload_module


@pytest.fixture(scope="module", autouse=True)
def disable_auto_patch_run(monkeypatch_module: pytest.MonkeyPatch) -> None:
    # Import py_diamond will automatically apply patches, so we silently disable all the patches
    from _pytest.monkeypatch import MonkeyPatch

    unload_module("pygame", include_submodules=True, monkeypatch=monkeypatch_module)
    unload_module("py_diamond", include_submodules=True, monkeypatch=monkeypatch_module)
    with MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("PYDIAMOND_PATCH_DISABLE", "all")
        # Then we import the package
        importlib.import_module("py_diamond")
