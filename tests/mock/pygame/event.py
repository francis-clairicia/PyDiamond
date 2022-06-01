# -*- coding: Utf-8 -*

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockEventModule(NamedTuple):
    """
    Mock of pygame.event module

    The default side effect for each mock is to call the default implementation

    Mocks only the functions used by PyDiamond and needed for test.
    """

    get: MagicMock
    clear: MagicMock


def _mock_pygame_event_module_func(name: str, mocker: MockerFixture) -> MagicMock:
    import pygame.event

    return mocker.patch(f"pygame.event.{name}", side_effect=getattr(pygame.event, name))


@pytest.fixture
def mock_pygame_event_module(mocker: MockerFixture) -> MockEventModule:
    return MockEventModule._make(_mock_pygame_event_module_func(field, mocker) for field in MockEventModule._fields)
