# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import Sequence

import pytest


# BUG: Random port could cause PermissionError
# Will be fixed on test refacto
def pytest_collection_modifyitems(items: Sequence[pytest.Item]) -> None:
    for item in items:
        if "test_network" in item.nodeid and "test_protocol" not in item.nodeid:
            item.add_marker(pytest.mark.xfail(reason="PermissionError could occur", raises=PermissionError))
