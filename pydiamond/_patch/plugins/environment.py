# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment checking module"""

from __future__ import annotations

__all__ = []  # type: list[str]

from types import MappingProxyType
from typing import Final, MutableMapping, Sequence, overload

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
    OVERRIDEN_VARIABLES: Final[MappingProxyType[str, str]] = MappingProxyType(
        {
            "PYGAME_HIDE_SUPPORT_PROMPT": "1",
            "PYGAME_FREETYPE": "1",
            "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS": "1",
        }
    )
    FORCE_OVERRIDE: Final[frozenset[str]] = frozenset(
        {
            "PYGAME_FREETYPE",
        }
    )

    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.BEFORE_IMPORTING_PYGAME

    def run(self) -> None:
        for env_var, env_value in self.OVERRIDEN_VARIABLES.items():
            if env_var in self.FORCE_OVERRIDE:
                self.environ[env_var] = env_value
            else:
                self.environ.setdefault(env_var, env_value)

        check_booleans(self.environ, only=list(self.OVERRIDEN_VARIABLES))


class VerifyBooleanEnvironmentVariables(AbstractEnvironmentPatch):
    @classmethod
    def get_required_context(cls) -> PatchContext:
        return PatchContext.BEFORE_IMPORTING_SUBMODULES

    def run(self) -> None:
        return check_booleans(self.environ, exclude=list(ArrangePygameEnvironmentBeforeImport.OVERRIDEN_VARIABLES))


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
    only: Sequence[str] | None = None,
    exclude: Sequence[str] | None = None,
) -> None:
    if only is not None and exclude is not None:
        raise TypeError("Invalid parameters")
    if only is None:
        only = BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES
    elif isinstance(only, str):
        only = (only,)
    else:
        only = tuple(set(only))
        if not only:
            raise ValueError("'only' argument: Empty sequence")
    if unknown_vars := set(only) - set(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES):
        raise ValueError(f"Invalid environment variables for 'only' parameter: {', '.join(unknown_vars)}")
    if exclude is None:
        exclude = ()
    elif isinstance(exclude, str):
        exclude = (exclude,)
    else:
        exclude = tuple(set(exclude))
    if unknown_vars := set(exclude) - set(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES):
        raise ValueError(f"Invalid environment variables for 'exclude' parameter: {', '.join(unknown_vars)}")
    for var in (var for var in only if var in environ and var not in exclude):
        value = environ[var]
        if value not in ("0", "1"):
            raise ValueError(f"Invalid value for {var!r} environment variable: {value}")
        if value == "0":
            environ.pop(var)
