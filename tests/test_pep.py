# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.functional
class TestPEP561:
    def test____py_typed____exists_in_all_packages(self, pydiamond_packages_paths: list[Path]) -> None:
        # Arrange
        packages_without_py_typed_file: set[str] = set()

        # Act
        for directory in pydiamond_packages_paths:
            if not (directory / "py.typed").is_file():
                packages_without_py_typed_file.add(os.fspath(directory))

        # Assert
        assert not packages_without_py_typed_file
