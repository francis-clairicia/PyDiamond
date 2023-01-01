# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's patch base class module"""

from __future__ import annotations

__all__ = ["BasePatch"]

import importlib
import inspect
import os
import re
import sys
import typing
import warnings
from abc import ABCMeta, abstractmethod
from enum import IntEnum, auto, unique

import typing_extensions


class PyDiamondPatchWarning(UserWarning):
    pass


@unique
class PatchContext(IntEnum):
    BEFORE_ALL = auto()
    BEFORE_IMPORTING_PYGAME = auto()
    AFTER_IMPORTING_PYGAME = auto()
    BEFORE_IMPORTING_SUBMODULES = auto()
    PATCH_SUBMODULES = auto()
    AFTER_ALL = auto()

    def __str__(self) -> str:
        return f"{type(self).__name__}.{self.name}"


class PatchMeta(ABCMeta):
    def __setattr__(cls, name: str, value: typing.Any, /) -> None:
        if name in ("DISABLED_PATCHES", "DISABLED_CONTEXTS", "ENABLE_PATCH"):
            raise AttributeError("Read-only property")
        super().__setattr__(name, value)

    def __delattr__(self, name: str, /) -> None:
        if name in ("DISABLED_PATCHES", "DISABLED_CONTEXTS", "ENABLE_PATCH"):
            raise AttributeError("Read-only property")
        super().__delattr__(name)


class BasePatch(metaclass=PatchMeta):
    DISABLED_PATCHES: typing.Final[frozenset[str]] = frozenset()
    DISABLED_CONTEXTS: typing.Final[frozenset[PatchContext]] = frozenset()
    ENABLE_PATCH: typing.Final[bool] = True

    @classmethod
    def get_name(cls) -> str:
        return f"{cls.__module__.removeprefix(__package__ + '.')}.{cls.__name__}"

    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.BEFORE_ALL

    @classmethod
    @typing_extensions.final
    def enabled(cls) -> bool:
        if RequiredPatch in cls.__bases__:
            return True
        if not BasePatch.ENABLE_PATCH:
            return False
        return cls.get_name() not in BasePatch.DISABLED_PATCHES and cls.get_required_context() not in BasePatch.DISABLED_CONTEXTS

    def setup(self) -> None:
        pass

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        pass


class RequiredPatch(BasePatch):
    """
    Base class used to identify required patches
    """


def __read_environment() -> None:
    patch_disable_value: str = os.environ.get("PYDIAMOND_PATCH_DISABLE", "")
    if patch_disable_value.lower() == "all":
        type.__setattr__(BasePatch, "ENABLE_PATCH", False)
        return

    invalid_patches: dict[str, str] = dict()
    disabled_contexts: set[PatchContext] = set()
    disabled_patches: set[str] = set()

    for patch_path in set(filter(None, (name.strip() for name in patch_disable_value.split(":")))):
        if match := re.match(r"context\[\s*(?P<contexts>\w+(?:\s*,\s*\w+)*)\s*\]", patch_path):
            contexts: set[str] = set(filter(None, (name.strip().upper() for name in match.group("contexts").split(","))))
            valid_contexts = set(name for name in contexts if name in PatchContext._member_map_)
            if unknown_contexts := contexts - valid_contexts:
                for context in unknown_contexts:
                    invalid_patches[f"context[{context!r}]"] = "Unknown patch context"
            disabled_contexts.update(PatchContext[name] for name in valid_contexts)
            continue
        patch_module_path, _, patch_name = patch_path.rpartition(".")
        if patch_module_path:
            patch_module_path = f"{__package__}.{patch_module_path}"
        else:
            patch_module_path = __package__
        try:
            patch_module = importlib.import_module(patch_module_path)
        except ModuleNotFoundError:
            invalid_patches[patch_path] = f"Module {patch_module_path!r} not found"
            continue
        try:
            patch_cls: typing.Any = getattr(patch_module, patch_name)
        except AttributeError:
            invalid_patches[patch_path] = f"Unable to resolve {patch_name!r} in {patch_module_path!r}"
            continue
        finally:
            del patch_module
            sys.modules.pop(patch_module_path, None)
        if not isinstance(patch_cls, type) or not issubclass(patch_cls, BasePatch):
            invalid_patches[patch_path] = "Invalid patch object"
            continue
        if inspect.isabstract(patch_cls):
            invalid_patches[patch_path] = "It is an abstract base patch class"
            continue
        if RequiredPatch in patch_cls.__bases__:
            invalid_patches[patch_path] = "It is a required patch and cannot be disabled"
            continue
        disabled_patches.add(patch_name)
    type.__setattr__(BasePatch, "DISABLED_CONTEXTS", frozenset(disabled_contexts))
    type.__setattr__(BasePatch, "DISABLED_PATCHES", frozenset(disabled_patches))
    if invalid_patches:
        msg = "Invalid instructions from environment:\n"
        msg += "\n".join(f"- {p}: {m}" for p, m in invalid_patches.items())
        warnings.warn(msg, category=PyDiamondPatchWarning)


__read_environment()

del __read_environment
