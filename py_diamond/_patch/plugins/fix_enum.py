# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch plugins module"""

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


import sys

if sys.version_info < (3, 11):

    def plugin__int_enum_monkeypatch() -> None:
        from enum import IntEnum

        setattr(IntEnum, "__str__", int.__str__)
        setattr(IntEnum, "__format__", int.__format__)
