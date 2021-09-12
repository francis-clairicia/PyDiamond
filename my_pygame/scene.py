# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
from operator import truth
from typing import Any, Callable, Dict, FrozenSet, List, Optional, TYPE_CHECKING, Tuple, TypeVar, Union, final
import pygame

from pygame.color import Color
from pygame.event import Event

from .theme import ThemeNamespace
from .mouse import Mouse
from .keyboard import Keyboard

if TYPE_CHECKING:
    from .window import _EventCallback, _EventType, _MousePositionCallback, _MousePosition, Window, WindowCallback

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


class MetaScene(ABCMeta):

    __abstractmethods__: FrozenSet[str]
    __namespaces: Dict[type, str] = dict()

    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **extra: Any) -> MetaScene:
        for attr_name, attr_obj in namespace.items():
            namespace[attr_name] = metacls.__apply_theme_namespace_decorator(attr_obj)

        return super().__new__(metacls, name, bases, namespace, **extra)

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
        if getattr(func, "__isabstractmethod__", False):
            return func

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

        return wrapper

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
        self.__busy_loop: bool = truth(busy_loop)
        self.__bg_color: Color = Color(0, 0, 0)
        self.__transition: Optional[SceneTransition] = None
        self.__event_handler_dict: Dict[int, List[_EventCallback]] = dict()
        self.__key_pressed_handler_dict: Dict[Keyboard.Key, List[_EventCallback]] = dict()
        self.__key_released_handler_dict: Dict[Keyboard.Key, List[_EventCallback]] = dict()
        self.__mouse_button_pressed_handler_dict: Dict[Mouse.Button, List[_EventCallback]] = dict()
        self.__mouse_button_released_handler_dict: Dict[Mouse.Button, List[_EventCallback]] = dict()
        self.__mouse_pos_handler_list: List[_MousePositionCallback] = list()

        self.bind_event(pygame.KEYDOWN, self.__handle_key_event)
        self.bind_event(pygame.KEYUP, self.__handle_key_event)
        self.bind_event(pygame.MOUSEBUTTONDOWN, self.__handle_mouse_event)
        self.bind_event(pygame.MOUSEBUTTONUP, self.__handle_mouse_event)

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

    @staticmethod
    def __bind(handler_dict: Dict[_T, List[_EventCallback]], key: _T, callback: _EventCallback) -> None:
        try:
            event_list: List[_EventCallback] = handler_dict[key]
        except KeyError:
            event_list = handler_dict[key] = []
        if callback not in event_list:
            event_list.append(callback)

    @staticmethod
    def __unbind(handler_dict: Dict[_T, List[_EventCallback]], key: _T, callback: _EventCallback) -> None:
        try:
            handler_dict[key].remove(callback)
        except (KeyError, ValueError):
            pass

    def bind_event(self, event_type: _EventType, callback: _EventCallback) -> None:
        Scene.__bind(self.__event_handler_dict, int(event_type), callback)

    def unbind_event(self, event_type: _EventType, callback_to_remove: _EventCallback) -> None:
        Scene.__unbind(self.__event_handler_dict, int(event_type), callback_to_remove)

    def bind_key(self, key: Union[int, Keyboard.Key], callback: _EventCallback) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, key: Union[int, Keyboard.Key], callback: _EventCallback) -> None:
        Scene.__bind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback)

    def bind_key_release(self, key: Union[int, Keyboard.Key], callback: _EventCallback) -> None:
        Scene.__bind(self.__key_released_handler_dict, Keyboard.Key(key), callback)

    def unbind_key(self, key: Union[int, Keyboard.Key], callback_to_remove: _EventCallback) -> None:
        self.unbind_key_press(key, callback_to_remove)
        self.unbind_key_release(key, callback_to_remove)

    def unbind_key_press(self, key: Union[int, Keyboard.Key], callback_to_remove: _EventCallback) -> None:
        Scene.__unbind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback_to_remove)

    def unbind_key_release(self, key: Union[int, Keyboard.Key], callback_to_remove: _EventCallback) -> None:
        Scene.__unbind(self.__key_released_handler_dict, Keyboard.Key(key), callback_to_remove)

    def bind_mouse_button(self, button: Union[int, Mouse.Button], callback: _EventCallback) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(self, button: Union[int, Mouse.Button], callback: _EventCallback) -> None:
        Scene.__bind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback)

    def bind_mouse_button_release(self, button: Union[int, Mouse.Button], callback: _EventCallback) -> None:
        Scene.__bind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback)

    def unbind_mouse_button(self, button: Union[int, Mouse.Button], callback_to_remove: _EventCallback) -> None:
        self.unbind_mouse_button_press(button, callback_to_remove)
        self.unbind_mouse_button_release(button, callback_to_remove)

    def unbind_mouse_button_press(self, button: Union[int, Mouse.Button], callback_to_remove: _EventCallback) -> None:
        Scene.__unbind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback_to_remove)

    def unbind_mouse_button_release(self, button: Union[int, Mouse.Button], callback_to_remove: _EventCallback) -> None:
        Scene.__unbind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback_to_remove)

    def bind_mouse_position(self, callback: _MousePositionCallback) -> None:
        mouse_pos_handler_list: List[_MousePositionCallback] = self.__mouse_pos_handler_list
        if callback not in mouse_pos_handler_list:
            mouse_pos_handler_list.append(callback)

    def unbind_mouse_position(self, callback_to_remove: _MousePositionCallback) -> None:
        mouse_pos_handler_list: List[_MousePositionCallback] = self.__mouse_pos_handler_list
        try:
            mouse_pos_handler_list.remove(callback_to_remove)
        except ValueError:
            pass

    def after(self, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        return self.__window.after(milliseconds, callback, *args, scene=self, **kwargs)

    @final
    def _handle_event(self, event: Event) -> None:
        event_dict: Dict[int, List[_EventCallback]] = self.__event_handler_dict
        for callback in event_dict.get(event.type, []):
            callback(event)

    def __handle_key_event(self, event: Event) -> None:
        key_handler_dict: Optional[Dict[Keyboard.Key, List[_EventCallback]]] = None
        if event.type == pygame.KEYDOWN:
            key_handler_dict = self.__key_pressed_handler_dict
        elif event.type == pygame.KEYUP:
            key_handler_dict = self.__key_released_handler_dict
        if key_handler_dict:
            for callback in key_handler_dict.get(event.key, []):
                callback(event)

    def __handle_mouse_event(self, event: Event) -> None:
        mouse_handler_dict: Optional[Dict[Mouse.Button, List[_EventCallback]]] = None
        if event.type == pygame.MOUSEBUTTONDOWN:
            mouse_handler_dict = self.__mouse_button_pressed_handler_dict
        elif event.type == pygame.MOUSEBUTTONUP:
            mouse_handler_dict = self.__mouse_button_released_handler_dict
        if mouse_handler_dict:
            for callback in mouse_handler_dict.get(event.button, []):
                callback(event)

    @final
    def _handle_mouse_pos(self, mouse_pos: _MousePosition) -> None:
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)

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


_S = TypeVar("_S", bound=MetaScene)


def set_default_theme_namespace(namespace: str) -> Callable[[_S], _S]:
    def decorator(scene: _S) -> _S:
        scene.set_theme_namespace(namespace)
        return scene

    return decorator


def closed_namespace(scene: _S) -> _S:
    scene.set_theme_namespace(f"_{scene.__name__}__{id(scene):#x}")
    return scene
