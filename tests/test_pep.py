# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
import os.path

import pytest


@pytest.mark.functional
class TestPEP561:
    def test__py_typed__exists_in_all_packages(self, pytestconfig: pytest.Config) -> None:
        # Arrange
        py_diamond_rootdir = pytestconfig.rootpath / "pydiamond"
        folder_without_py_typed_file: set[str] = set()

        # Act
        for root, _, files in os.walk(py_diamond_rootdir):
            if os.path.basename(root) == "__pycache__":
                continue
            if "py.typed" not in files:
                folder_without_py_typed_file.add(root)

        # Assert
        assert not folder_without_py_typed_file
