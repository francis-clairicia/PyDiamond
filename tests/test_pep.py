# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
import os.path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.functional
class TestPEP008:
    def test__import__no_import_between_future_import_and_dunder_all_declaration(self, pydiamond_rootdir: Path) -> None:
        # Arrange
        import ast

        invalid_files: set[str] = set()

        # Act
        for root, _, files in os.walk(pydiamond_rootdir):
            for file in files:
                if not file.endswith(".py"):
                    continue
                file = os.path.join(root, file)
                with open(file, "r") as file_fp:
                    source: str = file_fp.read()
                tree = ast.parse(source, file)
                future_import_found: bool = False
                other_import_than_future_found: bool = False
                for node in tree.body:
                    match node:
                        case ast.ImportFrom(module="__future__"):
                            future_import_found = True
                            continue
                        case ast.Import() | ast.ImportFrom():
                            other_import_than_future_found = True
                            continue
                        case ast.Assign(targets=[ast.Name(id="__all__")]) | ast.AnnAssign(target=ast.Name(id="__all__")):
                            if future_import_found and other_import_than_future_found:
                                invalid_files.add(os.path.relpath(file, str(pydiamond_rootdir.parent)))
                                break
                        case _:
                            continue

        # Assert
        assert not invalid_files


@pytest.mark.functional
class TestPEP484:
    def test__stubs__check_future_annotations_imports_not_present(self, pydiamond_rootdir: Path) -> None:
        # Arrange
        import ast

        stub_with_future_annotations_import: set[str] = set()

        # Act
        for root, _, files in os.walk(pydiamond_rootdir):
            for file in files:
                if not file.endswith(".pyi"):
                    continue
                file = os.path.join(root, file)
                with open(file, "r") as file_fp:
                    source: str = file_fp.read()
                tree = ast.parse(source, file)
                for node in tree.body:
                    match node:
                        case ast.ImportFrom(module="__future__", names=names) if any(a.name == "annotations" for a in names):
                            stub_with_future_annotations_import.add(os.path.relpath(file, str(pydiamond_rootdir.parent)))
                            break
                        case _:
                            continue

        # Assert
        assert not stub_with_future_annotations_import


@pytest.mark.functional
class TestPEP561:
    def test__py_typed__exists_in_all_packages(self, pydiamond_rootdir: Path) -> None:
        # Arrange
        folder_without_py_typed_file: set[str] = set()

        # Act
        for root, _, files in os.walk(pydiamond_rootdir):
            if os.path.basename(root) == "__pycache__":
                continue
            if "py.typed" not in files:
                folder_without_py_typed_file.add(os.path.relpath(root, str(pydiamond_rootdir.parent)))

        # Assert
        assert not folder_without_py_typed_file
