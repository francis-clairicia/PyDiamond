# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class MockMixerModule(NamedTuple):
    """
    Mock of pygame.mixer module

    Mocks only the functions used by PyDiamond and needed for test.
    """

    pre_init: MagicMock
    init: MagicMock
    get_init: MagicMock
    quit: MagicMock
    stop: MagicMock
    pause: MagicMock
    unpause: MagicMock
    fadeout: MagicMock
    set_num_channels: MagicMock
    get_num_channels: MagicMock
    set_reserved: MagicMock
    find_channel: MagicMock
    get_busy: MagicMock
    get_sdl_mixer_version: MagicMock


@pytest.fixture
def mock_pygame_mixer_module(mocker: MockerFixture) -> MockMixerModule:
    return MockMixerModule._make(mocker.patch(f"pygame.mixer.{field}") for field in MockMixerModule._fields)
