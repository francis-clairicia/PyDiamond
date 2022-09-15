# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Singleton class module"""

from __future__ import annotations

__all__ = ["Singleton", "SingletonMeta"]


from types import MethodType
from typing import Any, Callable, TypeVar

from .object import Object, ObjectMeta, final
from .utils.abc import isabstractclass

_T = TypeVar("_T")


class SingletonMeta(ObjectMeta):
    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> SingletonMeta:
        kwargs.pop("abstract", None)

        call_twice_error_wrapper = mcs.__call_twice_error_wrapper

        for constructor_attr in ("__new__", "__init__"):
            default_constructor: Callable[..., Any] = getattr(bases[0] if bases else object, constructor_attr)
            constructor: Callable[..., Any] = namespace.pop(constructor_attr, default_constructor)
            namespace[constructor_attr] = call_twice_error_wrapper(constructor)

        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def __init__(
        cls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], *, abstract: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)
        cls.__abstractsingleton__: bool = bool(abstract or isabstractclass(cls))
        if not cls.__abstractsingleton__:
            instance = cls()
            setattr(cls, "_singleton_instance_", instance)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("_singleton_instance_", "__abstractsingleton__") and name in cls.__dict__:
            if name == "_singleton_instance_":
                raise TypeError("Cannot modify singleton instance")
            raise AttributeError(f"{name} is a read-only attribute")
        if name in ("__new__", "__init__"):
            raise TypeError("Cannot modify singleton constructors")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name in ("_singleton_instance_", "__abstractsingleton__") and name in cls.__dict__:
            if name == "_singleton_instance_":
                raise TypeError("Cannot modify singleton instance")
            raise AttributeError(f"{name} is a read-only attribute")
        if name in ("__new__", "__init__"):
            raise TypeError("Cannot modify singleton constructors")
        return super().__delattr__(name)

    @property
    @final
    def instance(cls: type[_T]) -> _T:
        try:
            instance: _T = getattr(cls, "_singleton_instance_")
        except AttributeError:
            raise TypeError(f"{cls.__name__} cannot be instantiated") from None
        return instance

    class __call_twice_error_wrapper:
        def __init__(self, func: Callable[..., Any]) -> None:
            self.__func__ = func

        @property
        def __wrapped__(self) -> Callable[..., Any]:
            return self.__func__

        def __call__(self, __cls_or_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            cls: type = __cls_or_self if isinstance(__cls_or_self, type) else type(__cls_or_self)
            if not isinstance(cls, SingletonMeta):
                raise TypeError("Called from a non-singleton class")
            if cls.__abstractsingleton__:
                raise TypeError(f"{cls.__name__} cannot be instantiated")
            if "_singleton_instance_" in cls.__dict__:
                raise TypeError("Cannot instantiate a singleton twice")
            func = self.__func__
            return func(__cls_or_self, *args, **kwargs)

        def __get__(self, obj: object, objtype: type | None = None, /) -> Callable[..., Any]:
            if obj is None:
                return self
            return MethodType(self, obj)


class Singleton(Object, metaclass=SingletonMeta, abstract=True):
    pass
