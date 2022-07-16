# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockEventModule(NamedTuple):
    """
    Mock of pygame.event module

    Mocks only the functions used by PyDiamond and needed for test.
    """

    get: MagicMock
    clear: MagicMock
    post: MagicMock
    event_name: MagicMock


@pytest.fixture
def mock_pygame_event_module(mocker: MockerFixture) -> MockEventModule:
    return MockEventModule._make(mocker.patch(f"pygame.event.{field}", autospec=True) for field in MockEventModule._fields)
