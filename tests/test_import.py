# -*- coding: Utf-8 -*

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@pytest.mark.functional
class TestGlobalImport:
    @pytest.fixture(autouse=True)
    def unload_pygame(self, monkeypatch: MonkeyPatch) -> None:
        import sys

        for module in filter(lambda m: re.match(r"pygame(?:\..+)?", m), tuple(sys.modules)):
            monkeypatch.delitem(sys.modules, module, raising=False)

    @pytest.fixture(autouse=True)
    def unload_py_diamond(self, monkeypatch: MonkeyPatch) -> None:
        import sys

        for module in filter(lambda m: re.match(r"py_diamond(?:\..+)?", m), tuple(sys.modules)):
            monkeypatch.delitem(sys.modules, module, raising=False)

    def test__import__successful_import(self) -> None:
        # Arrange
        import sys

        assert not any(n.startswith("py_diamond") for n in tuple(sys.modules))

        # Act
        import py_diamond  # pyright: reportUnusedImport=false

        # Assert
        assert "py_diamond" in sys.modules
        assert "py_diamond.audio" in sys.modules
        assert "py_diamond.environ" in sys.modules
        assert "py_diamond.graphics" in sys.modules
        assert "py_diamond.math" in sys.modules
        assert "py_diamond.network" in sys.modules
        assert "py_diamond.resource" in sys.modules
        assert "py_diamond.system" in sys.modules
        assert "py_diamond.window" in sys.modules
