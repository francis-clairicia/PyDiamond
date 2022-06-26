# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockDisplayModule(NamedTuple):
    """
    Mock of pygame.display module

    Mocks only the functions used by PyDiamond and needed for test.
    """

    init: MagicMock
    get_init: MagicMock
    quit: MagicMock
    set_mode: MagicMock
    get_surface: MagicMock
    flip: MagicMock
    set_icon: MagicMock
    iconify: MagicMock
    set_caption: MagicMock
    get_caption: MagicMock


@pytest.fixture
def mock_pygame_display_module(mocker: MockerFixture) -> MockDisplayModule:
    return MockDisplayModule._make(mocker.patch(f"pygame.display.{field}", autospec=True) for field in MockDisplayModule._fields)
