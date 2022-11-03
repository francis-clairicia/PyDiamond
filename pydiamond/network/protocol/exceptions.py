# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network packet protocol exceptions definition module"""

from __future__ import annotations

__all__ = ["DeserializeError"]


class DeserializeError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
