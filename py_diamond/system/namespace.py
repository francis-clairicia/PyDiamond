# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ClassNamespace objects module"""

__all__ = ["ClassNamespace", "MetaClassNamespace"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from operator import truth
from typing import Any, Dict, Tuple, Type, TypeVar


class MetaClassNamespace(type):
    __Self = TypeVar("__Self", bound="MetaClassNamespace")

    def __new__(
        metacls: Type[__Self],
        /,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        *,
        frozen: bool = False,
        **kwargs: Any,
    ) -> __Self:
        if "__slots__" in namespace:
            raise ValueError("'__slots__' must not be defined")
        if not frozen:
            for b in bases:
                if isinstance(b, MetaClassNamespace):
                    frozen = getattr(b, "_frozen_class_namespace_")
                    if frozen:
                        break
        namespace["__slots__"] = ()
        namespace["_frozen_class_namespace_"] = bool(frozen)
        namespace["_class_namespace_was_init_"] = False
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __init__(
        cls,
        /,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)
        setattr(cls, "_class_namespace_was_init_", True)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"{cls.__module__}.{cls.__name__} is cannot be instantiated")

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if getattr(cls, "_class_namespace_was_init_"):
            if cls.is_frozen():
                raise AttributeError(f"{cls.__module__}.{cls.__name__}: Frozen class namespace")
            if name in ("_frozen_class_namespace_", "_class_namespace_was_init_"):
                raise AttributeError(f"{name!r} is read-only")
        return super().__setattr__(name, value)

    def is_frozen(cls) -> bool:
        return truth(getattr(cls, "_frozen_class_namespace_", False))

    del __Self


class ClassNamespace(metaclass=MetaClassNamespace):
    pass
