# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockFreetypeModule(NamedTuple):
    """
    Mock of pygame.freetype module

    Mocks only the functions used by PyDiamond and needed for test.
    """

    init: MagicMock
    get_init: MagicMock
    quit: MagicMock

    get_default_font: MagicMock
    get_default_resolution: MagicMock

    Font: MagicMock


@pytest.fixture
def mock_pygame_freetype_module(mocker: MockerFixture) -> MockFreetypeModule:
    return MockFreetypeModule._make(
        mocker.patch(f"pygame.freetype.{field}", autospec=True) for field in MockFreetypeModule._fields
    )
