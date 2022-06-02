# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment checking module"""

from __future__ import annotations

__all__ = ["check_booleans"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from typing import Any, Final, Sequence, overload

BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES: Final[Sequence[str]] = (
    "PYGAME_BLEND_ALPHA_SDL2",
    "PYGAME_FREETYPE",
    "PYGAME_HIDE_SUPPORT_PROMPT",
    "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
    "SDL_VIDEO_CENTERED",
    "SDL_VIDEO_ALLOW_SCREENSAVER",
)


@overload
def check_booleans() -> None:
    ...


@overload
def check_booleans(*, only: Sequence[str]) -> None:
    ...


@overload
def check_booleans(*, exclude: Sequence[str]) -> None:
    ...


def check_booleans(*, only: Sequence[str] | Any = None, exclude: Sequence[str] | Any = None) -> None:
    import os

    environ = os.environ
    del os

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
