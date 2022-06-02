# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network selector module"""

from __future__ import annotations

__all__ = ["DefaultSelector"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from selectors import BaseSelector

    DefaultSelector: type[BaseSelector]
else:
    try:
        from selectors import PollSelector as DefaultSelector
    except ImportError:
        from selectors import SelectSelector as DefaultSelector
