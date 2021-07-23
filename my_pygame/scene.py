# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
from enum import Enum, EnumMeta, auto, unique
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Tuple, Union

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

    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any]) -> None:
        super().__init__(name, bases, namespace)
        unique(cls)  # type: ignore


class SceneEnum(str, Enum, metaclass=MetaSceneEnum):
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
        return obj


class SceneTransition(metaclass=ABCMeta):
    @abstractmethod
    def show_new_scene(self, previous_scene: Optional[Scene], scene: Scene) -> None:
        raise NotImplementedError

    @abstractmethod
    def show_previous_scene_end_loop(self, scene: Scene, next_scene: Optional[Scene]) -> None:
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

    def push_on_top(self, alias: Optional[SceneAlias] = None) -> None:
        self.window.scenes.push_on_top(self, alias)

    def push_before(self, pivot: Union[Scene, SceneAlias], alias: Optional[SceneAlias] = None) -> None:
        self.window.scenes.push_before(self, pivot, alias)

    def push_after(self, pivot: Union[Scene, SceneAlias], alias: Optional[SceneAlias] = None) -> None:
        self.window.scenes.push_after(self, pivot, alias)

    def kill(self) -> None:
        self.window.scenes.remove(self)

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
