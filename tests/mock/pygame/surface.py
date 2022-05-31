# -*- coding: Utf-8 -*

from __future__ import annotations

from typing import Any

from pygame import Surface


class MockSurface(Surface):
    """
    Mock of pygame.surface.Surface
    """

    def convert(self, *args: Any, **kwargs: Any) -> MockSurface:
        return MockSurface(self.get_size())

    def convert_alpha(self, *args: Any, **kwargs: Any) -> MockSurface:
        return MockSurface(self.get_size())
