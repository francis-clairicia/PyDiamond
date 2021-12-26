# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Python mangling module"""

__all__ = ["mangle_private_attribute"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


def mangle_private_attribute(cls: type, attribute: str) -> str:
    return f"_{cls.__name__}__{attribute}"
