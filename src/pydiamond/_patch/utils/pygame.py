# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#

from __future__ import annotations

__all__ = ["is_pygame_imported"]

import sys


def is_pygame_imported() -> bool:
    return any(name == "pygame" or name.startswith("pygame.") for name in list(sys.modules))
