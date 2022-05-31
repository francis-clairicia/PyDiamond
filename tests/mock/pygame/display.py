# -*- coding: Utf-8 -*

from __future__ import annotations

from threading import Event
from typing import TYPE_CHECKING, NamedTuple

import pygame

from .surface import MockSurface

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pygame.surface import Surface


class MockDisplayModule:
    """
    Mock of pygame.display module

    Reproduce approximately the behaviour of the real implementation.

    This class is essentially used for 'monkeypatch' fixture, or as side effect for pytest_mock.

    Mocks only the functions used by PyDiamond.
    """

    _default_render_size = (1920, 1080)

    def __init__(self) -> None:
        self._shared_init_event = Event()
        self._shared_surface: MockSurface | None = None
        self._caption: tuple[str, str] | tuple[()] = ()

    def init(self) -> None:
        if self._caption == ():
            self._caption = "pygame window", "pygame window"
        self._shared_init_event.set()

    def get_init(self) -> bool:
        return self._shared_init_event.is_set()

    def quit(self) -> None:
        self._shared_surface = None
        self._caption = ()
        self._shared_init_event.clear()

    def set_mode(
        self,
        size: tuple[int, int] = (0, 0),
        flags: int = 0,
        depth: int = 0,
        display: int = 0,
        vsync: int = 0,
    ) -> MockSurface:
        width, height = size
        if width < 0 or height < 0:
            size = MockDisplayModule._default_render_size
        self._shared_surface = shared_surface = MockSurface(size)
        return shared_surface

    def get_surface(self) -> MockSurface | None:
        return self._shared_surface

    def flip(self) -> None:
        if not self.get_init():
            raise pygame.error("video system not initialized")
        if self.get_surface() is None:
            raise pygame.error("Display mode not set")
        return

    def set_icon(self, icon: Surface) -> None:
        # The real implementation implicitly initialize pygame.display module
        # Ref: https://www.pygame.org/docs/ref/display.html#pygame.display.set_icon
        self.init()

    def iconify(self) -> bool:
        if not self.get_init():
            raise pygame.error("video system not initialized")
        if self.get_surface() is None:
            raise pygame.error("No open window")
        return True

    def set_caption(self, title: str, icontitle: str | None = None) -> None:
        self._caption = (title, icontitle or title)

    def get_caption(self) -> tuple[str, str] | tuple[()]:
        return self._caption


class PatchedDisplayModule(NamedTuple):
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
