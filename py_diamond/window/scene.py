# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Scene module"""

from __future__ import annotations

__all__ = [
    "AbstractAutoLayeredScene",
    "AbstractLayeredScene",
    "LayeredMainScene",
    "LayeredMainSceneMeta",
    "LayeredScene",
    "LayeredSceneMeta",
    "MainScene",
    "MainSceneMeta",
    "ReturningSceneTransition",
    "Scene",
    "SceneMeta",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneWindow",
    "closed_namespace",
    "set_default_theme_namespace",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
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
    Final,
    Generator,
    Iterator,
    NoReturn,
    ParamSpec,
    Sequence,
    TypeAlias,
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
from ..system._mangling import getattr_pv, mangle_private_attribute
from ..system.utils import concreteclassmethod, wraps
from .display import Window, WindowCallback, WindowError, _WindowCallbackList
from .event import Event, EventManager
from .time import Time

_S = TypeVar("_S", bound="SceneMeta")
_P = ParamSpec("_P")

_ALL_SCENES: Final[list[type[Scene]]] = []


class SceneMeta(ABCMeta):
    __namespaces: ClassVar[dict[type, str]] = dict()

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        framerate: int = 0,
        fixed_framerate: int = 0,
        busy_loop: bool = False,
        **kwargs: Any,
    ) -> SceneMeta:
        if "Scene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, Scene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Scene.__name__} class in order to use {SceneMeta.__name__} metaclass"
            )

        if not all(issubclass(cls, Scene) for cls in bases):
            raise TypeError("Multiple inheritance with other class than Scene is not supported")

        for attr_name, attr_obj in namespace.items():
            if attr_name == "__new__":
                raise TypeError("__new__ method must not be overridden")
            namespace[attr_name] = metacls.__apply_theme_namespace_decorator(attr_obj)

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if not cls.__abstractmethods__:
            _ALL_SCENES.append(cast(type[Scene], cls))
            cls.__framerate = max(int(framerate), 0)
            cls.__fixed_framerate = max(int(fixed_framerate), 0)
            cls.__busy_loop = truth(busy_loop)
        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError(f"{name} cannot be overriden")
        return super().__setattr__(name, value)

    @concreteclassmethod
    def get_theme_namespace(cls) -> str | None:
        return SceneMeta.__namespaces.get(cls)

    @concreteclassmethod
    def set_theme_namespace(cls, namespace: str) -> None:
        SceneMeta.__namespaces[cls] = str(namespace)

    @concreteclassmethod
    def remove_theme_namespace(cls) -> None:
        SceneMeta.__namespaces.pop(cls, None)

    @concreteclassmethod
    def get_required_framerate(cls) -> int:
        return cls.__framerate  # type: ignore[no-any-return, attr-defined]

    @concreteclassmethod
    def get_required_fixed_framerate(cls) -> int:
        return cls.__fixed_framerate  # type: ignore[no-any-return, attr-defined]

    @concreteclassmethod
    def require_busy_loop(cls) -> bool:
        return cls.__busy_loop  # type: ignore[no-any-return, attr-defined]

    @staticmethod
    def __theme_namespace_decorator(func: Callable[..., Any], /) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(__cls_or_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            cls: type = type(__cls_or_self) if not isinstance(__cls_or_self, type) else __cls_or_self
            theme_namespace: str | None = SceneMeta.__namespaces.get(cls)
            if theme_namespace is None:
                return func(__cls_or_self, *args, **kwargs)
            with ThemeNamespace(theme_namespace):
                return func(__cls_or_self, *args, **kwargs)

        return wrapper

    @staticmethod
    def __apply_theme_namespace_decorator(obj: Any) -> Any:
        if isinstance(obj, property):
            if callable(obj.fget):
                obj = obj.getter(SceneMeta.__theme_namespace_decorator(obj.fget))
            if callable(obj.fset):
                obj = obj.setter(SceneMeta.__theme_namespace_decorator(obj.fset))
            if callable(obj.fdel):
                obj = obj.deleter(SceneMeta.__theme_namespace_decorator(obj.fdel))
        elif isinstance(obj, classmethod):
            obj = classmethod(SceneMeta.__theme_namespace_decorator(obj.__func__))
        elif isinstance(obj, (FunctionType, LambdaType)):
            obj = SceneMeta.__theme_namespace_decorator(obj)
        return obj


SceneTransitionCoroutine: TypeAlias = Generator[None, float | None, None]


class SceneTransition(metaclass=ABCMeta):
    @abstractmethod
    def show_new_scene(
        self, target: Renderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class ReturningSceneTransition(SceneTransition):
    @abstractmethod
    def hide_actual_scene(
        self, target: Renderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class Scene(metaclass=SceneMeta):
    __instances: ClassVar[set[type[Scene]]] = set()

    __slots__ = (
        "__manager",
        "__event",
        "__bg_color",
        "__callback_after",
        "__callback_after_dict",
        "__stack",
        "__dict__",
    )

    def __new__(cls) -> Any:
        instances: set[type[Scene]] = Scene.__instances
        if cls in instances:
            raise TypeError(f"Trying to instantiate two scene of same type {f'{cls.__module__}.{cls.__name__}'!r}")
        scene = super().__new__(cls)
        instances.add(cls)
        return scene

    def __init__(self) -> None:
        self.__manager: _SceneManager
        try:
            manager = self.__manager
        except AttributeError:
            raise TypeError(f"Trying to instantiate {self.__class__.__name__!r} scene outside a SceneWindow manager") from None

        self.__event: EventManager = EventManager()
        self.__bg_color: Color = Color(0, 0, 0)
        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__callback_after_dict: dict[Scene, _WindowCallbackList] = getattr_pv(
            manager.window, "callback_after_scenes", owner=SceneWindow
        )
        self.__stack: ExitStack = ExitStack()

    def __theme_init__(self) -> None:
        pass

    @final
    def __del_scene__(self) -> None:
        with suppress(KeyError):
            Scene.__instances.remove(type(self))

    @abstractmethod
    def awake(self, **kwargs: Any) -> None:
        pass

    def on_start_loop_before_transition(self) -> None:
        pass

    def on_start_loop(self) -> None:
        pass

    def fixed_update(self) -> None:
        pass

    def update_alpha(self, interpolation: float) -> None:
        pass

    def update(self) -> None:
        pass

    def on_quit_before_transition(self) -> None:
        pass

    def on_quit(self) -> None:
        pass

    def destroy(self) -> None:
        pass

    @abstractmethod
    def render(self) -> None:
        raise NotImplementedError

    def draw_scene(self, scene: type[Scene]) -> None:
        self.__manager.render(scene)

    def handle_event(self, event: Event) -> bool:
        return False

    @final
    def is_awaken(self) -> bool:
        return self.__manager.is_awaken(self)

    @final
    def looping(self) -> bool:
        return self.__manager.top() is self

    @final
    def start(
        self, scene: type[Scene], *, transition: SceneTransition | None = None, stop_self: bool = False, **awake_kwargs: Any
    ) -> NoReturn:
        self.__manager.go_to(scene, transition=transition, remove_actual=stop_self, awake_kwargs=awake_kwargs)

    @final
    def stop(self) -> NoReturn:
        self.__manager.go_back()

    def after(
        self, __milliseconds: float, __callback: Callable[_P, None], /, *args: _P.args, **kwargs: _P.kwargs
    ) -> WindowCallback:
        window_callback: WindowCallback = _SceneWindowCallback(self, __milliseconds, __callback, args, kwargs)  # type: ignore[arg-type]
        callback_dict: dict[Scene, _WindowCallbackList] = self.__callback_after_dict
        callback_list: _WindowCallbackList = self.__callback_after

        callback_dict[self] = callback_list
        callback_list.append(window_callback)
        return window_callback

    @overload
    def every(
        self, __milliseconds: float, __callback: Callable[_P, None], /, *args: _P.args, **kwargs: _P.kwargs
    ) -> WindowCallback:
        ...

    @overload
    def every(
        self, __milliseconds: float, __callback: Callable[_P, Iterator[None]], /, *args: _P.args, **kwargs: _P.kwargs
    ) -> WindowCallback:
        ...

    def every(self, __milliseconds: float, __callback: Callable[..., Any], /, *args: Any, **kwargs: Any) -> WindowCallback:
        window_callback: WindowCallback
        callback_dict: dict[Scene, _WindowCallbackList] = self.__callback_after_dict
        callback_list: _WindowCallbackList = self.__callback_after
        callback_dict[self] = callback_list

        if isgeneratorfunction(__callback):
            generator: Iterator[None] = __callback(*args, **kwargs)

            @wraps(__callback)
            def wrapper() -> None:
                try:
                    next(generator)
                except ValueError:
                    pass
                except StopIteration:
                    window_callback.kill()

            window_callback = _SceneWindowCallback(self, __milliseconds, wrapper, loop=True)

        else:
            window_callback = _SceneWindowCallback(self, __milliseconds, __callback, args, kwargs, loop=True)

        callback_list.append(window_callback)
        return window_callback

    @property
    def window(self) -> SceneWindow:
        return self.__manager.window

    @property
    def event(self) -> EventManager:
        return self.__event

    @property
    def exit_stack(self) -> ExitStack:
        return self.__stack

    @property
    def background_color(self) -> Color:
        return self.__bg_color

    @background_color.setter
    def background_color(self, color: Color) -> None:
        self.__bg_color = Color(color)


class MainSceneMeta(SceneMeta):
    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> SceneMeta:
        if "MainScene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, MainScene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {MainScene.__name__} class in order to use {MainSceneMeta.__name__} metaclass"
            )

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if not cls.__abstractmethods__:
            closed_namespace(cls)
        return cls


class MainScene(Scene, metaclass=MainSceneMeta):
    __slots__ = ()


@overload
def set_default_theme_namespace(namespace: str) -> Callable[[_S], _S]:
    ...


@overload
def set_default_theme_namespace(namespace: str, cls: _S) -> None:
    ...


def set_default_theme_namespace(namespace: str, cls: _S | None = None) -> Callable[[_S], _S] | None:
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


class LayeredSceneMeta(SceneMeta):
    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        add_drawable_attributes: bool = False,
        **kwargs: Any,
    ) -> SceneMeta:
        if "AbstractLayeredScene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, AbstractLayeredScene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {AbstractLayeredScene.__name__} class in order to use {LayeredSceneMeta.__name__} metaclass"
            )

        if "render" in namespace:
            raise TypeError("render() method must not be overriden")

        if any(isinstance(getattr(cls, "__setattr__", None), metacls.__setattr_wrapper) for cls in bases):
            add_drawable_attributes = False

        if add_drawable_attributes:
            setattr_func: Callable[[AbstractLayeredScene, str, Any], Any] = namespace.get("__setattr__", bases[0].__setattr__)
            delattr_func: Callable[[AbstractLayeredScene, str], Any] = namespace.get("__delattr__", bases[0].__delattr__)

            @wraps(setattr_func)
            def setattr_wrapper(self: AbstractLayeredScene, name: str, value: Any, /) -> Any:
                try:
                    group: LayeredGroup = self.group
                except AttributeError:
                    return setattr_func(self, name, value)
                output: Any = setattr_func(self, name, value)
                if isinstance(value, Drawable):
                    group.add(value)
                return output

            @wraps(delattr_func)
            def delattr_wrapper(self: AbstractLayeredScene, name: str, /) -> Any:
                try:
                    group: LayeredGroup = self.group
                except AttributeError:
                    return delattr_func(self, name)
                _MISSING: Any = object()
                value: Any = getattr(self, name, _MISSING)
                output: Any = delattr_func(self, name)
                if value is not _MISSING and isinstance(value, Drawable) and value in group:
                    group.remove(value)
                return output

            namespace["__setattr__"] = metacls.__setattr_wrapper(setattr_wrapper)
            namespace["__delattr__"] = delattr_wrapper

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    class __setattr_wrapper:
        def __init__(self, setattr_func: Callable[[Any, str, Any], None]) -> None:
            self.__func__: Callable[[object, str, Any], None] = setattr_func

        def __call__(self, __obj: object, __name: str, __value: Any, /) -> None:
            func = self.__func__
            return func(__obj, __name, __value)

        def __get__(self, obj: object, objtype: type | None = None, /) -> Callable[..., Any]:
            if obj is None:
                return self
            return MethodType(self, obj)

        @property
        def __wrapped__(self) -> Callable[..., Any]:
            return self.__func__


class AbstractLayeredScene(Scene, metaclass=LayeredSceneMeta):

    __slots__ = ()

    @property
    @abstractmethod
    def group(self) -> LayeredGroup:
        raise NotImplementedError

    def destroy(self) -> None:
        super().destroy()
        self.group.clear()

    def render_before(self) -> None:
        pass

    def render_after(self) -> None:
        pass

    @final
    def render(self) -> None:
        group: LayeredGroup = self.group
        self.render_before()
        self.window.draw(group)
        self.render_after()


class LayeredScene(AbstractLayeredScene, metaclass=LayeredSceneMeta):

    __slots__ = ("__group",)

    def __init__(self) -> None:
        super().__init__()
        self.__group: LayeredGroup = LayeredGroup()

    @property
    def group(self) -> LayeredGroup:
        return self.__group


class AbstractAutoLayeredScene(AbstractLayeredScene, add_drawable_attributes=True):
    __slots__ = ()


class LayeredMainSceneMeta(LayeredSceneMeta, MainSceneMeta):
    __slots__ = ()


class LayeredMainScene(LayeredScene, MainScene, metaclass=LayeredMainSceneMeta):
    __slots__ = ()


class SceneWindow(Window):
    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] = (0, 0),
        *,
        resizable: bool = False,
        fullscreen: bool = False,
        vsync: bool = True,
    ) -> None:
        super().__init__(title=title, size=size, resizable=resizable, fullscreen=fullscreen, vsync=vsync)
        self.__callback_after_scenes: dict[Scene, _WindowCallbackList] = dict()
        self.__scenes: _SceneManager
        self.__accumulator: float = 0
        self.__running: bool = False

    __Self = TypeVar("__Self", bound="SceneWindow")

    @contextmanager
    def open(self: __Self) -> Iterator[__Self]:
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
    def run(self, default_scene: type[Scene], **scene_kwargs: Any) -> None:
        if self.__running:
            raise WindowError("SceneWindow already running")
        self.__running = True
        self.__scenes.clear()
        self.__scenes._apply_themes()
        self.__accumulator = 0
        gc.collect()
        try:
            self.__scenes.go_to(default_scene, awake_kwargs=scene_kwargs)
        except _SceneManager.NewScene as exc:
            exc.actual_scene.on_start_loop_before_transition()
            exc.actual_scene.on_start_loop()
        looping = self.looping
        process_events = self.process_events
        update_scene = self.update_scene
        render_scene = self.render_scene
        refresh_screen = self.refresh
        scene_transition = self.__scene_transition

        try:
            while looping():
                try:
                    for _ in process_events():
                        pass
                    update_scene()
                    render_scene()
                    refresh_screen()
                except _SceneManager.NewScene as exc:
                    if exc.previous_scene is None:
                        raise TypeError("Previous scene must not be None") from None
                    with ExitStack() as all_scenes_stack:
                        for scene in reversed(exc.closing_scenes):
                            all_scenes_stack.enter_context(scene.exit_stack)
                        if not self.__scenes.started(exc.previous_scene):
                            all_scenes_stack.enter_context(exc.previous_scene.exit_stack)
                        scene_transition(exc.previous_scene, exc.actual_scene, exc.closing_scenes, exc.transition)
                except _SceneManager.SceneException as exc:
                    print(f"{type(exc).__name__}: {exc}", file=stderr)
                    continue
        finally:
            self.__scenes.clear()
            self.__running = False

    def __scene_transition(
        self,
        previous_scene: Scene,
        actual_scene: Scene,
        closing_scenes: Sequence[Scene],
        transition_factory: Callable[[Renderer, Surface, Surface], SceneTransitionCoroutine] | None,
    ) -> None:
        if previous_scene is None:
            raise TypeError("Previous scene must not be None")
        previous_scene.on_quit_before_transition()
        actual_scene.on_start_loop_before_transition()
        if transition_factory is not None:
            with self.capture(draw_on_default_at_end=False) as previous_scene_surface:
                self.clear(previous_scene.background_color)
                previous_scene.render()
            with self.capture(draw_on_default_at_end=False) as actual_scene_surface:
                self.clear(actual_scene.background_color)
                actual_scene.render()
            with self.capture() as window_surface, self.block_all_events_context(), self.no_window_callback_processing():
                transition: SceneTransitionCoroutine
                transition = transition_factory(SurfaceRenderer(window_surface), previous_scene_surface, actual_scene_surface)
                animating = True
                try:
                    next(transition)
                except StopIteration:
                    animating = False
                next_transition = transition.send
                next_fixed_transition = lambda: next_transition(None)
                while self.looping() and animating:
                    for _ in self.process_events():
                        pass
                    try:
                        self._fixed_updates_call(next_fixed_transition)
                        self._interpolation_updates_call(next_transition)
                    except StopIteration:
                        animating = False
                    self.refresh()
                del next_fixed_transition, next_transition, transition
        previous_scene.on_quit()
        if not self.__scenes.started(previous_scene):
            self.__scenes._destroy_awaken_scene(previous_scene)
        for scene in closing_scenes:
            with scene.exit_stack:
                scene.on_quit_before_transition()
                scene.on_quit()
                self.__scenes._destroy_awaken_scene(scene)
        self.__callback_after_scenes.pop(previous_scene, None)
        self.__accumulator = 0
        self.clear_all_events()
        gc.collect()
        actual_scene.on_start_loop()

    def refresh(self) -> float:
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

    def update_scene(self) -> None:
        scene: Scene | None = self.__scenes.top()
        if scene is None:
            return
        self._fixed_updates_call(scene.fixed_update)
        self._interpolation_updates_call(scene.update_alpha)
        scene.update()

    def render_scene(self) -> None:
        scene: Scene | None = self.__scenes.top()
        if scene is None:
            return
        self.clear(scene.background_color)
        scene.render()

    def start_scene(
        self,
        scene: type[Scene],
        *,
        transition: SceneTransition | None = None,
        remove_actual: bool = False,
        **awake_kwargs: Any,
    ) -> NoReturn:
        self.__scenes.go_to(scene, transition=transition, remove_actual=remove_actual, awake_kwargs=awake_kwargs)

    def stop_actual_scene(self) -> NoReturn:
        self.__scenes.go_back()

    def _process_callbacks(self) -> None:
        super()._process_callbacks()
        actual_scene = self.__scenes.top()
        if actual_scene in self.__callback_after_scenes:
            self.__callback_after_scenes[actual_scene].process()

    def process_events(self) -> Iterator[Event]:
        actual_scene: Scene | None = self.__scenes.top()
        manager: EventManager | None = actual_scene.event if actual_scene is not None else None
        manager_process_event: Callable[[Event], bool] = manager.process_event if manager is not None else lambda event: False
        process_event: Callable[[Event], bool] = actual_scene.handle_event if actual_scene is not None else lambda event: False
        for event in super().process_events():
            if not manager_process_event(event) and not process_event(event):
                yield event
        if manager is not None:
            manager.handle_mouse_position()

    def used_framerate(self) -> int:
        framerate = super().used_framerate()
        for scene in self.__scenes.from_top_to_bottom():
            f: int = scene.__class__.get_required_framerate()
            if f > 0:
                framerate = f
                break
        return framerate

    def used_fixed_framerate(self) -> int:
        framerate = super().used_fixed_framerate()
        for scene in self.__scenes.from_top_to_bottom():
            f: int = scene.__class__.get_required_fixed_framerate()
            if f > 0:
                framerate = f
                break
        return framerate

    def get_busy_loop(self) -> bool:
        actual_scene: Scene | None = self.__scenes.top()
        return super().get_busy_loop() or (actual_scene is not None and actual_scene.__class__.require_busy_loop())

    def remove_window_callback(self, window_callback: WindowCallback) -> None:
        if not isinstance(window_callback, _SceneWindowCallback):
            return super().remove_window_callback(window_callback)
        scene = window_callback.scene
        scene_callback_after: _WindowCallbackList | None = self.__callback_after_scenes.get(scene)
        if scene_callback_after is None:
            return
        with suppress(ValueError):
            scene_callback_after.remove(window_callback)
        if not scene_callback_after:
            self.__callback_after_scenes.pop(scene)

    del __Self


class _SceneManager:
    class SceneException(BaseException):
        pass

    class NewScene(SceneException):
        def __init__(
            self,
            previous_scene: Scene | None,
            actual_scene: Scene,
            transition: Callable[[Renderer, Surface, Surface], SceneTransitionCoroutine] | None,
            closing_scenes: list[Scene],
        ) -> None:
            super().__init__(
                f"New scene open, from {type(previous_scene).__name__ if previous_scene else None} to {type(actual_scene).__name__}"
            )
            self.previous_scene: Scene | None = previous_scene
            self.actual_scene: Scene = actual_scene
            self.transition = transition
            self.closing_scenes = closing_scenes

    class SameScene(SceneException):
        def __init__(self, scene: Scene) -> None:
            super().__init__(f"Trying to go to the same running scene: {type(scene).__name__!r}")
            self.scene: Scene = scene

    __scene_manager_attribute: Final[str] = mangle_private_attribute(Scene, "manager")

    def __init__(self, window: SceneWindow) -> None:
        def new_scene(cls: type[Scene]) -> Scene:
            scene: Scene = cls.__new__(cls)
            setattr(scene, self.__scene_manager_attribute, self)
            scene.__init__()  # type: ignore[misc]
            return scene

        self.__window: SceneWindow = window
        self.__all: dict[type[Scene], Scene] = {}
        self.__all.update({cls: new_scene(cls) for cls in _ALL_SCENES})
        self.__stack: list[Scene] = []
        self.__returning_transitions: dict[type[Scene], ReturningSceneTransition] = {}
        self.__awaken: set[Scene] = set()

    def __del__(self) -> None:
        for scene in self.__all.values():
            scene.__del_scene__()
        self.__all.clear()

    def __del_manager__(self) -> None:
        for scene in self.__all.values():
            delattr(scene, self.__scene_manager_attribute)

    def _destroy_awaken_scene(self, scene: Scene) -> None:
        with scene.exit_stack:
            try:
                self.__awaken.remove(scene)
            except KeyError:
                return
            all_attributes: list[str] = list(scene.__dict__)
            scene.destroy()
        for attr in all_attributes:
            if attr != self.__scene_manager_attribute:
                delattr(scene, attr)
        scene.__init__()  # type: ignore[misc]

    def _apply_themes(self) -> None:
        for scene in self.__all.values():
            scene.__theme_init__()

    def __iter__(self) -> Iterator[Scene]:
        return self.from_top_to_bottom()

    def from_top_to_bottom(self) -> Iterator[Scene]:
        return iter(self.__stack)

    def from_bottom_to_top(self) -> Iterator[Scene]:
        return reversed(self.__stack)

    def top(self) -> Scene | None:
        return self.__stack[0] if self.__stack else None

    def started(self, scene: Scene) -> bool:
        return scene in self.__stack

    def is_awaken(self, scene: Scene) -> bool:
        return scene in self.__awaken

    def clear(self) -> None:
        with ExitStack() as all_scenes_exit_stack:
            for scene in reversed(self.__stack):
                all_scenes_exit_stack.enter_context(scene.exit_stack)
            while self.__stack:
                scene = self.__stack.pop(0)
                with suppress(Exception):
                    scene.on_quit_before_transition()
                with suppress(Exception):
                    scene.on_quit()
                with suppress(Exception):
                    self._destroy_awaken_scene(scene)
        gc.collect()

    def render(self, scene: type[Scene]) -> None:
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
        scene: type[Scene],
        *,
        transition: SceneTransition | None = None,
        remove_actual: bool = False,
        awake_kwargs: dict[str, Any] = {},
    ) -> NoReturn:
        if scene.__abstractmethods__:
            raise TypeError(f"{scene.__name__} is an abstract class")
        next_scene = self.__all[scene]
        stack = self.__stack
        actual_scene = stack[0] if stack else None
        if actual_scene is next_scene:
            raise _SceneManager.SameScene(actual_scene)
        scene_transition: Callable[[Renderer, Surface, Surface], SceneTransitionCoroutine] | None = None
        closing_scenes: list[Scene] = []
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
    def window(self) -> SceneWindow:
        return self.__window


class _SceneWindowCallback(WindowCallback):
    def __init__(
        self,
        master: Scene,
        wait_time: float,
        callback: Callable[..., None],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] = {},
        loop: bool = False,
    ) -> None:
        self.__scene: Scene = master
        super().__init__(master.window, wait_time, callback, args, kwargs, loop)

    def __call__(self) -> None:
        scene = self.__scene
        if not scene.looping():
            return
        return super().__call__()

    @property
    def scene(self) -> Scene:
        return self.__scene


del _S, _P
