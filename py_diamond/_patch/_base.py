# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch base class module"""

from __future__ import annotations

__all__ = ["BasePatch"]

import os
import re
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
        if match := re.match(r"context\[\s*(?P<contexts>\w+(?:\s*,\s*\w+)*)\s*\]", patch_disable_value):
            contexts: set[str] = set(filter(None, (name.strip() for name in match.group("contexts").split(","))))
            valid_contexts = set(name for name in contexts if name in PatchContext._member_map_)
            if unknown_contexts := contexts - valid_contexts:
                import warnings

                warnings.warn(f"Unknown patch contexts caught in environment: {', '.join(map(repr, unknown_contexts))}")

            return cls.get_required_context() not in [PatchContext[name] for name in valid_contexts]

        patches: list[str] = list(filter(None, (name.strip() for name in patch_disable_value.split(":"))))
        return cls.get_name() not in patches

    def setup(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        pass
