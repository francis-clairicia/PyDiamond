# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract classes utility module"""

from __future__ import annotations

__all__ = [
    "readable_buffer_to_bytes",
]

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from _typeshed import ReadableBuffer

if TYPE_CHECKING:
    # A readable buffer implements the C-API buffer protocol
    # There is no type hint actually to provide this
    # See PEP-688: https://peps.python.org/pep-0688/

    def readable_buffer_to_bytes(b: ReadableBuffer, /) -> bytes:
        ...

else:
    readable_buffer_to_bytes = bytes
