# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Singleton class module"""

from __future__ import annotations

__all__ = ["Singleton", "SingletonMeta"]

from collections.abc import Callable
from types import MethodType
from typing import Any, final

from .object import Object, ObjectMeta
from .utils.abc import isabstractclass


class SingletonMeta(ObjectMeta):
    def __new__[Self: SingletonMeta](
        mcs: type[Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> Self:
        kwargs.pop("abstract", None)
        kwargs.pop("lazy", None)

        call_twice_error_wrapper = mcs.__call_twice_error_wrapper

        for constructor_attr in ("__new__", "__init__"):
            default_constructor: Callable[..., Any] = getattr(bases[0] if bases else object, constructor_attr)
            constructor: Callable[..., Any] = namespace.pop(constructor_attr, default_constructor)
            namespace[constructor_attr] = call_twice_error_wrapper(constructor)

        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        abstract: bool = False,
        lazy: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)
        cls.__abstractsingleton__: bool = bool(abstract or isabstractclass(cls))
        if not cls.__abstractsingleton__:
            final(cls)
            setattr(cls, "_singleton_instance_", None)
            if not lazy:
                cls()
        elif lazy:
            raise ValueError("Cannot set 'lazy' parameter for abstract singletons")

    def __call__(cls) -> Any:
        return cls.instance

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("_singleton_instance_", "__abstractsingleton__") and name in vars(cls):
            if name == "_singleton_instance_":
                raise TypeError("Cannot modify singleton instance")
            raise AttributeError(f"{name} is a read-only attribute")
        if name in ("__new__", "__init__"):
            raise TypeError("Cannot modify singleton constructors")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name in ("_singleton_instance_", "__abstractsingleton__") and name in vars(cls):
            if name == "_singleton_instance_":
                raise TypeError("Cannot modify singleton instance")
            raise AttributeError(f"{name} is a read-only attribute")
        if name in ("__new__", "__init__"):
            raise TypeError("Cannot modify singleton constructors")
        return super().__delattr__(name)

    @property
    @final
    def instance[_T](cls: type[_T]) -> _T:
        try:
            instance: _T | None = vars(cls)["_singleton_instance_"]
        except KeyError:
            raise TypeError(f"{cls.__qualname__} cannot be instantiated") from None
        if instance is None:
            instance = cls.__new__(cls)
            cls.__init__(instance)
            super().__setattr__("_singleton_instance_", instance)  # type: ignore[misc]
        return instance

    class __call_twice_error_wrapper:
        def __init__(self, func: Callable[..., Any]) -> None:
            self.__func__ = func

        @property
        def __wrapped__(self) -> Callable[..., Any]:
            return self.__func__

        def __call__(self, __cls_or_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            cls: Any = __cls_or_self if isinstance(__cls_or_self, type) else type(__cls_or_self)
            if not isinstance(cls, SingletonMeta):
                raise TypeError("Called from a non-singleton class")
            if cls.__abstractsingleton__:
                raise TypeError(f"{cls.__qualname__} cannot be instantiated")
            if "_singleton_instance_" in vars(cls) and vars(cls)["_singleton_instance_"] is not None:
                raise TypeError("Cannot instantiate a singleton twice")
            func = self.__func__
            return func(__cls_or_self, *args, **kwargs)

        def __get__(self, obj: object, objtype: type | None = None, /) -> Callable[..., Any]:
            if obj is None:
                return self
            return MethodType(self, obj)


class Singleton(Object, metaclass=SingletonMeta, abstract=True):
    pass
