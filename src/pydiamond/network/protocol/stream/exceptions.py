# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Stream network packet protocol exceptions definition module"""

from __future__ import annotations

__all__ = ["IncrementalDeserializeError"]

from ..exceptions import DeserializeError


class IncrementalDeserializeError(DeserializeError):
    def __init__(self, message: str, remaining_data: bytes) -> None:
        super().__init__(message)
        self.remaining_data: bytes = remaining_data
