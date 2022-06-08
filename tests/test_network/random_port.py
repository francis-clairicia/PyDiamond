# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["random_port"]

from random import randrange as _rand


def random_port() -> int:
    min_port = _rand(5000, 10000)
    max_port = _rand(65000, 65536)
    return _rand(min_port, max_port)
