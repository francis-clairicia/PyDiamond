# -*- coding: Utf-8 -*

from __future__ import annotations

import re
from functools import partial
from types import ModuleType
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def _unload_module(module_name: str, include_submodules: bool, monkeypatch: MonkeyPatch) -> None:
    import sys

    monkeypatch.delitem(sys.modules, module_name)
    if include_submodules:
        pattern = r"{}(?:\.\w)+".format(module_name)
        for module in filter(partial(re.match, pattern), tuple(sys.modules)):
            monkeypatch.delitem(sys.modules, module, raising=False)


@pytest.fixture(autouse=True)
def unload_pygame(monkeypatch: MonkeyPatch) -> None:
    return _unload_module("pygame", include_submodules=True, monkeypatch=monkeypatch)


@pytest.fixture(autouse=True)
def unload_py_diamond(monkeypatch: MonkeyPatch) -> None:
    return _unload_module("py_diamond", include_submodules=True, monkeypatch=monkeypatch)


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
    def test__import__successful_auto_import(self, submodule_name: str) -> None:
        import sys

        submodule_fullname = f"py_diamond.{submodule_name}"

        # Simple check to ensure the unload_* fixtures do their jobs
        assert not any(n == "py_diamond" or n.startswith(submodule_fullname) for n in tuple(sys.modules))

        import py_diamond

        assert hasattr(py_diamond, submodule_name)
        assert isinstance(getattr(py_diamond, submodule_name), ModuleType)
        assert submodule_fullname in sys.modules
