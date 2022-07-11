############ Module declaration ############
from __future__ import annotations

from typing import Final

__all__: Final[list[str]] = []

__author__: Final[str]
__copyright__: Final[str]
__credits__: Final[list[str]]
__license__: Final[str]
__version__: Final[str]
__maintainer__: Final[str]
__email__: Final[str]
__status__: Final[str]

from . import (
    audio as audio,
    environ as environ,
    graphics as graphics,
    math as math,
    network as network,
    resource as resource,
    system as system,
    version as version,
    warnings as warnings,
    window as window,
)
from .version import version_info as version_info

__patches__: Final[frozenset[str]]
