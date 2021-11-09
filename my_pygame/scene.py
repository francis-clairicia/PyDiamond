# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
from inspect import isgeneratorfunction
from operator import truth
from typing import TYPE_CHECKING, Any, Callable, Dict, FrozenSet, Iterator, List, Optional, Tuple, Type, TypeVar, Union, overload

from pygame.color import Color

from .clock import Clock
from .event import EventManager
from .theme import ThemeNamespace
from .utils import MethodWrapper

if TYPE_CHECKING:
    from .window import Window

__all__ = [
    "MetaScene",
    "Scene",
    "SceneTransition",
    "MetaMainScene",
    "MainScene",
    "set_default_theme_namespace",
    "closed_namespace",
]

_T = TypeVar("_T")
_S = TypeVar("_S", bound="MetaScene")


class MetaScene(ABCMeta):

    __abstractmethods__: FrozenSet[str]
    __namespaces: Dict[type, str] = dict()
    __instances: Dict[Type[Any], Any] = dict()

    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> MetaScene:
        for attr_name, attr_obj in namespace.items():
            namespace[attr_name] = metacls.__apply_theme_namespace_decorator(attr_obj)

        return super().__new__(metacls, name, bases, namespace, **extra)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        instance: object
        dict_instances: Dict[Type[Any], Any] = cls.__instances
        try:
            instance = dict_instances[cls]
            getattr(instance, "__init__")(*args, **kwargs)
        except KeyError:
            dict_instances[cls] = instance = super().__call__(*args, **kwargs)
        return instance

    def set_theme_namespace(cls, namespace: str) -> None:
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
            cls: type = type(self) if not isinstance(self, type) else self
            output: Any
            try:
                theme_namespace: Any = MetaScene.__namespaces[cls]
            except KeyError:
                output = func(self, *args, **kwargs)
            else:
                with ThemeNamespace(theme_namespace):
                    output = func(self, *args, **kwargs)
            return output

        return MethodWrapper(wrapper)

    @staticmethod
    def __apply_theme_namespace_decorator(obj: Any) -> Any:
        if isinstance(obj, property):
            if callable(obj.fget):
                obj = obj.getter(MetaScene.__theme_namespace_decorator(obj.fget))
            if callable(obj.fset):
                obj = obj.setter(MetaScene.__theme_namespace_decorator(obj.fset))
            if callable(obj.fdel):
                obj = obj.deleter(MetaScene.__theme_namespace_decorator(obj.fdel))
        elif isinstance(obj, classmethod):
            obj = classmethod(MetaScene.__theme_namespace_decorator(obj.__func__))
        elif callable(obj):
            obj = MetaScene.__theme_namespace_decorator(obj)
        return obj


class SceneTransition(metaclass=ABCMeta):
    @abstractmethod
    def show_new_scene(self, actual_scene: Scene, next_scene: Scene) -> None:
        raise NotImplementedError

    @abstractmethod
    def hide_actual_scene(self, scene_to_hide: Scene, scene_to_show: Scene) -> None:
        raise NotImplementedError


class Scene(EventManager, metaclass=MetaScene):
    def __init__(self, master: Union[Window, Scene], framerate: int = 0, busy_loop: bool = False) -> None:
        super().__init__()
        self.__master: Optional[Scene]
        self.__window: Window
        if isinstance(master, Scene):
            self.__master = master
            self.__window = master.window
        else:
            self.__master = None
            self.__window = master
        self.__framerate: int = max(int(framerate), 0)
        self.__busy_loop: bool = truth(busy_loop)
        self.__bg_color: Color = Color(0, 0, 0)
        self.__transition: Optional[SceneTransition] = None
        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__callback_after_dict: Dict[Scene, _WindowCallbackList] = getattr(self.__window, "_Window__callback_after_scenes")

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
        return self.__window.get_actual_scene() is self

    def started(self) -> bool:
        return self in self.__window

    def start(self) -> None:
        self.__window.start_scene(self)

    def stop(self) -> None:
        self.__window.stop_scene(self)

    def after(self, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        window_callback: WindowCallback = WindowCallback(self, milliseconds, callback, args, kwargs)
        callback_dict: Dict[Scene, _WindowCallbackList] = self.__callback_after_dict
        callback_list: _WindowCallbackList = self.__callback_after

        callback_dict[self] = callback_list
        callback_list.append(window_callback)
        return window_callback

    @overload
    def every(self, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        ...

    @overload
    def every(self, milliseconds: float, callback: Callable[..., Iterator[None]], *args: Any, **kwargs: Any) -> WindowCallback:
        ...

    def every(self, milliseconds: float, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> WindowCallback:
        window_callback: WindowCallback
        callback_dict: Dict[Scene, _WindowCallbackList] = self.__callback_after_dict
        callback_list: _WindowCallbackList = self.__callback_after
        callback_dict[self] = callback_list

        if isgeneratorfunction(callback):
            generator: Iterator[None] = callback(*args, **kwargs)

            def callback() -> None:
                try:
                    next(generator)
                except ValueError:
                    pass
                except StopIteration:
                    window_callback.kill()

            window_callback = WindowCallback(self, milliseconds, callback, loop=True)

        else:
            window_callback = WindowCallback(self, milliseconds, callback, args, kwargs, loop=True)

        callback_list.append(window_callback)
        return window_callback

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

    @transition.setter
    def transition(self, transition: Optional[SceneTransition]) -> None:
        if isinstance(transition, SceneTransition):
            self.__transition = transition
        else:
            self.__transition = None


class MetaMainScene(MetaScene):
    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: dict[str, Any]) -> None:
        super().__init__(name, bases, namespace)
        if not cls.__abstractmethods__:
            closed_namespace(cls)


class MainScene(Scene, metaclass=MetaMainScene):
    def __init__(self, master: Window, framerate: int = 0, busy_loop: bool = False) -> None:
        super().__init__(master, framerate=framerate, busy_loop=busy_loop)

    @property
    def master(self) -> None:
        return None


def set_default_theme_namespace(namespace: str) -> Callable[[_S], _S]:
    def decorator(scene: _S) -> _S:
        scene.set_theme_namespace(namespace)
        return scene

    return decorator


def closed_namespace(scene: _S) -> _S:
    scene.set_theme_namespace(f"_{scene.__name__}__{id(scene):#x}")
    return scene


class WindowCallback:
    def __init__(
        self,
        master: Union[Window, Scene],
        wait_time: float,
        callback: Callable[..., None],
        args: Tuple[Any, ...] = (),
        kwargs: Dict[str, Any] = {},
        loop: bool = False,
    ) -> None:
        self.__master: Window
        self.__scene: Optional[Scene]
        if isinstance(master, Scene):
            self.__master = master.window
            self.__scene = master
        else:
            self.__master = master
            self.__scene = None

        self.__wait_time: float = wait_time
        self.__callback: Callable[..., None] = callback
        self.__args: Tuple[Any, ...] = args
        self.__kwargs: Dict[str, Any] = kwargs
        self.__clock = Clock(start=True)
        self.__loop: bool = bool(loop)

    def __call__(self) -> None:
        scene: Optional[Scene] = self.__scene
        if scene is not None and not scene.looping():
            return
        loop: bool = self.__loop
        if self.__clock.elapsed_time(self.__wait_time, restart=loop):
            self.__callback(*self.__args, **self.__kwargs)
            if not loop:
                self.kill()

    def kill(self) -> None:
        self.__master.remove_window_callback(self)

    @property
    def scene(self) -> Optional[Scene]:
        return self.__scene


class _WindowCallbackList(List[WindowCallback]):
    def process(self) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()
