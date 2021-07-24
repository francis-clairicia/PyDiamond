# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
from enum import Enum, EnumMeta, auto, unique
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Tuple, Union, overload

from pygame.color import Color

from .theme import ThemeNamespace

if TYPE_CHECKING:
    from .window import Window


class MetaSceneEnum(EnumMeta):
    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]) -> MetaSceneEnum:
        annotations: Dict[str, Union[type, str]] = namespace.get("__annotations__", dict())
        for enum_name, enum_type in annotations.items():
            if not isinstance(enum_type, (type, str)):
                raise TypeError(f"Enum type annotation must be str, not {repr(enum_type)}")
            if isinstance(enum_type, str) and enum_type != "str":
                raise TypeError(f"Enum type annotation must be str, not {repr(enum_type)}")
            if isinstance(enum_type, type) and enum_type is not str:
                raise TypeError(f"Enum type annotation must be str, not {repr(enum_type.__name__)}")
            if enum_name not in namespace:
                namespace[enum_name] = auto()

        return super().__new__(metacls, name, bases, namespace)


class SceneEnum(str, Enum, metaclass=MetaSceneEnum):
    def __init_subclass__(cls) -> None:
        unique(cls)

    def _generate_next_value_(name: str, start: int, count: int, last_values: List[str]) -> str:  # type: ignore[override]
        return name.upper()


SceneAlias = Union[str, SceneEnum]


class MetaScene(ABCMeta):

    __abstractmethods__: frozenset[str]
    __namespaces: Dict[type, Any] = dict()

    def __new__(metacls, name: str, bases: Tuple[type, ...], attrs: Dict[str, Any], **extra: Any) -> MetaScene:
        for attr_name, attr_obj in attrs.items():
            attrs[attr_name] = metacls.__apply_theme_namespace_decorator(attr_obj)

        return super().__new__(metacls, name, bases, attrs, **extra)

    def set_theme_namespace(cls, namespace: Any) -> None:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        if namespace is not None:
            MetaScene.__namespaces[cls] = namespace
        else:
            MetaScene.__namespaces.pop(cls, None)

    def remove_theme_namespace(cls) -> None:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        MetaScene.__namespaces.pop(cls, None)

    @staticmethod
    def __theme_namespace_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
            cls: type = type(self) if not isinstance(self, type) else self
            output: Any
            if cls in MetaScene.__namespaces and ThemeNamespace.get() is not MetaScene.__namespaces[cls]:
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
        elif isinstance(obj, classmethod):
            obj = classmethod(MetaScene.__theme_namespace_decorator(obj.__func__))
        return obj


class SceneTransition(metaclass=ABCMeta):
    @abstractmethod
    def show_new_scene(self, actual_scene: Scene, next_scene: Scene) -> None:
        raise NotImplementedError

    @abstractmethod
    def hide_actual_scene(self, scene_to_hide: Scene, scene_to_show: Scene) -> None:
        raise NotImplementedError


class Scene(metaclass=MetaScene):
    def __init__(self, master: Union[Window, Scene], framerate: int = 0, busy_loop: bool = False) -> None:
        self.__master: Optional[Scene]
        self.__window: Window
        if isinstance(master, Scene):
            self.__master = master
            self.__window = master.window
        else:
            self.__master = None
            self.__window = master
        self.__framerate: int = max(framerate, 0)
        self.__busy_loop: bool = busy_loop
        self.__bg_color: Color = Color(0, 0, 0)
        self.__transition: Optional[SceneTransition] = None

    def on_start_loop(self) -> None:
        pass

    def update(self) -> None:
        pass

    def on_quit(self) -> None:
        pass

    @abstractmethod
    def draw(self) -> None:
        raise NotImplementedError

    def looping(self) -> bool:
        return self.window.get_actual_scene() is self

    def started(self) -> bool:
        return self in self.window

    @overload
    def start(self) -> None:
        ...

    @overload
    def start(self, new_alias: SceneAlias) -> None:
        ...

    def start(self, new_alias: Optional[SceneAlias] = None) -> None:
        if new_alias is not None:
            self.window.start_scene(self, new_alias)
        else:
            self.window.start_scene(self)

    def stop(self) -> None:
        self.window.stop_scene(self)

    def get_required_framerate(self) -> int:
        return self.__framerate

    def require_busy_loop(self) -> bool:
        return self.__busy_loop

    @property
    def master(self) -> Optional[Scene]:
        return self.__master

    @property
    def window(self) -> Window:
        return self.__window

    @property
    def background_color(self) -> Color:
        return self.__bg_color

    @background_color.setter
    def background_color(self, color: Color) -> None:
        self.__bg_color = Color(color)

    @property
    def transition(self) -> Optional[SceneTransition]:
        return self.__transition
