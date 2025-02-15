############ Module declaration ############
# isort: dont-add-imports

__all__: list[str] = []

from typing import Final, Literal

__author__: Final[str]
__contact__: Final[str]
__copyright__: Final[str]
__credits__: Final[list[str]]
__deprecated__: Final = False
__email__: Final[str]
__license__: Final[str]
__maintainer__: Final[str]
__status__: Final[str]
__version__: Final = "1.0.0.dev3"

from .version import version_info as version_info

__patches__: Final[frozenset[str]]
