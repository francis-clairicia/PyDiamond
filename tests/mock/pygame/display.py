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

    The default side effect for each mock is to call the default implementation

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


def _mock_pygame_display_module_func(name: str, mocker: MockerFixture) -> MagicMock:
    import pygame.display

    return mocker.patch(f"pygame.display.{name}", side_effect=getattr(pygame.display, name))


@pytest.fixture
def mock_pygame_display_module(mocker: MockerFixture) -> MockDisplayModule:
    return MockDisplayModule._make(_mock_pygame_display_module_func(field, mocker) for field in MockDisplayModule._fields)
