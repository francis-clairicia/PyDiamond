# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's system module"""

__all__ = [
    "AutoLowerNameEnum",
    "AutoUpperNameEnum",
    "ClassNamespace",
    "ClassNamespaceMeta",
    "ConfigError",
    "Configuration",
    "ConfigurationTemplate",
    "EmptyOptionNameError",
    "InitializationError",
    "InvalidAliasError",
    "NoDuplicate",
    "NoDuplicateMeta",
    "NonCopyable",
    "NonCopyableMeta",
    "Object",
    "ObjectMeta",
    "OptionAttribute",
    "OptionError",
    "RThread",
    "Singleton",
    "SingletonMeta",
    "StrEnum",
    "Thread",
    "UnknownOptionError",
    "UnregisteredOptionError",
    "cache",
    "concreteclass",
    "concreteclasscheck",
    "concreteclassmethod",
    "dsuppress",
    "final",
    "flatten",
    "forbidden_call",
    "initializer",
    "isabstractmethod",
    "isconcreteclass",
    "lru_cache",
    "noexcept",
    "override",
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
    ConfigError,
    Configuration,
    ConfigurationTemplate,
    EmptyOptionNameError,
    InitializationError,
    InvalidAliasError,
    OptionAttribute,
    OptionError,
    UnknownOptionError,
    UnregisteredOptionError,
    initializer,
)
from .duplicate import NoDuplicate, NoDuplicateMeta
from .enum import AutoLowerNameEnum, AutoUpperNameEnum, StrEnum
from .exception import noexcept
from .namespace import ClassNamespace, ClassNamespaceMeta
from .non_copyable import NonCopyable, NonCopyableMeta
from .object import Object, ObjectMeta, final, override
from .path import set_constant_directory, set_constant_file
from .singleton import Singleton, SingletonMeta
from .threading import RThread, Thread, rthread, thread
from .utils import (
    cache,
    concreteclass,
    concreteclasscheck,
    concreteclassmethod,
    dsuppress,
    flatten,
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
