# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockMouseModule(NamedTuple):
    """
    Mock of pygame.mouse module

    Mocks only the functions used by PyDiamond and needed for test.
    """

    get_cursor: MagicMock
    set_cursor: MagicMock


@pytest.fixture
def mock_pygame_mouse_module(mocker: MockerFixture) -> MockMouseModule:
    return MockMouseModule._make(mocker.patch(f"pygame.mouse.{field}", autospec=True) for field in MockMouseModule._fields)
