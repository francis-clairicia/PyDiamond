# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ClassNamespace objects module"""

from __future__ import annotations

__all__ = ["ClassNamespace", "ClassNamespaceMeta"]


from typing import TYPE_CHECKING, Any, Final, TypeVar

from .object import Object, ObjectMeta


class ClassNamespaceMeta(ObjectMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="ClassNamespaceMeta")

    def __new__(
        mcs: type[__Self],
        /,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        frozen: bool = False,
        **kwargs: Any,
    ) -> __Self:
        if "__slots__" in namespace:
            raise ValueError("'__slots__' must not be defined")
        for attr in ("__new__", "__init__"):
            if attr in namespace:
                raise TypeError(f"A ClassNamespace class is not instantiable, so no need to define {attr!r}")
        if not frozen:
            frozen = next(
                (True for b in bases if isinstance(b, ClassNamespaceMeta) and getattr(b, "_frozen_class_namespace_", False)),
                False,
            )
        namespace["__slots__"] = ()
        namespace["_frozen_class_namespace_"] = bool(frozen)
        namespace["_class_namespace_was_init_"] = False
        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def __init__(
        cls,
        /,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)
        super().__setattr__("_class_namespace_was_init_", True)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        raise TypeError(f"{cls.__module__}.{cls.__name__} cannot be instantiated")

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("__new__", "__init__"):
            raise TypeError(f"{cls.__module__}.{cls.__name__} cannot be instantiated")
        if getattr(cls, "_class_namespace_was_init_"):
            if getattr(cls, "_frozen_class_namespace_", False):
                raise AttributeError(f"{cls.__module__}.{cls.__name__}: Frozen class namespace")
            if name in ("_frozen_class_namespace_", "_class_namespace_was_init_"):
                raise AttributeError(f"{name!r} is read-only")
        elif name in ("_frozen_class_namespace_"):
            raise AttributeError(f"{name!r} is read-only")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name in ("__new__", "__init__"):
            raise TypeError(f"{cls.__module__}.{cls.__name__} cannot be instantiated")
        if getattr(cls, "_class_namespace_was_init_"):
            if getattr(cls, "_frozen_class_namespace_", False):
                raise AttributeError(f"{cls.__module__}.{cls.__name__}: Frozen class namespace")
            if name in ("_frozen_class_namespace_", "_class_namespace_was_init_"):
                raise AttributeError(f"{name!r} is read-only")
        elif name in ("_frozen_class_namespace_"):
            raise AttributeError(f"{name!r} is read-only")
        return super().__delattr__(name)


class ClassNamespace(Object, metaclass=ClassNamespaceMeta):
    if TYPE_CHECKING:
        __slots__: Final[tuple[()]] = ()
