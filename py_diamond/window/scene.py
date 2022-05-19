# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Scene module"""

from __future__ import annotations

__all__ = [
    "AbstractAutoLayeredDrawableScene",
    "AbstractLayeredMainScene",
    "AbstractLayeredScene",
    "LayeredMainSceneMeta",
    "LayeredSceneMeta",
    "MainScene",
    "MainSceneMeta",
    "RenderedLayeredScene",
    "ReturningSceneTransition",
    "Scene",
    "SceneMeta",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneWindow",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import gc
from abc import abstractmethod
from contextlib import ExitStack, contextmanager, suppress
from inspect import isgeneratorfunction
from itertools import chain
from operator import truth
from sys import stderr
from types import MethodType
from typing import (
    TYPE_CHECKING,
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
    overload,
)

from ..graphics.color import Color
from ..graphics.drawable import Drawable, LayeredDrawableGroup
from ..graphics.renderer import AbstractRenderer, SurfaceRenderer
from ..graphics.surface import Surface
from ..graphics.theme import ClassWithThemeNamespaceMeta, closed_namespace, no_theme_decorator
from ..system.object import Object, final
from ..system.utils._mangling import getattr_pv, mangle_private_attribute
from ..system.utils.abc import concreteclassmethod, isconcreteclass
from ..system.utils.functools import cache, wraps
from .display import Window, WindowCallback, WindowError, _WindowCallbackList
from .event import Event, EventManager
from .time import Time

_P = ParamSpec("_P")

_ALL_SCENES: Final[list[type[Scene]]] = []


class SceneMeta(ClassWithThemeNamespaceMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="SceneMeta")

    __theme_namespace_decorator_exempt: Sequence[str] = (
        "__del_scene__",
        "render",
        "fixed_update",
        "interpolation_update",
        "is_awaken",
        "looping",
        "start",
        "stop",
        "after",
        "every",
    )

    def __new__(
        metacls: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        framerate: int = 0,
        fixed_framerate: int = 0,
        busy_loop: bool = False,
        **kwargs: Any,
    ) -> __Self:
        if "Scene" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, Scene) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Scene.__name__} class in order to use {SceneMeta.__name__} metaclass"
            )

        if not all(issubclass(cls, Scene) for cls in bases):
            raise TypeError("Multiple inheritance with other class than Scene is not supported")

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if isconcreteclass(cls):
            _ALL_SCENES.append(cast(type[Scene], cls))
            cls.__framerate = max(int(framerate), 0)
            cls.__fixed_framerate = max(int(fixed_framerate), 0)
            cls.__busy_loop = truth(busy_loop)
        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError(f"{name} cannot be overriden")
        return super().__setattr__(name, value)

    @final
    @concreteclassmethod
    def get_required_framerate(cls) -> int:
        return cls.__framerate  # type: ignore[no-any-return, attr-defined]

    @final
    @concreteclassmethod
    def get_required_fixed_framerate(cls) -> int:
        return cls.__fixed_framerate  # type: ignore[no-any-return, attr-defined]

    @final
    @concreteclassmethod
    def require_busy_loop(cls) -> bool:
        return cls.__busy_loop  # type: ignore[no-any-return, attr-defined]

    @classmethod
    @cache
    def get_default_theme_decorator_exempt(metacls) -> frozenset[str]:
        return frozenset(chain(super().get_default_theme_decorator_exempt(), metacls.__theme_namespace_decorator_exempt))


SceneTransitionCoroutine: TypeAlias = Generator[None, float | None, None]


class SceneTransition(Object):
    @abstractmethod
    def show_new_scene(
        self, target: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class ReturningSceneTransition(SceneTransition):
    @abstractmethod
    def hide_actual_scene(
        self, target: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class Scene(Object, metaclass=SceneMeta, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[Sequence[str]] = ("__dict__",)

    __instances: ClassVar[set[type[Scene]]] = set()

    @final
    def __new__(cls) -> Any:
        instances: set[type[Scene]] = Scene.__instances
        if cls in instances:
            raise TypeError(f"Trying to instantiate two scene of same type {f'{cls.__module__}.{cls.__name__}'!r}")
        scene = super().__new__(cls)
        if not issubclass(cls, Dialog):
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
        self.__stack_quit: ExitStack = ExitStack()
        self.__stack_destroy: ExitStack = ExitStack()

    @classmethod
    def __theme_init__(cls) -> None:
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

    def interpolation_update(self, interpolation: float) -> None:
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
        return self.event.process_event(event)

    @final
    def is_awaken(self) -> bool:
        return self.__manager.is_awaken(self)

    @final
    def looping(self) -> bool:
        return self.__manager.top() is self

    def use_framerate(self) -> int:
        return self.__class__.get_required_framerate()

    def use_fixed_framerate(self) -> int:
        return self.__class__.get_required_fixed_framerate()

    @overload
    def start(  # type: ignore[misc]
        self,
        __scene: type[Dialog],
        /,
        **awake_kwargs: Any,
    ) -> None:
        ...

    @overload
    def start(
        self,
        __scene: type[Scene],
        /,
        *,
        transition: SceneTransition | None = None,
        stop_self: bool = False,
        **awake_kwargs: Any,
    ) -> NoReturn:
        ...

    @final
    def start(
        self,
        __scene: type[Scene],
        /,
        **kwargs: Any,
    ) -> None:
        if issubclass(__scene, Dialog):
            return self.__manager.open_dialog(__scene, awake_kwargs=kwargs)

        transition: SceneTransition | None = kwargs.pop("transition", None)
        stop_self: bool = kwargs.pop("stop_self", False)
        self.__manager.go_to(__scene, transition=transition, remove_actual=stop_self, awake_kwargs=kwargs)

    @final
    def stop(self) -> NoReturn:
        self.__manager.go_back()

    @overload
    def after(
        self, __milliseconds: float, __callback: Callable[_P, None], /, *args: _P.args, **kwargs: _P.kwargs
    ) -> WindowCallback:
        ...

    @overload
    def after(self, __milliseconds: float, /) -> Callable[[Callable[[], None]], WindowCallback]:
        ...

    def after(
        self, __milliseconds: float, __callback: Callable[..., None] | None = None, /, *args: Any, **kwargs: Any
    ) -> WindowCallback | Callable[[Callable[..., None]], WindowCallback]:
        def decorator(__callback: Callable[..., None], /) -> WindowCallback:
            window_callback: WindowCallback = _SceneWindowCallback(self, __milliseconds, __callback, args, kwargs)
            callback_dict: dict[Scene, _WindowCallbackList] = self.__callback_after_dict
            callback_list: _WindowCallbackList = self.__callback_after

            callback_dict[self] = callback_list
            callback_list.append(window_callback)
            return window_callback

        if __callback is not None:
            return decorator(__callback)
        return decorator

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

    @overload
    def every(self, __milliseconds: float, /) -> Callable[[Callable[[], Iterator[None] | None]], WindowCallback]:
        ...

    def every(
        self, __milliseconds: float, __callback: Callable[..., Any] | None = None, /, *args: Any, **kwargs: Any
    ) -> WindowCallback | Callable[[Callable[..., Any]], WindowCallback]:
        def decorator(__callback: Callable[..., Any], /) -> WindowCallback:
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

        if __callback is not None:
            return decorator(__callback)
        return decorator

    @property
    def window(self) -> SceneWindow:
        return self.__manager.window

    @property
    def event(self) -> EventManager:
        return self.__event

    @property
    def on_quit_exit_stack(self) -> ExitStack:
        return self.__stack_quit

    @property
    def destroy_exit_stack(self) -> ExitStack:
        return self.__stack_destroy

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
        if isconcreteclass(cls):
            closed_namespace(cls)
        return cls


class MainScene(Scene, metaclass=MainSceneMeta):
    pass


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

        setattr_wrapper_cls = metacls.__setattr_wrapper

        if any(isinstance(getattr(cls, "__setattr__", None), setattr_wrapper_cls) for cls in bases):
            add_drawable_attributes = False

        if add_drawable_attributes:
            setattr_func: Callable[[AbstractLayeredScene, str, Any], Any] = namespace.get("__setattr__", bases[0].__setattr__)
            delattr_func: Callable[[AbstractLayeredScene, str], Any] = namespace.get("__delattr__", bases[0].__delattr__)

            @setattr_wrapper_cls
            @wraps(setattr_func)
            def setattr_wrapper(self: AbstractLayeredScene, name: str, value: Any, /) -> Any:
                try:
                    group: LayeredDrawableGroup = self.group
                except AttributeError:
                    return setattr_func(self, name, value)
                output: Any = setattr_func(self, name, value)
                if isinstance(value, Drawable):
                    group.add(value)
                return output

            @wraps(delattr_func)
            def delattr_wrapper(self: AbstractLayeredScene, name: str, /) -> Any:
                try:
                    group: LayeredDrawableGroup = self.group
                except AttributeError:
                    return delattr_func(self, name)
                _MISSING: Any = object()
                value: Any = getattr(self, name, _MISSING)
                output: Any = delattr_func(self, name)
                if value is not _MISSING and isinstance(value, Drawable) and value in group:
                    group.remove(value)
                return output

            namespace["__setattr__"] = setattr_wrapper
            namespace["__delattr__"] = delattr_wrapper

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    @classmethod
    @cache
    def get_default_theme_decorator_exempt(metacls) -> frozenset[str]:
        return frozenset(chain(super().get_default_theme_decorator_exempt(), ("__setattr__", "__delattr__")))

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
    @property
    @abstractmethod
    def group(self) -> LayeredDrawableGroup:
        raise NotImplementedError

    def destroy(self) -> None:
        super().destroy()
        self.group.clear()


class RenderedLayeredScene(AbstractLayeredScene):
    def __init__(self) -> None:
        super().__init__()
        self.__group: LayeredDrawableGroup = LayeredDrawableGroup()

    @no_theme_decorator
    def render_before(self) -> None:
        pass

    @no_theme_decorator
    def render_after(self) -> None:
        pass

    @final
    def render(self) -> None:
        group: LayeredDrawableGroup = self.group
        self.render_before()
        self.window.draw(group)
        self.render_after()

    @property
    def group(self) -> LayeredDrawableGroup:
        return self.__group


class AbstractAutoLayeredDrawableScene(AbstractLayeredScene, add_drawable_attributes=True):
    pass


class LayeredMainSceneMeta(LayeredSceneMeta, MainSceneMeta):
    pass


class AbstractLayeredMainScene(AbstractLayeredScene, MainScene, metaclass=LayeredMainSceneMeta):
    pass


class DialogMeta(SceneMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="DialogMeta")

    __theme_namespace_decorator_exempt: Sequence[str] = ("render",)

    def __new__(
        metacls: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> __Self:
        if "Dialog" not in globals():
            return super().__new__(metacls, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, Dialog) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Dialog.__name__} class in order to use {DialogMeta.__name__} metaclass"
            )

        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __init__(
        cls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace, **kwargs)
        if cls in _ALL_SCENES:
            _ALL_SCENES.remove(cls)  # type: ignore[arg-type]

    @classmethod
    @cache
    def get_default_theme_decorator_exempt(metacls) -> frozenset[str]:
        return frozenset(chain(super().get_default_theme_decorator_exempt(), metacls.__theme_namespace_decorator_exempt))


class Dialog(Scene, metaclass=DialogMeta):
    def __init__(self) -> None:
        super().__init__()
        self.__master: Scene
        try:
            self.__master
        except AttributeError:
            raise TypeError(f"Trying to instantiate {self.__class__.__name__!r} dialog outside a SceneWindow manager") from None
        self.background_color = Color(0, 0, 0, 0)

    @property
    def master(self) -> Scene:
        return self.__master


class SceneWindow(Window):
    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] = (0, 0),
        *,
        resizable: bool = False,
        fullscreen: bool = False,
        vsync: bool = False,
    ) -> None:
        super().__init__(title=title, size=size, resizable=resizable, fullscreen=fullscreen, vsync=vsync)
        self.__callback_after_scenes: dict[Scene, _WindowCallbackList] = dict()
        self.__scenes: _SceneManager
        self.__accumulator: float = 0
        self.__running: bool = False

    if TYPE_CHECKING:
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
        ClassWithThemeNamespaceMeta.theme_initialize_all()
        self.__accumulator = 0
        gc.collect()
        try:
            self.start_scene(default_scene, awake_kwargs=scene_kwargs)
        except _SceneManager.NewScene as exc:
            exc.actual_scene.on_start_loop_before_transition()
            exc.actual_scene.on_start_loop()
        looping = self.looping
        process_events = self.handle_events
        update_scene = self.update_scene
        render_scene = self.render_scene
        refresh_screen = self.refresh
        scene_transition = self.__scene_transition
        on_start_loop: Callable[[], None] | None = None

        try:
            while looping():
                if on_start_loop is not None:
                    on_start_loop()
                    on_start_loop = None
                try:
                    process_events()
                    update_scene()
                    render_scene()
                    refresh_screen()
                except _SceneManager.NewScene as exc:
                    if exc.previous_scene is None:
                        raise TypeError("Previous scene must not be None") from None
                    with ExitStack() as all_scenes_stack:
                        for scene in reversed(exc.closing_scenes):
                            all_scenes_stack.enter_context(scene.destroy_exit_stack)
                            all_scenes_stack.enter_context(scene.on_quit_exit_stack)
                        if not self.__scenes.started(exc.previous_scene):
                            all_scenes_stack.enter_context(exc.previous_scene.destroy_exit_stack)
                        all_scenes_stack.enter_context(exc.previous_scene.on_quit_exit_stack)
                        try:
                            scene_transition(
                                exc.previous_scene,
                                exc.actual_scene,
                                exc.closing_scenes,
                                exc.transition,
                            )
                        except _SceneManager.SceneException as sub_exc:
                            raise RuntimeError("Open a new scene within a scene transition is forbidden") from sub_exc
                    on_start_loop = exc.actual_scene.on_start_loop
                except _SceneManager.SceneException as exc:
                    print(f"{type(exc).__name__}: {exc}", file=stderr)
                    continue
        finally:
            self.__running = False
            self.__scenes.clear()

    def __scene_transition(
        self,
        previous_scene: Scene,
        actual_scene: Scene,
        closing_scenes: Sequence[Scene],
        transition_factory: Callable[[AbstractRenderer, Surface, Surface], SceneTransitionCoroutine] | None,
    ) -> None:
        if previous_scene is None:
            raise TypeError("Previous scene must not be None")
        previous_scene.on_quit_before_transition()
        for scene in closing_scenes:
            scene.on_quit_before_transition()
        actual_scene.on_start_loop_before_transition()
        if transition_factory is not None:
            with self.capture(draw_on_default_at_end=False) as previous_scene_surface:
                self.clear(previous_scene.background_color)
                previous_scene.render()
            with self.capture(draw_on_default_at_end=False) as actual_scene_surface:
                self.clear(actual_scene.background_color)
                actual_scene.render()
            with (
                self.capture() as window_surface,
                self.block_all_events_context(),
                self.no_window_callback_processing(),
            ):
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
                    self.handle_events()
                    try:
                        self._fixed_updates_call(next_fixed_transition)
                        self._interpolation_updates_call(next_transition)
                    except StopIteration:
                        animating = False
                    self.refresh()
                del next_fixed_transition, next_transition, transition
        with previous_scene.on_quit_exit_stack:
            previous_scene.on_quit()
        if not self.__scenes.started(previous_scene):
            self.__scenes._destroy_awaken_scene(previous_scene)
        for scene in closing_scenes:
            with scene.on_quit_exit_stack:
                scene.on_quit()
            self.__scenes._destroy_awaken_scene(scene)
        self.__callback_after_scenes.pop(previous_scene, None)
        self.__accumulator = 0
        self.clear_all_events()
        gc.collect()

    def refresh(self) -> float:
        real_delta_time: float = super().refresh()
        self.__accumulator += max(real_delta_time, 0) / 1000
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
        self._interpolation_updates_call(scene.interpolation_update)
        scene.update()

    def render_scene(self) -> None:
        scene: Scene | None = self.__scenes.top()
        if scene is None:
            return
        self.__scenes._render(scene)

    @final
    def start_scene(
        self,
        __scene: type[Scene],
        /,
        *,
        transition: SceneTransition | None = None,
        remove_actual: bool = False,
        **awake_kwargs: Any,
    ) -> NoReturn:
        if issubclass(__scene, Dialog):
            raise TypeError(f"start_scene() does not accept Dialogs")
        self.__scenes.go_to(__scene, transition=transition, remove_actual=remove_actual, awake_kwargs=awake_kwargs)

    def _process_callbacks(self) -> None:
        super()._process_callbacks()
        actual_scene = self.__scenes.top()
        if actual_scene in self.__callback_after_scenes:
            self.__callback_after_scenes[actual_scene].process()

    def _process_event(self, event: Event) -> bool:
        if super()._process_event(event):
            return True
        actual_scene: Scene | None = self.__scenes.top()
        if actual_scene is None:
            return False
        return actual_scene.handle_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        super()._handle_mouse_position(mouse_pos)
        actual_scene: Scene | None = self.__scenes.top()
        if actual_scene is not None:
            actual_scene.event.handle_mouse_position(mouse_pos)

    def used_framerate(self) -> int:
        framerate = super().used_framerate()
        for scene in self.__scenes.from_top_to_bottom():
            f: int = scene.use_framerate()
            if f > 0:
                framerate = f
                break
        return framerate

    def used_fixed_framerate(self) -> int:
        framerate = super().used_fixed_framerate()
        for scene in self.__scenes.from_top_to_bottom():
            f: int = scene.use_fixed_framerate()
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


class _SceneManager:
    class SceneException(BaseException):
        pass

    class NewScene(SceneException):
        def __init__(
            self,
            previous_scene: Scene | None,
            actual_scene: Scene,
            transition: Callable[[AbstractRenderer, Surface, Surface], SceneTransitionCoroutine] | None,
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

    class DialogStop(SceneException):
        def __init__(self) -> None:
            super().__init__("Dialog window closed")

    __scene_manager_attribute: Final[str] = mangle_private_attribute(Scene, "manager")
    __dialog_master_attribute: Final[str] = mangle_private_attribute(Dialog, "master")

    def __init__(self, window: SceneWindow) -> None:
        def new_scene(cls: type[Scene]) -> Scene:
            scene: Scene = cls.__new__(cls)
            scene.__dict__[self.__scene_manager_attribute] = self
            scene.__init__()  # type: ignore[misc]
            return scene

        self.__window: SceneWindow = window
        self.__all: dict[type[Scene], Scene] = {cls: new_scene(cls) for cls in _ALL_SCENES}
        self.__stack: list[Scene] = []
        self.__returning_transitions: dict[type[Scene], ReturningSceneTransition] = {}
        self.__awaken: set[Scene] = set()
        self.__dialogs: list[Dialog] = []

    def __del__(self) -> None:
        for scene in self.__all.values():
            scene.__del_scene__()
        self.__all.clear()

    def __del_manager__(self) -> None:
        for scene in self.__all.values():
            delattr(scene, self.__scene_manager_attribute)

    def _awake_scene(self, scene: Scene, awake_kwargs: dict[str, Any]) -> None:
        scene.awake(**awake_kwargs)
        self.__awaken.add(scene)

    def _destroy_awaken_scene(self, scene: Scene) -> None:
        with scene.destroy_exit_stack:
            try:
                self.__awaken.remove(scene)
            except KeyError:
                return
            scene.destroy()
            scene.event.unbind_all()
        scene.__dict__.clear()
        if not isinstance(scene, Dialog):
            scene.__dict__[self.__scene_manager_attribute] = self
            scene.__init__()  # type: ignore[misc]

    def __iter__(self) -> Iterator[Scene]:
        return self.from_top_to_bottom()

    def from_top_to_bottom(self) -> Iterator[Scene]:
        return chain(self.__dialogs, self.__stack)

    def from_bottom_to_top(self) -> Iterator[Scene]:
        return chain(reversed(self.__stack), reversed(self.__dialogs))

    def top(self) -> Scene | None:
        if self.__dialogs:
            return self.__dialogs[0]
        return self.__stack[0] if self.__stack else None

    def started(self, scene: Scene) -> bool:
        return scene in self.__stack or scene in self.__dialogs

    def is_awaken(self, scene: Scene) -> bool:
        return scene in self.__awaken

    def clear(self) -> None:
        while self.__stack:
            scene = self.__stack.pop(0)
            with scene.on_quit_exit_stack:
                with suppress(Exception):
                    scene.on_quit_before_transition()
                with suppress(Exception):
                    scene.on_quit()
            with scene.destroy_exit_stack, suppress(Exception):
                self._destroy_awaken_scene(scene)
        gc.collect()

    def render(self, scene: type[Scene]) -> None:
        if not isconcreteclass(scene):
            raise TypeError(f"{scene.__name__} is an abstract class")
        if issubclass(scene, Dialog):
            raise TypeError(f"Trying to draw a Dialog scene")
        obj = self.__all[scene]
        if not obj.is_awaken():
            raise ValueError("Trying to draw non-awaken scene")
        if obj.looping():
            raise ValueError("Trying to draw actual looping scene")
        self._render(obj, fill_background_color=False)

    def _render(self, scene: Scene, *, fill_background_color: bool = True) -> None:
        if fill_background_color:
            self.window.clear(scene.background_color)
        if isinstance(scene, Dialog):
            self._render(scene.master, fill_background_color=fill_background_color)
            self.window.clear(scene.background_color, blend_alpha=True)
        scene.render()

    def go_to(
        self,
        scene: type[Scene],
        *,
        transition: SceneTransition | None = None,
        remove_actual: bool = False,
        awake_kwargs: dict[str, Any] | None = None,
    ) -> NoReturn:
        if not isconcreteclass(scene):
            raise TypeError(f"{scene.__name__} is an abstract class")
        if issubclass(scene, Dialog):
            raise TypeError(f"{scene.__name__} must be opened with open_dialog()")
        if awake_kwargs is None:
            awake_kwargs = {}
        next_scene = self.__all[scene]
        stack = self.__stack
        actual_scene = stack[0] if stack else None
        if actual_scene is next_scene:
            raise _SceneManager.SameScene(actual_scene)
        scene_transition: Callable[[AbstractRenderer, Surface, Surface], SceneTransitionCoroutine] | None = None
        closing_scenes: list[Scene] = []
        if actual_scene is None or next_scene not in stack:
            stack.insert(0, next_scene)
            self._awake_scene(next_scene, awake_kwargs)
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
        if self.__dialogs:
            raise _SceneManager.DialogStop
        if len(self.__stack) <= 1:
            self.window.close()
        self.go_to(self.__stack[1].__class__)

    def open_dialog(
        self,
        dialog: type[Dialog],
        *,
        awake_kwargs: dict[str, Any] | None = None,
    ) -> None:
        if not isconcreteclass(dialog):
            raise TypeError(f"{dialog.__name__} is an abstract class")
        if not self.__stack:
            raise TypeError("Trying to open dialog without opened scene")
        if not issubclass(dialog, Dialog):
            raise TypeError(f"{dialog.__name__} must be opened with go_to()")
        if awake_kwargs is None:
            awake_kwargs = {}
        master: Scene = self.__dialogs[0] if self.__dialogs else self.__stack[0]
        obj: Dialog = object.__new__(dialog)
        obj.__dict__[self.__scene_manager_attribute] = self
        obj.__dict__[self.__dialog_master_attribute] = master
        obj.__init__()  # type: ignore[misc]
        return self.__open_dialog(obj, awake_kwargs=awake_kwargs)

    def __open_dialog(
        self,
        dialog: Dialog,
        *,
        awake_kwargs: dict[str, Any],
    ) -> None:
        dialogs_stack = self.__dialogs

        with ExitStack() as exit_stack:
            dialogs_stack.insert(0, dialog)
            exit_stack.callback(dialogs_stack.remove, dialog)
            self._awake_scene(dialog, awake_kwargs)
            exit_stack.callback(self._destroy_awaken_scene, dialog)
            exit_stack.enter_context(dialog.on_quit_exit_stack)

            window = self.window
            try:
                dialog.on_start_loop_before_transition()
                dialog.on_start_loop()
                while window.looping():
                    window.handle_events()
                    window.update_scene()
                    window.render_scene()
                    window.refresh()
            except _SceneManager.DialogStop:
                pass
            finally:
                dialog.on_quit_before_transition()
                dialog.on_quit()

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
        kwargs: dict[str, Any] | None = None,
        loop: bool = False,
    ) -> None:
        self.__scene: Scene = master
        super().__init__(master.window, wait_time, callback, args, kwargs, loop)

    def __call__(self) -> None:
        try:
            scene = self.__scene
        except AttributeError:  # killed
            return
        if not scene.looping():
            return
        return super().__call__()

    def kill(self) -> None:
        super().kill()
        with suppress(AttributeError):
            del self.__scene

    @property
    def scene(self) -> Scene:
        return self.__scene
