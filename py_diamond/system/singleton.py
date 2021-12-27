# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Singleton class module"""

from __future__ import annotations

__all__ = ["MetaSingleton", "Singleton"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta
from types import MethodType
from typing import Any, Callable, Dict, Optional, Tuple, Type, TypeVar

_T = TypeVar("_T")


class MetaSingleton(ABCMeta):
    def __new__(metacls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> MetaSingleton:
        kwargs.pop("abstract", None)
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __init__(
        cls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], *, abstract: bool = False, **kwargs: Any
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)
        cls.__abstractsingleton__: bool = bool(abstract or cls.__abstractmethods__)
        if not cls.__abstractsingleton__:
            instance = cls()
            setattr(cls, "_singleton_instance_", instance)
        for constructor_attr in ("__new__", "__init__"):
            setattr(
                cls,
                constructor_attr,
                cls.__call_twice_error_wrapper(getattr(cls, constructor_attr, None) or getattr(object, constructor_attr)),
            )

    def __setattr__(cls, /, __name: str, __value: Any) -> None:
        if __name == "_singleton_instance_" and __name in cls.__dict__:
            raise TypeError("Cannot modify singleton instance")
        if __name in ("__new__", "__init__") and not isinstance(__value, cls.__call_twice_error_wrapper):
            raise TypeError("Cannot modify singleton constructors")
        return super().__setattr__(__name, __value)

    @property
    def instance(cls: Type[_T]) -> _T:
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
            if not isinstance(cls, MetaSingleton):
                raise TypeError("Called from a non-singleton class")
            if cls.__abstractsingleton__ and not cls.__abstractmethods__:
                raise TypeError(f"{cls.__name__} cannot be instantiated")
            if "_singleton_instance_" in cls.__dict__:
                raise TypeError("Cannot instanciate a singleton twice")
            func = self.__func__
            return func(__cls_or_self, *args, **kwargs)

        def __get__(self, obj: object, objtype: Optional[type] = None) -> Callable[..., Any]:
            if obj is None:
                return self
            return MethodType(self, obj)


class Singleton(metaclass=MetaSingleton, abstract=True):
    pass
