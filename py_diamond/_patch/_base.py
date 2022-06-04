# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch base class module"""

from __future__ import annotations

import os
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
        patch_disable_value: str = os.environ.get("PYDIAMOND_PATCH_DISABLE", "")
        if patch_disable_value.lower() == "all":
            return False
        cls = self.__class__
        return cls.__name__ not in [patch_name for name in patch_disable_value.split(":") if (patch_name := name.strip())]

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
