# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's system module"""

__all__ = [
    "AutoLowerNameEnum",
    "AutoUpperNameEnum",
    "BoundConfiguration",
    "ClassNamespace",
    "ConfigError",
    "Configuration",
    "EmptyOptionNameError",
    "InitializationError",
    "InvalidAliasError",
    "MetaClassNamespace",
    "MetaNoDuplicate",
    "MetaNonCopyable",
    "MetaSingleton",
    "NoDuplicate",
    "NonCopyable",
    "OptionAttribute",
    "OptionError",
    "RThread",
    "Singleton",
    "StrEnum",
    "Thread",
    "UnknownOptionError",
    "UnregisteredOptionError",
    "cache",
    "concreteclass",
    "concreteclasscheck",
    "concreteclassmethod",
    "dsuppress",
    "forbidden_call",
    "initializer",
    "isabstractmethod",
    "isconcreteclass",
    "lru_cache",
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
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
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
from .duplicate import MetaNoDuplicate, NoDuplicate
from .enum import AutoLowerNameEnum, AutoUpperNameEnum, StrEnum
from .namespace import ClassNamespace, MetaClassNamespace
from .non_copyable import MetaNonCopyable, NonCopyable
from .path import set_constant_directory, set_constant_file
from .singleton import MetaSingleton, Singleton
from .threading import RThread, Thread, rthread, thread
from .utils import (
    cache,
    concreteclass,
    concreteclasscheck,
    concreteclassmethod,
    dsuppress,
    forbidden_call,
    isabstractmethod,
    isconcreteclass,
    lru_cache,
    setdefaultattr,
    tp_cache,
    valid_float,
    valid_integer,
    valid_optional_float,
    valid_optional_integer,
    wraps,
)
