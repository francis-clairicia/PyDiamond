# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch base class module"""

from __future__ import annotations

__all__ = ["BasePatch"]

import os
from abc import ABCMeta, abstractmethod
from enum import IntEnum, auto, unique


@unique
class PatchContext(IntEnum):
    BEFORE_ALL = auto()
    BEFORE_IMPORTING_PYGAME = auto()
    AFTER_IMPORTING_PYGAME = auto()
    BEFORE_IMPORTING_SUBMODULES = auto()
    AFTER_IMPORTING_SUBMODULES = auto()
    AFTER_ALL = auto()

    def __repr__(self) -> str:
        return f"<{type(self).__name__}.{self.name}: {self.value}>"

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


class BasePatch(metaclass=ABCMeta):
    run_context: PatchContext

    @classmethod
    def get_name(cls) -> str:
        return f"{cls.__module__.removeprefix(__package__ + '.')}.{cls.__name__}"

    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.BEFORE_ALL

    @classmethod
    def enabled(cls) -> bool:
        patch_disable_value: str = os.environ.get("PYDIAMOND_PATCH_DISABLE", "")
        if patch_disable_value.lower() == "all":
            return False
        return cls.get_name() not in [patch_name for name in patch_disable_value.split(":") if (patch_name := name.strip())]

    def setup(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        pass
