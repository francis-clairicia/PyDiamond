# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's system module"""

__all__ = [
    "BoundConfiguration",
    "ConfigError",
    "Configuration",
    "EmptyOptionNameError",
    "InitializationError",
    "InvalidAliasError",
    "JThread",
    "MetaNonCopyable",
    "MetaSingleton",
    "NonCopyable",
    "OptionAttribute",
    "OptionError",
    "RThread",
    "Singleton",
    "Thread",
    "UnknownOptionError",
    "UnregisteredOptionError",
    "cache",
    "initializer",
    "jthread",
    "lru_cache",
    "only_for_concrete_class",
    "rthread",
    "set_constant_directory",
    "set_constant_file",
    "setdefaultattr",
    "thread",
    "tp_cache",
    "valid_float",
    "valid_integer",
    "valid_optional_float",
    "valid_optional_integer",
    "wraps",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


############ Package initialization ############
from .configuration import (
    BoundConfiguration,
    ConfigError,
    Configuration,
    EmptyOptionNameError,
    InitializationError,
    InvalidAliasError,
    OptionAttribute,
    OptionError,
    UnknownOptionError,
    UnregisteredOptionError,
    initializer,
)
from .non_copyable import MetaNonCopyable, NonCopyable
from .path import set_constant_directory, set_constant_file
from .singleton import MetaSingleton, Singleton
from .threading import JThread, RThread, Thread, jthread, rthread, thread
from .utils import (
    cache,
    lru_cache,
    only_for_concrete_class,
    setdefaultattr,
    tp_cache,
    valid_float,
    valid_integer,
    valid_optional_float,
    valid_optional_integer,
    wraps,
)
