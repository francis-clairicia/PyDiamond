# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Scene module"""

from __future__ import annotations

__all__ = [
    "AutoLayeredMainScene",
    "AutoLayeredScene",
    "LayeredMainScene",
    "LayeredScene",
    "MainScene",
    "MetaLayeredMainScene",
    "MetaLayeredScene",
    "MetaMainScene",
    "MetaScene",
    "ReturningSceneTransition",
    "Scene",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneWindow",
    "closed_namespace",
    "set_default_theme_namespace",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import gc
from abc import ABCMeta, abstractmethod
from contextlib import ExitStack, contextmanager, suppress
from inspect import isgeneratorfunction
from operator import truth
from sys import stderr
from types import FunctionType, LambdaType, MethodType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Final,
    FrozenSet,
    Generator,
    Iterator,
    List,
    NoReturn,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    cast,
    final,
    overload,
)

from ..graphics.color import Color
from ..graphics.drawable import Drawable, LayeredGroup
from ..graphics.renderer import Renderer, SurfaceRenderer
from ..graphics.surface import Surface
from ..graphics.theme import ThemeNamespace
from ..system._mangling import mangle_private_attribute
from ..system.utils import wraps
from .display import Window, WindowCallback, WindowError, _WindowCallbackList
from .event import Event, EventManager
from .time import Time

_S = TypeVar("_S", bound="MetaScene")

_ALL_SCENES: Final[List[Type[Scene]]] = []


class MetaScene(ABCMeta):

    __abstractmethods__: FrozenSet[str]
    __namespaces: ClassVar[Dict[type, str]] = dict()

    def __new__(
        metacls,
        /,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        *,
        framerate: int = 0,
        fixed_framerate: int = 0,
        busy_loop: bool = False,
        **kwargs: Any,
    ) -> MetaScene:
        if "Scene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, Scene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Scene.__name__} class in order to use {MetaScene.__name__} metaclass"
            )

        if not all(issubclass(cls, Scene) for cls in bases):
            raise TypeError("Multiple inheritance with other class than Scene is not supported")

        for attr_name, attr_obj in namespace.items():
            if attr_name == "__new__":
                raise TypeError("__new__ method must not be overridden")
            namespace[attr_name] = metacls.__apply_theme_namespace_decorator(attr_obj)

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if not cls.__abstractmethods__:
            _ALL_SCENES.append(cast(Type[Scene], cls))
            cls.__framerate = max(int(framerate), 0)
            cls.__fixed_framerate = max(int(fixed_framerate), 0)
            cls.__busy_loop = truth(busy_loop)
        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name == "__new__":
            raise AttributeError("__new__ cannot be overriden")
        return super().__setattr__(name, value)

    def set_theme_namespace(cls, /, namespace: str) -> None:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        MetaScene.__namespaces[cls] = namespace

    def remove_theme_namespace(cls, /) -> None:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        MetaScene.__namespaces.pop(cls, None)

    def get_required_framerate(cls, /) -> int:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        return cls.__framerate  # type: ignore[no-any-return, attr-defined]

    def get_required_fixed_framerate(cls, /) -> int:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        return cls.__fixed_framerate  # type: ignore[no-any-return, attr-defined]

    def require_busy_loop(cls, /) -> bool:
        if cls.__abstractmethods__:
            raise TypeError(f"{cls.__name__} is an abstract class")
        return cls.__busy_loop  # type: ignore[no-any-return, attr-defined]

    @staticmethod
    def __theme_namespace_decorator(func: Callable[..., Any], /) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(__cls_or_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            cls: type = type(__cls_or_self) if not isinstance(__cls_or_self, type) else __cls_or_self
            output: Any
            try:
                theme_namespace: Any = MetaScene.__namespaces[cls]
            except KeyError:
                output = func(__cls_or_self, *args, **kwargs)
            else:
                with ThemeNamespace(theme_namespace):
                    output = func(__cls_or_self, *args, **kwargs)
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
        elif isinstance(obj, (FunctionType, LambdaType)):
            obj = MetaScene.__theme_namespace_decorator(obj)
        return obj


SceneTransitionCoroutine = Generator[None, Optional[float], None]


class SceneTransition(metaclass=ABCMeta):
    @abstractmethod
    def show_new_scene(
        self, /, target: Renderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class ReturningSceneTransition(SceneTransition):
    @abstractmethod
    def hide_actual_scene(
        self, /, target: Renderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class Scene(metaclass=MetaScene):
    __instances: ClassVar[Set[Type[Scene]]] = set()

    def __new__(cls, /) -> Any:
        instances: Set[Type[Scene]] = Scene.__instances
        if cls in instances:
            raise TypeError(f"Trying to instantiate two scene of same type {f'{cls.__module__}.{cls.__name__}'!r}")
        scene = super().__new__(cls)
        instances.add(cls)
        return scene

    def __init__(self, /) -> None:
        self.__manager: _SceneManager
        try:
            manager = self.__manager
        except AttributeError:
            raise TypeError(f"Trying to instantiate {self.__class__.__name__!r} scene outside a SceneWindow manager") from None

        self.__event: EventManager = EventManager()
        self.__bg_color: Color = Color(0, 0, 0)
        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__callback_after_dict: Dict[Scene, _WindowCallbackList] = getattr(
            manager.window, mangle_private_attribute(SceneWindow, "callback_after_scenes")
        )

    def __quit__(self, /) -> None:
        pass

    @final
    def __del_scene__(self, /) -> None:
        with suppress(KeyError):
            Scene.__instances.remove(type(self))

    @abstractmethod
    def awake(self, /, **kwargs: Any) -> None:
        pass

    def on_start_loop_before_transition(self, /) -> None:
        pass

    def on_start_loop(self, /) -> None:
        pass

    def fixed_update(self, /) -> None:
        pass

    def update_alpha(self, /, interpolation: float) -> None:
        pass

    def update(self, /) -> None:
        pass

    def on_quit_before_transition(self, /) -> None:
        pass

    def on_quit(self, /) -> None:
        pass

    @abstractmethod
    def render(self, /) -> None:
        raise NotImplementedError

    def draw_scene(self, /, scene: Type[Scene]) -> None:
        self.__manager.render(scene)

    @final
    def is_awaken(self, /) -> bool:
        return self.__manager.is_awaken(self)

    @final
    def looping(self, /) -> bool:
        return self.__manager.top() is self

    @final
    def start(
        self, /, scene: Type[Scene], *, transition: Optional[SceneTransition] = None, stop_self: bool = False, **awake_kwargs: Any
    ) -> NoReturn:
        self.__manager.go_to(scene, transition=transition, remove_actual=stop_self, awake_kwargs=awake_kwargs)

    @final
    def stop(self, /) -> NoReturn:
        self.__manager.go_back()

    def after(self, /, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        window_callback: WindowCallback = _SceneWindowCallback(self, milliseconds, callback, args, kwargs)
        callback_dict: Dict[Scene, _WindowCallbackList] = self.__callback_after_dict
        callback_list: _WindowCallbackList = self.__callback_after

        callback_dict[self] = callback_list
        callback_list.append(window_callback)
        return window_callback

    @overload
    def every(self, /, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        ...

    @overload
    def every(self, /, milliseconds: float, callback: Callable[..., Iterator[None]], *args: Any, **kwargs: Any) -> WindowCallback:
        ...

    def every(self, /, milliseconds: float, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> WindowCallback:
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

            window_callback = _SceneWindowCallback(self, milliseconds, callback, loop=True)

        else:
            window_callback = _SceneWindowCallback(self, milliseconds, callback, args, kwargs, loop=True)

        callback_list.append(window_callback)
        return window_callback

    @property
    def window(self, /) -> SceneWindow:
        return self.__manager.window

    @property
    def event(self, /) -> EventManager:
        return self.__event

    @property
    def background_color(self, /) -> Color:
        return self.__bg_color

    @background_color.setter
    def background_color(self, /, color: Color) -> None:
        self.__bg_color = Color(color)


class MetaMainScene(MetaScene):
    def __new__(metacls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> MetaScene:
        if "MainScene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, MainScene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {MainScene.__name__} class in order to use {MetaMainScene.__name__} metaclass"
            )

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if not cls.__abstractmethods__:
            closed_namespace(cls)
        return cls


class MainScene(Scene, metaclass=MetaMainScene):
    pass


@overload
def set_default_theme_namespace(namespace: str) -> Callable[[_S], _S]:
    ...


@overload
def set_default_theme_namespace(namespace: str, cls: _S) -> None:
    ...


def set_default_theme_namespace(namespace: str, cls: Optional[_S] = None) -> Optional[Callable[[_S], _S]]:
    def decorator(scene: _S, /) -> _S:
        scene.set_theme_namespace(namespace)
        return scene

    if cls is not None:
        decorator(cls)
        return None
    return decorator


def closed_namespace(scene: _S) -> _S:
    scene.set_theme_namespace(f"_{scene.__name__}__{id(scene):#x}")
    return scene


class MetaLayeredScene(MetaScene):
    def __new__(
        metacls,
        /,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        *,
        add_drawable_attributes: bool = False,
        **kwargs: Any,
    ) -> MetaScene:
        if "LayeredScene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, LayeredScene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {LayeredScene.__name__} class in order to use {MetaLayeredScene.__name__} metaclass"
            )

        if any(isinstance(getattr(cls, "__setattr__", None), metacls.__setattr_wrapper) for cls in bases):
            add_drawable_attributes = False

        if add_drawable_attributes:
            setattr_func: Callable[[LayeredScene, str, Any], None] = namespace.get("__setattr__", object.__setattr__)

            @wraps(setattr_func)
            def setattr_wrapper(self: LayeredScene, __name: str, __value: Any) -> None:
                try:
                    group: LayeredGroup = self.group
                except AttributeError:
                    return setattr_func(self, __name, __value)
                setattr_func(self, __name, __value)
                if isinstance(__value, Drawable):
                    group.add(__value)

            namespace["__setattr__"] = metacls.__setattr_wrapper(setattr_wrapper)

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    class __setattr_wrapper:
        def __init__(self, /, setattr_func: Callable[[Any, str, Any], None]) -> None:
            self.__func__: Callable[[object, str, Any], None] = setattr_func

        def __call__(self, /, __obj: object, __name: str, __value: Any) -> None:
            func = self.__func__
            return func(__obj, __name, __value)

        def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Callable[..., Any]:
            if obj is None:
                return self
            return MethodType(self, obj)

        @property
        def __wrapped__(self, /) -> Callable[..., Any]:
            return self.__func__


class LayeredScene(Scene, metaclass=MetaLayeredScene):
    def __init__(self, /) -> None:
        super().__init__()
        self.__group: LayeredGroup = LayeredGroup()

    def __quit__(self, /) -> None:
        super().__quit__()
        self.__group.clear()

    @final
    def render(self, /) -> None:
        group: LayeredGroup = self.__group
        self.window.draw(group)

    @property
    def group(self, /) -> LayeredGroup:
        return self.__group


class AutoLayeredScene(LayeredScene, add_drawable_attributes=True):
    pass


class MetaLayeredMainScene(MetaLayeredScene, MetaMainScene):
    pass


class LayeredMainScene(LayeredScene, MainScene, metaclass=MetaLayeredMainScene):
    pass


class AutoLayeredMainScene(LayeredMainScene, add_drawable_attributes=True):
    pass


class SceneWindow(Window):
    def __init__(self, /, title: Optional[str] = None, size: Tuple[int, int] = (0, 0), fullscreen: bool = False) -> None:
        super().__init__(title=title, size=size, fullscreen=fullscreen)
        self.__callback_after_scenes: Dict[Scene, _WindowCallbackList] = dict()
        self.__scenes: _SceneManager
        self.__accumulator: float = 0
        self.__running: bool = False

    __W = TypeVar("__W", bound="SceneWindow")

    @contextmanager
    def open(self: __W, /) -> Iterator[__W]:
        def cleanup() -> None:
            self.__callback_after_scenes.clear()
            self.__scenes.clear()
            self.__scenes.__del_manager__()
            del self.__scenes

        with super().open(), ExitStack() as stack:
            self.__scenes = _SceneManager(self)
            stack.callback(cleanup)
            yield self

    @final
    def run(self, /, default_scene: Type[Scene], **scene_kwargs: Any) -> None:
        if self.__running:
            raise WindowError("SceneWindow already running")
        self.__running = True
        self.__scenes.clear()
        self.__accumulator = 0
        gc.collect()
        try:
            self.__scenes.go_to(default_scene, awake_kwargs=scene_kwargs)
        except _SceneManager.NewScene as exc:
            exc.actual_scene.on_start_loop_before_transition()
            exc.actual_scene.on_start_loop()
        is_open = self.is_open
        process_events = self.process_events
        update_scene = self.update_scene
        render_scene = self.render_scene
        refresh_screen = self.refresh
        scene_transition = self.__scene_transition

        def handle_events() -> None:
            for _ in process_events():
                pass

        try:
            while is_open():
                try:
                    handle_events()
                    update_scene()
                    render_scene()
                    refresh_screen()
                except _SceneManager.NewScene as exc:
                    scene_transition(exc)
                except _SceneManager.SceneException as exc:
                    print(f"{type(exc).__name__}: {exc}", file=stderr)
                    continue
        finally:
            self.__running = False

    def __scene_transition(self, event: _SceneManager.NewScene) -> None:
        if event.previous_scene is None:
            raise TypeError("Previous scene must not be None")
        event.previous_scene.on_quit_before_transition()
        event.actual_scene.on_start_loop_before_transition()
        if event.transition is not None:
            with self.capture(draw_on_default_at_end=False) as previous_scene_surface:
                self.clear(event.previous_scene.background_color)
                event.previous_scene.render()
            with self.capture(draw_on_default_at_end=False) as actual_scene_surface:
                self.clear(event.actual_scene.background_color)
                event.actual_scene.render()
            with self.capture() as window_surface, self.block_all_events_context(), self.no_window_callback_processing():
                transition: SceneTransitionCoroutine
                transition = event.transition(SurfaceRenderer(window_surface), previous_scene_surface, actual_scene_surface)
                animating = True
                try:
                    next(transition)
                except StopIteration:
                    animating = False
                next_transition = transition.send
                while self.is_open() and animating:
                    self.handle_events()
                    try:
                        self._fixed_updates_call(lambda: next_transition(None))
                        self._interpolation_updates_call(next_transition)
                    except StopIteration:
                        animating = False
                    self.refresh()
        event.previous_scene.on_quit()
        if not self.__scenes.started(event.previous_scene):
            self.__scenes._destroy_awaken_scene(event.previous_scene)
        for scene in event.closing_scenes:
            scene.on_quit_before_transition()
            scene.on_quit()
            self.__scenes._destroy_awaken_scene(scene)
        self.__callback_after_scenes.pop(event.previous_scene, None)
        self.__accumulator = 0
        gc.collect()
        event.actual_scene.on_start_loop()

    def refresh(self, /) -> float:
        real_delta_time: float = super().refresh()
        self.__accumulator += min(real_delta_time / 1000, 2 * Time.fixed_delta())
        return real_delta_time

    def _fixed_updates_call(self, *funcs: Callable[[], None]) -> None:
        dt: float = Time.fixed_delta()
        while self.__accumulator >= dt:
            for func in funcs:
                func()
            self.__accumulator -= dt

    def _interpolation_updates_call(self, *funcs: Callable[[float], None]) -> None:
        alpha: float = self.__accumulator / Time.fixed_delta()
        alpha = min(max(alpha, 0), 1)
        for func in funcs:
            func(alpha)

    def update_scene(self, /) -> None:
        scene: Optional[Scene] = self.__scenes.top()
        if scene is None:
            return
        self._fixed_updates_call(scene.fixed_update)
        self._interpolation_updates_call(scene.update_alpha)
        scene.update()

    def render_scene(self, /) -> None:
        scene: Optional[Scene] = self.__scenes.top()
        if scene is None:
            return
        self.clear(scene.background_color)
        scene.render()

    def start_scene(
        self,
        /,
        scene: Type[Scene],
        *,
        transition: Optional[SceneTransition] = None,
        remove_actual: bool = False,
        **awake_kwargs: Any,
    ) -> NoReturn:
        self.__scenes.go_to(scene, transition=transition, remove_actual=remove_actual, awake_kwargs=awake_kwargs)

    def stop_actual_scene(self) -> NoReturn:
        self.__scenes.go_back()

    def _process_callbacks(self, /) -> None:
        super()._process_callbacks()
        actual_scene = self.__scenes.top()
        if actual_scene in self.__callback_after_scenes:
            self.__callback_after_scenes[actual_scene].process()

    def process_events(self, /) -> Iterator[Event]:
        actual_scene: Optional[Scene] = self.__scenes.top()
        manager: Optional[EventManager] = actual_scene.event if actual_scene is not None else None
        process_event = manager.process_event if manager is not None else None
        for event in super().process_events():
            if process_event is None or not process_event(event):
                yield event
        if manager is not None:
            manager.handle_mouse_position()

    def used_framerate(self, /) -> int:
        framerate = super().used_framerate()
        for scene in self.__scenes.from_top_to_bottom():
            f: int = scene.__class__.get_required_framerate()
            if f > 0:
                framerate = f
                break
        return framerate

    def used_fixed_framerate(self, /) -> int:
        framerate = super().used_fixed_framerate()
        for scene in self.__scenes.from_top_to_bottom():
            f: int = scene.__class__.get_required_fixed_framerate()
            if f > 0:
                framerate = f
                break
        return framerate

    def get_busy_loop(self, /) -> bool:
        actual_scene: Optional[Scene] = self.__scenes.top()
        return super().get_busy_loop() or (actual_scene is not None and actual_scene.__class__.require_busy_loop())

    def remove_window_callback(self, /, window_callback: WindowCallback) -> None:
        if not isinstance(window_callback, _SceneWindowCallback):
            return super().remove_window_callback(window_callback)
        scene = window_callback.scene
        scene_callback_after: Optional[_WindowCallbackList] = self.__callback_after_scenes.get(scene)
        if scene_callback_after is None:
            return
        with suppress(ValueError):
            scene_callback_after.remove(window_callback)
        if not scene_callback_after:
            self.__callback_after_scenes.pop(scene)


class _SceneManager:
    class SceneException(BaseException):
        pass

    class NewScene(SceneException):
        def __init__(
            self,
            previous_scene: Optional[Scene],
            actual_scene: Scene,
            transition: Optional[Callable[[Renderer, Surface, Surface], SceneTransitionCoroutine]],
            closing_scenes: List[Scene],
        ) -> None:
            super().__init__(
                f"New scene open, from {type(previous_scene).__name__ if previous_scene else None} to {type(actual_scene).__name__}"
            )
            self.previous_scene: Optional[Scene] = previous_scene
            self.actual_scene: Scene = actual_scene
            self.transition = transition
            self.closing_scenes = closing_scenes

    class SameScene(SceneException):
        def __init__(self, scene: Scene) -> None:
            super().__init__(f"Trying to go to the same running scene: {type(scene).__name__!r}")
            self.scene: Scene = scene

    __scene_manager_attribute: Final[str] = mangle_private_attribute(Scene, "manager")

    def __init__(self, /, window: SceneWindow) -> None:
        def new_scene(cls: Type[Scene]) -> Scene:
            scene: Scene = cls.__new__(cls)
            setattr(scene, self.__scene_manager_attribute, self)
            scene.__init__()  # type: ignore[misc]
            return scene

        self.__window: SceneWindow = window
        self.__all: Dict[Type[Scene], Scene] = {cls: new_scene(cls) for cls in _ALL_SCENES}
        self.__stack: List[Scene] = []
        self.__returning_transitions: Dict[Type[Scene], ReturningSceneTransition] = {}
        self.__awaken: Set[Scene] = set()

    def __del__(self, /) -> None:
        for scene in self.__all.values():
            scene.__del_scene__()
        self.__all.clear()

    def __del_manager__(self, /) -> None:
        for scene in self.__all.values():
            delattr(scene, self.__scene_manager_attribute)

    def _destroy_awaken_scene(self, /, scene: Scene) -> None:
        try:
            self.__awaken.remove(scene)
        except KeyError:
            return
        all_attributes: List[str] = list(scene.__dict__)
        scene.__quit__()
        for attr in all_attributes:
            if attr != self.__scene_manager_attribute:
                delattr(scene, attr)
        scene.__init__()  # type: ignore[misc]

    def __iter__(self, /) -> Iterator[Scene]:
        return self.from_top_to_bottom()

    def from_top_to_bottom(self, /) -> Iterator[Scene]:
        return iter(self.__stack)

    def from_bottom_to_top(self, /) -> Iterator[Scene]:
        return reversed(self.__stack)

    def top(self, /) -> Optional[Scene]:
        return self.__stack[0] if self.__stack else None

    def started(self, /, scene: Scene) -> bool:
        return scene in self.__stack

    def is_awaken(self, /, scene: Scene) -> bool:
        return scene in self.__awaken

    def clear(self, /) -> None:
        while self.__stack:
            scene = self.__stack.pop(0)
            scene.on_quit_before_transition()
            scene.on_quit()
            self._destroy_awaken_scene(scene)
        gc.collect()

    def render(self, /, scene: Type[Scene]) -> None:
        if scene.__abstractmethods__:
            raise TypeError(f"{scene.__name__} is an abstract class")
        obj = self.__all[scene]
        if not obj.is_awaken():
            raise ValueError("Trying to draw non-awaken scene")
        if obj.looping():
            raise ValueError("Trying to draw actual looping scene")
        self.window.clear(obj.background_color)
        obj.render()

    def go_to(
        self,
        /,
        scene: Type[Scene],
        *,
        transition: Optional[SceneTransition] = None,
        remove_actual: bool = False,
        awake_kwargs: Dict[str, Any] = {},
    ) -> NoReturn:
        if scene.__abstractmethods__:
            raise TypeError(f"{scene.__name__} is an abstract class")
        next_scene = self.__all[scene]
        stack = self.__stack
        actual_scene = stack[0] if stack else None
        if actual_scene is next_scene:
            raise _SceneManager.SameScene(actual_scene)
        scene_transition: Optional[Callable[[Renderer, Surface, Surface], SceneTransitionCoroutine]] = None
        closing_scenes: List[Scene] = []
        if actual_scene is None or next_scene not in stack:
            stack.insert(0, next_scene)
            next_scene.awake(**awake_kwargs)
            self.__awaken.add(next_scene)
            if actual_scene is not None:
                if isinstance(transition, ReturningSceneTransition):
                    self.__returning_transitions[actual_scene.__class__] = transition
                if transition is not None:
                    scene_transition = transition.show_new_scene
                if remove_actual:
                    stack.remove(actual_scene)
        else:
            returning_transition = self.__returning_transitions.pop(scene, None)
            while stack[0] is not next_scene:
                closed_scene = stack.pop(0)
                if closed_scene is not actual_scene:
                    closing_scenes.append(closed_scene)
                self.__returning_transitions.pop(closed_scene.__class__, None)
            if returning_transition is not None:
                scene_transition = returning_transition.hide_actual_scene
            elif transition is not None:
                scene_transition = (
                    transition.hide_actual_scene
                    if isinstance(transition, ReturningSceneTransition)
                    else transition.show_new_scene
                )
        raise _SceneManager.NewScene(actual_scene, next_scene, scene_transition, closing_scenes)

    def go_back(self) -> NoReturn:
        if len(self.__stack) <= 1:
            self.window.close()
        self.go_to(self.__stack[1].__class__)

    @property
    def window(self, /) -> SceneWindow:
        return self.__window


class _SceneWindowCallback(WindowCallback):
    def __init__(
        self,
        /,
        master: Scene,
        wait_time: float,
        callback: Callable[..., None],
        args: Tuple[Any, ...] = (),
        kwargs: Dict[str, Any] = {},
        loop: bool = False,
    ) -> None:
        self.__scene: Scene = master
        super().__init__(master.window, wait_time, callback, args, kwargs, loop)

    def __call__(self, /) -> None:
        scene = self.__scene
        if not scene.looping():
            return
        return super().__call__()

    @property
    def scene(self, /) -> Scene:
        return self.__scene
