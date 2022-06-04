# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch base class module"""

from __future__ import annotations

from enum import Enum, auto, unique

__all__ = ["BasePatch"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod


class BasePatch(metaclass=ABCMeta):
    @classmethod
    def get_context(cls) -> PatchContext:
        return PatchContext.BEFORE_ALL

    def must_be_run(self) -> bool:
        return True

    def setup(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        pass


@unique
class PatchContext(Enum):
    BEFORE_ALL = auto()
    BEFORE_IMPORTING_PYGAME = auto()
    AFTER_IMPORTING_PYGAME = auto()
    BEFORE_IMPORTING_SUBMODULES = auto()
    AFTER_IMPORTING_SUBMODULES = auto()
    AFTER_ALL = auto()
