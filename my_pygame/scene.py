# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
from typing import Any, Callable, Dict, TYPE_CHECKING, Tuple
from .theme import ThemeNamespace

if TYPE_CHECKING:
    from .window import Window


class MetaScene(ABCMeta):

    __abstractmethods__: frozenset[str]
    __namespaces: Dict[type, Any] = dict()

    def __new__(metacls, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any], **extra: Any) -> MetaScene:
        for attr_name, attr_obj in attrs.items():
            attrs[attr_name] = metacls.__apply_theme_namespace_decorator(attr_obj)

        return super().__new__(metacls, name, bases, attrs, **extra)

    def __setattr__(cls, name: str, value: Any) -> None:
        return super().__setattr__(name, cls.__apply_theme_namespace_decorator(value))

    def set_theme_namespace(cls, namespace: Any) -> None:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        MetaScene.__namespaces[cls] = namespace

    def remove_theme_namespace(cls) -> None:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        MetaScene.__namespaces.pop(cls, None)

    @staticmethod
    def __theme_namespace_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            cls: type = type(self)
            output: Any
            if cls in MetaScene.__namespaces and ThemeNamespace.get() != MetaScene.__namespaces[cls]:
                with ThemeNamespace(MetaScene.__namespaces[cls]):
                    output = func(self, *args, **kwargs)
            else:
                output = func(self, *args, **kwargs)
            return output

        return wrapper

    @staticmethod
    def __apply_theme_namespace_decorator(obj: Any) -> Any:
        if callable(obj):
            obj = MetaScene.__theme_namespace_decorator(obj)
        elif isinstance(obj, property):
            if callable(obj.fget):
                obj = obj.getter(MetaScene.__theme_namespace_decorator(obj.fget))
            if callable(obj.fset):
                obj = obj.setter(MetaScene.__theme_namespace_decorator(obj.fset))
            if callable(obj.fdel):
                obj = obj.deleter(MetaScene.__theme_namespace_decorator(obj.fdel))
        return obj


class Scene(metaclass=MetaScene):
    def __init__(self, window: Window, framerate: int = 0, busy_loop: bool = False) -> None:
        self.__w: Window = window
        self.__f: int = max(framerate, 0)
        self.__b: bool = busy_loop

    def update(self) -> None:
        pass

    @abstractmethod
    def draw(self) -> None:
        raise NotImplementedError

    def get_required_framerate(self) -> int:
        return self.__f

    def require_busy_loop(self) -> bool:
        return self.__b

    @property
    def window(self) -> Window:
        return self.__w
