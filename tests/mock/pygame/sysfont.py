from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockSysFontModule(NamedTuple):
    """
    Mock of pygame.sysfont module

    Mocks only the functions used by PyDiamond and needed for test.
    """

    get_fonts: MagicMock
    match_font: MagicMock
    SysFont: MagicMock


@pytest.fixture
def mock_pygame_sysfont_module(mocker: MockerFixture) -> MockSysFontModule:
    return MockSysFontModule._make(mocker.patch(f"pygame.sysfont.{field}", autospec=True) for field in MockSysFontModule._fields)
