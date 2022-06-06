# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment checking module"""

from __future__ import annotations

__all__ = []  # type: list[str]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Any, Final, MutableMapping, Sequence, overload

from .._base import BasePatch, PatchContext

BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES: Final[Sequence[str]] = (
    "PYGAME_BLEND_ALPHA_SDL2",
    "PYGAME_FREETYPE",
    "PYGAME_HIDE_SUPPORT_PROMPT",
    "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
    "SDL_VIDEO_CENTERED",
    "SDL_VIDEO_ALLOW_SCREENSAVER",
)


class AbstractEnvironmentPatch(BasePatch):
    def setup(self) -> None:
        super().setup()

        import os

        self.environ: MutableMapping[str, str] = os.environ

    def teardown(self) -> None:
        del self.environ
        return super().teardown()


class ArrangePygameEnvironmentBeforeImport(AbstractEnvironmentPatch):
    def get_required_context(self) -> PatchContext:
        return PatchContext.BEFORE_IMPORTING_PYGAME

    def run(self) -> None:
        self.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
        self.environ.setdefault("SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1")
        self.environ["PYGAME_FREETYPE"] = "1"

        check_booleans(
            self.environ,
            only=[
                "PYGAME_HIDE_SUPPORT_PROMPT",
                "PYGAME_FREETYPE",
                "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
            ],
        )


class VerifyBooleanEnvironmentVariables(AbstractEnvironmentPatch):
    def get_required_context(self) -> PatchContext:
        return PatchContext.AFTER_IMPORTING_SUBMODULES

    def run(self) -> None:
        return check_booleans(
            self.environ,
            exclude=[
                "PYGAME_HIDE_SUPPORT_PROMPT",
                "PYGAME_FREETYPE",
                "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
            ],
        )


@overload
def check_booleans(environ: MutableMapping[str, str]) -> None:
    ...


@overload
def check_booleans(environ: MutableMapping[str, str], *, only: Sequence[str]) -> None:
    ...


@overload
def check_booleans(environ: MutableMapping[str, str], *, exclude: Sequence[str]) -> None:
    ...


def check_booleans(
    environ: MutableMapping[str, str],
    *,
    only: Sequence[str] | Any = None,
    exclude: Sequence[str] | Any = None,
) -> None:
    if only is not None and exclude is not None:
        raise TypeError("Invalid parameters")
    if only is None:
        only = BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES
    elif isinstance(only, str):
        only = (only,)
    else:
        only = tuple(only)
    if exclude is None:
        exclude = ()
    elif isinstance(exclude, str):
        exclude = (exclude,)
    else:
        exclude = tuple(exclude)
    if any(var not in BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES for var in only):
        raise ValueError(f"Invalid envionment variables for 'only' parameter: {only!r}")
    if any(var not in BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES for var in exclude):
        raise ValueError(f"Invalid envionment variables for 'exclude' parameter: {exclude!r}")
    for var in filter(lambda var: var in environ and var not in exclude, only):
        value = environ[var]
        if value not in ("0", "1"):
            raise ValueError(f"Invalid value for {var!r} environment variable")
        if value == "0":
            environ.pop(var)
