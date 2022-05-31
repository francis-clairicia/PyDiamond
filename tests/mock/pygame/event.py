# -*- coding: Utf-8 -*

from __future__ import annotations

from typing import TYPE_CHECKING, NamedTuple

import pygame

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pygame.event import Event

    from .display import MockDisplayModule


class MockEventModule:
    """
    Mock of pygame.event module

    Reproduce approximately the behaviour of the real implementation.

    This class is essentially used for 'monkeypatch' fixture, or as side effect for pytest_mock.

    Mocks only the functions used by PyDiamond.
    """

    def __init__(self, mock_display: MockDisplayModule) -> None:
        self._queue: list[Event] = []
        self._display: MockDisplayModule = mock_display

    def get(self) -> list[Event]:
        # Deliberately omit the parameters
        if not self._display.get_init():
            raise pygame.error("video system not initialized")
        queue, self._queue[:] = self._queue, []
        return queue

    def clear(self) -> None:
        # Deliberately omit the parameters
        if not self._display.get_init():
            raise pygame.error("video system not initialized")
        del self._queue[:]


class PatchedEventModule(NamedTuple):
    get: MagicMock
    clear: MagicMock
