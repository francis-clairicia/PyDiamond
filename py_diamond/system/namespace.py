# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ClassNamespace objects module"""

__all__ = ["ClassNamespace", "MetaClassNamespace"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from typing import Any, Dict, Tuple, Type, TypeVar


class MetaClassNamespace(type):
    __T = TypeVar("__T", bound="MetaClassNamespace")

    def __new__(
        metacls: Type[__T],
        /,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        *,
        frozen: bool = False,
        **kwargs: Any,
    ) -> __T:
        if "__slots__" in namespace:
            raise ValueError("'__slots__' must not be defined")
        namespace["__slots__"] = ()
        namespace["_frozen_class_namespace_"] = bool(frozen)
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"{cls.__module__}.{cls.__name__} is cannot be instantiated")

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if getattr(cls, "_frozen_class_namespace_", False):
            raise AttributeError(f"{cls.__module__}.{cls.__name__}: Frozen class namespace")
        if name == "_frozen_class_namespace_":
            raise AttributeError(f"{name!r} is read-only")
        return super().__setattr__(name, value)


class ClassNamespace(metaclass=MetaClassNamespace):
    pass
