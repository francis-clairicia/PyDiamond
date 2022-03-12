# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's environment module"""

__all__ = ["check"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


import typing

BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES: typing.Final[typing.Sequence[str]] = (
    "PYGAME_BLEND_ALPHA_SDL2",
    "PYGAME_FREETYPE",
    "SDL_VIDEO_CENTERED",
    "SDL_VIDEO_ALLOW_SCREENSAVER",
)


def check(environ: typing.MutableMapping[str, str] | None = None) -> None:
    if environ is None:
        import os

        environ = os.environ
        del os
    for var in filter(environ.__contains__, BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES):
        value = environ[var]
        if value not in ("0", "1"):
            raise ValueError(f"Invalid value for {var!r} environment variable")
        if value == "0":
            environ.pop(var)
