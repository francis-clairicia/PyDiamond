# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
import os.path
import sys
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.functional
class TestPEP561:
    def test____py_typed____exists_in_all_packages(self, pydiamond_rootdirs_list: list[Path]) -> None:
        # Arrange
        folder_without_py_typed_file: set[str] = set()
        pycache_prefix = sys.pycache_prefix or "__pycache__"

        # Act
        for pydiamond_rootdir in pydiamond_rootdirs_list:
            for root, _, files in os.walk(pydiamond_rootdir):
                if os.path.basename(root) == pycache_prefix:
                    continue
                if "py.typed" not in files:
                    folder_without_py_typed_file.add(os.path.relpath(root, str(pydiamond_rootdir.parent)))

        # Assert
        assert not folder_without_py_typed_file
