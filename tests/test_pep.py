# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
import itertools
import os
import pkgutil
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path


@pytest.mark.functional
class TestPEP561:
    def test____py_typed____exists_in_all_packages(self, pydiamond_rootdirs_list: list[Path]) -> None:
        # Arrange
        packages_without_py_typed_file: set[str] = set()

        # Act
        for directory in itertools.chain.from_iterable(
            map(
                lambda module: (
                    (module_spec.submodule_search_locations if (module_spec := module.__spec__) else module.__path__) or []
                ),
                map(
                    lambda module_info: importlib.import_module(module_info.name),
                    filter(
                        lambda module_info: module_info.ispkg,
                        pkgutil.walk_packages(map(os.fspath, pydiamond_rootdirs_list), prefix="pydiamond."),
                    ),
                ),
            )
        ):
            if not os.path.isfile(os.path.join(directory, "py.typed")):
                packages_without_py_typed_file.add(directory)

        # Assert
        assert not packages_without_py_typed_file
