# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import NamedTuple


class Error(NamedTuple):
    lineno: int
    col: int
    message: str
    type: type
