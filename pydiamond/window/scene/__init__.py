# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Scene module"""

from __future__ import annotations

__all__ = [
    "MainScene",
    "ReturningSceneTransition",
    "ReturningSceneTransitionProtocol",
    "Scene",
    "SceneMeta",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneTransitionProtocol",
    "SceneWindow",
]

import gc
from abc import abstractmethod
from collections import deque
from contextlib import ExitStack, contextmanager, suppress
from enum import auto, unique
from inspect import isgeneratorfunction
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Final,
    Generator,
    Iterator,
    NoReturn,
    ParamSpec,
    Protocol,
    Sequence,
    TypeAlias,
    TypeGuard,
    TypeVar,
    overload,
    runtime_checkable,
)
from weakref import WeakKeyDictionary, WeakSet

from ...graphics.color import Color
from ...graphics.renderer import AbstractRenderer
from ...graphics.surface import Surface, SurfaceRenderer
from ...system.enum import AutoLowerNameEnum
from ...system.object import Object, final
from ...system.theme import ClassWithThemeNamespaceMeta, no_theme_decorator
from ...system.time import Time
from ...system.utils._mangling import getattr_pv, mangle_private_attribute, setattr_pv
from ...system.utils.abc import concreteclassmethod, isconcreteclass
from ...system.utils.contextlib import ExitStackView
from ...system.utils.functools import wraps
from ...system.utils.itertools import consume
from ..display import Window, WindowCallback, WindowError, _WindowCallbackList
from ..event import Event, EventManager

_P = ParamSpec("_P")


class SceneMeta(ClassWithThemeNamespaceMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="SceneMeta")

    def __new__(
        mcs: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        framerate: int = 0,
        fixed_framerate: int = 0,
        busy_loop: bool = False,
        **kwargs: Any,
    ) -> __Self:
        try:
            Scene
        except NameError:
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        if not any(issubclass(cls, Scene) for cls in bases):
            raise TypeError(f"{name!r} must inherit from a {Scene.__name__} class in order to use {SceneMeta.__name__} metaclass")

        if not all(issubclass(cls, Scene) for cls in bases):
            raise TypeError("Multiple inheritance with other class than Scene is not supported")

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if isconcreteclass(cls):
            cls.__framerate = max(int(framerate), 0)
            cls.__fixed_framerate = max(int(fixed_framerate), 0)
            cls.__busy_loop = bool(busy_loop)
        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError(f"{name} cannot be overriden")
        return super().__setattr__(name, value)

    @final
    @concreteclassmethod
    def get_required_framerate(cls) -> int:
        return cls.__framerate  # type: ignore[attr-defined]

    @final
    @concreteclassmethod
    def get_required_fixed_framerate(cls) -> int:
        return cls.__fixed_framerate  # type: ignore[attr-defined]

    @final
    @concreteclassmethod
    def require_busy_loop(cls) -> bool:
        return cls.__busy_loop  # type: ignore[attr-defined]


SceneTransitionCoroutine: TypeAlias = Generator[None, float | None, None]


@runtime_checkable
class SceneTransitionProtocol(Protocol):
    @abstractmethod
    def show_new_scene(
        self, window: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


@runtime_checkable
class ReturningSceneTransitionProtocol(SceneTransitionProtocol, Protocol):
    @abstractmethod
    def hide_actual_scene(
        self, window: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        raise NotImplementedError


class _BaseSceneTransitionImpl(Object):
    __slots__ = ()

    @final
    def _loop(self) -> SceneTransitionCoroutine:
        while True:
            try:
                while (interpolation := (yield)) is None:
                    self.fixed_update()
                self.interpolation_update(interpolation)
                self.update()
                self.render()
            except GeneratorExit:
                self.destroy()
                return
            except BaseException:
                self.destroy()
                raise

    def fixed_update(self) -> None:
        pass

    def interpolation_update(self, interpolation: float) -> None:
        pass

    def update(self) -> None:
        pass

    @abstractmethod
    def render(self) -> None:
        raise NotImplementedError

    @final
    def stop(self) -> NoReturn:
        raise GeneratorExit

    def destroy(self) -> None:
        pass


class SceneTransition(_BaseSceneTransitionImpl):
    __slots__ = ("window",)

    window: AbstractRenderer

    @abstractmethod
    def init(self, previous_scene_image: Surface, actual_scene_image: Surface) -> None:
        raise NotImplementedError

    @final
    def show_new_scene(
        self, window: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        self.window = window
        self.init(previous_scene_image=previous_scene_image, actual_scene_image=actual_scene_image)
        try:
            return (yield from self._loop())
        finally:
            with suppress(AttributeError):
                del self.window


class ReturningSceneTransition(_BaseSceneTransitionImpl):
    __slots__ = ("window",)

    window: AbstractRenderer

    @unique
    class Context(AutoLowerNameEnum):
        SHOW = auto()
        HIDE = auto()

    @abstractmethod
    def init(self, previous_scene_image: Surface, actual_scene_image: Surface, context: Context) -> None:
        raise NotImplementedError

    @final
    def show_new_scene(
        self, window: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        self.window = window
        context = ReturningSceneTransition.Context.SHOW
        self.init(previous_scene_image=previous_scene_image, actual_scene_image=actual_scene_image, context=context)
        try:
            return (yield from self._loop())
        finally:
            with suppress(AttributeError):
                del self.window

    @final
    def hide_actual_scene(
        self, window: AbstractRenderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        self.window = window
        context = ReturningSceneTransition.Context.HIDE
        self.init(previous_scene_image=previous_scene_image, actual_scene_image=actual_scene_image, context=context)
        try:
            return (yield from self._loop())
        finally:
            with suppress(AttributeError):
                del self.window


class Scene(Object, metaclass=SceneMeta, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[Sequence[str]] = ("__dict__", "__weakref__")

        __Self = TypeVar("__Self", bound="Scene")

    @final
    def __new__(cls: type[__Self], *args: Any, **kwargs: Any) -> __Self:
        return super().__new__(cls)

    def __init__(self) -> None:
        self.__manager: _SceneManager
        try:
            manager = self.__manager
        except AttributeError:
            raise TypeError(f"Trying to instantiate {self.__class__.__name__!r} scene outside a SceneWindow manager") from None

        self.__event: EventManager = EventManager()
        self.__bg_color: Color = Color(0, 0, 0)
        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__callback_after_dict: WeakKeyDictionary[Scene, _WindowCallbackList] = getattr_pv(
            manager.window, "callback_after_scenes", owner=SceneWindow
        )
        self.__stack_quit: ExitStack = ExitStack()
        self.__stack_destroy: ExitStack = ExitStack()

    @classmethod
    def __theme_init__(cls) -> None:
        pass

    @no_theme_decorator
    def __del_scene__(self) -> None:
        with self.__stack_destroy, ExitStack() as stack:
            stack.callback(self.__dict__.clear)

            @stack.callback
            def _() -> None:
                for window_callback in list(self.__callback_after):
                    window_callback.kill()
                self.__callback_after_dict.pop(self, None)

            stack.callback(self.__event.clear)
            stack.callback(self.__stack_quit.close)

    @abstractmethod
    def awake(self, **kwargs: Any) -> None:
        pass

    def on_restart(self, **kwargs: Any) -> None:
        pass

    def on_start_loop_before_transition(self) -> None:
        pass

    def on_start_loop(self) -> None:
        pass

    def fixed_update(self) -> None:
        pass

    @no_theme_decorator
    def interpolation_update(self, interpolation: float) -> None:
        pass

    def update(self) -> None:
        pass

    def on_quit_before_transition(self) -> None:
        pass

    def on_quit(self) -> None:
        self.__stack_quit.close()

    @abstractmethod
    @no_theme_decorator
    def render(self) -> None:
        raise NotImplementedError

    def draw_scene(self, scene: type[Scene]) -> None:
        self.__manager.render(scene)

    def handle_event(self, event: Event) -> bool:
        return self.__event._process_event(event)

    def handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        self.__event._handle_mouse_position(mouse_pos)

    @final
    @no_theme_decorator
    def is_awaken(self) -> bool:
        return self.__manager.is_awaken(self)

    @final
    @no_theme_decorator
    def looping(self) -> bool:
        return self.__manager.top() is self

    @no_theme_decorator
    def use_framerate(self) -> int:
        return self.__class__.get_required_framerate()

    @no_theme_decorator
    def use_fixed_framerate(self) -> int:
        return self.__class__.get_required_fixed_framerate()

    @overload
    def start(  # type: ignore[misc]
        self,
        __dialog: type[Dialog],
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
        transition: SceneTransitionProtocol | None = None,
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

        transition: SceneTransitionProtocol | None = kwargs.pop("transition", None)
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

    @no_theme_decorator
    def after(
        self, __milliseconds: float, __callback: Callable[..., None] | None = None, /, *args: Any, **kwargs: Any
    ) -> WindowCallback | Callable[[Callable[..., None]], WindowCallback]:
        def decorator(__callback: Callable[..., None], /) -> WindowCallback:
            window_callback: WindowCallback = _SceneWindowCallback(self, __milliseconds, __callback, args, kwargs)
            callback_dict: WeakKeyDictionary[Scene, _WindowCallbackList] = self.__callback_after_dict
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

    @no_theme_decorator
    def every(
        self, __milliseconds: float, __callback: Callable[..., Any] | None = None, /, *args: Any, **kwargs: Any
    ) -> WindowCallback | Callable[[Callable[..., Any]], WindowCallback]:
        def decorator(__callback: Callable[..., Any], /) -> WindowCallback:
            window_callback: WindowCallback
            callback_dict: WeakKeyDictionary[Scene, _WindowCallbackList] = self.__callback_after_dict
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
    def on_quit_exit_stack(self) -> ExitStackView:
        return ExitStackView(self.__stack_quit)

    @property
    def destroy_exit_stack(self) -> ExitStackView:
        return ExitStackView(self.__stack_destroy)

    @property
    def background_color(self) -> Color:
        return self.__bg_color

    @background_color.setter
    def background_color(self, color: Color) -> None:
        self.__bg_color = Color(color)


class MainScene(Scene):
    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        if isconcreteclass(cls):
            cls.set_closed_theme_namespace()


class SceneWindow(Window):
    DEFAULT_FIXED_FRAMERATE: Final[int] = 50

    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] | None = None,
        *,
        resizable: bool = False,
        fullscreen: bool = False,
        vsync: bool = False,
    ) -> None:
        super().__init__(title=title, size=size, resizable=resizable, fullscreen=fullscreen, vsync=vsync)
        self.__callback_after_scenes: WeakKeyDictionary[Scene, _WindowCallbackList] = WeakKeyDictionary()
        self.__scenes: _SceneManager
        self.__default_fixed_framerate: int = self.DEFAULT_FIXED_FRAMERATE
        self.__accumulator: float = 0
        self.__reset_interpolation_data()
        self.__running: bool = False
        self.__event = EventManager()

    @contextmanager
    def open(self) -> Iterator[None]:
        with ExitStack() as stack_before_open:
            stack_before_open.callback(self.__event.clear)

            del stack_before_open
            with super().open(), ExitStack() as stack_after_open:
                self.__scenes = _SceneManager(self)
                self.__reset_interpolation_data()
                stack_after_open.callback(self.__reset_interpolation_data)

                @stack_after_open.callback
                def _() -> None:
                    try:
                        self.__scenes.clear()
                    finally:
                        del self.__scenes

                stack_after_open.callback(self.__callback_after_scenes.clear)
                yield

    @final
    def run(self, __default_scene: type[Scene], /, **scene_kwargs: Any) -> None:
        if not self.is_open():
            raise WindowError("Window not open")
        if self.__running:
            raise WindowError("SceneWindow already running")
        self.__running = True
        self.__scenes.clear()
        self.__reset_interpolation_data()
        gc.collect()
        on_start_loop: Callable[[], None]
        try:
            self.start_scene(__default_scene, **scene_kwargs)
        except _SceneManager.NewScene as exc:
            exc.actual_scene.on_start_loop_before_transition()
            on_start_loop = exc.actual_scene.on_start_loop
            del exc
        else:
            raise RuntimeError("self.start_scene() didn't raise")
        finally:
            del __default_scene
        loop = self.loop
        process_events = self.handle_events
        update_and_render_scene = self.update_and_render_scene
        refresh_screen = self.refresh
        scene_transition = self.__scene_transition

        try:
            on_start_loop()
            del on_start_loop
            while loop():
                try:
                    process_events()
                    update_and_render_scene(fixed_update=True, interpolation_update=True)
                    refresh_screen()
                except _SceneManager.NewScene as exc:
                    assert exc.previous_scene is not None, "Previous scene must not be None"
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
                    del exc
                    gc.collect()
                    on_start_loop()
                    del on_start_loop
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
        with self.__scenes.closing_scenes(previous_scene, *closing_scenes):
            self.__stop_all_window_callbacks(previous_scene)
            previous_scene.on_quit_before_transition()
            for scene in closing_scenes:
                self.__stop_all_window_callbacks(scene)
                scene.on_quit_before_transition()
            actual_scene.on_start_loop_before_transition()
            if transition_factory is not None:
                renderer = self.renderer
                with renderer.capture(draw_on_default_at_end=False) as previous_scene_surface:
                    self.__scenes._render(previous_scene)
                with renderer.capture(draw_on_default_at_end=False) as actual_scene_surface:
                    self.__scenes._render(actual_scene)
                with renderer.capture(draw_on_default_at_end=True) as window_surface, self.stuck():
                    transition: SceneTransitionCoroutine
                    transition = transition_factory(SurfaceRenderer(window_surface), previous_scene_surface, actual_scene_surface)
                    animating = True
                    try:
                        next(transition)
                    except StopIteration:
                        animating = False
                    next_transition = transition.send
                    next_fixed_transition = lambda: next_transition(None)
                    loop = self.loop
                    refresh = self.refresh
                    while loop() and animating:
                        try:
                            self._fixed_updates_call(next_fixed_transition)
                            self._interpolation_updates_call(next_transition)
                        except StopIteration:
                            animating = False
                        refresh()
                    del loop, refresh
                    del next_fixed_transition, next_transition, transition
        self.__reset_interpolation_data()
        self.clear_all_events()

    def _handle_framerate(self) -> float:
        real_delta_time: float = super()._handle_framerate()
        fixed_framerate: int = self.used_fixed_framerate()
        if fixed_framerate < 1:
            fixed_framerate = self.used_framerate()
        setattr_pv(Time, "fixed_delta", 1 / fixed_framerate if fixed_framerate > 0 else Time.delta())
        self.__compute_interpolation_data(real_delta_time / 1000)
        return real_delta_time

    def _fixed_updates_call(self, *funcs: Callable[[], None]) -> None:
        for _ in range(self.__nb_fixed_update_call):
            for func in funcs:
                func()

    def _interpolation_updates_call(self, *funcs: Callable[[float], None]) -> None:
        alpha: float = self.__alpha_interpolation
        for func in funcs:
            func(alpha)

    def update_and_render_scene(self, *, fixed_update: bool, interpolation_update: bool) -> None:
        scene: Scene | None = self.__scenes.top()
        if scene is None:
            return
        if fixed_update:
            scene_fixed_update = scene.fixed_update
            for _ in range(self.__nb_fixed_update_call):
                scene_fixed_update()
            del scene_fixed_update
        if interpolation_update:
            scene.interpolation_update(self.__alpha_interpolation)
        scene.update()
        self.__scenes._render(scene)

    @final
    def start_scene(
        self,
        __scene: type[Scene],
        /,
        *,
        transition: SceneTransitionProtocol | None = None,
        remove_actual: bool = False,
        **awake_kwargs: Any,
    ) -> NoReturn:
        if not self.__running:
            raise WindowError("Consider using run() to start a first scene")
        if issubclass(__scene, Dialog):
            raise TypeError("start_scene() does not accept Dialogs")
        self.__scenes.go_to(__scene, transition=transition, remove_actual=remove_actual, awake_kwargs=awake_kwargs)

    @final
    def handle_events(self) -> None:
        consume(self.process_events())

    def _process_callbacks(self) -> None:
        super()._process_callbacks()
        actual_scene = self.__scenes.top()
        window_callback_list = self.__callback_after_scenes.get(actual_scene) if actual_scene else None
        if window_callback_list:
            window_callback_list.process()

    def _process_event(self, event: Event) -> bool:
        if self.__event._process_event(event) or super()._process_event(event):
            return True
        actual_scene: Scene | None = self.__scenes.top()
        if actual_scene is None:
            return False
        return actual_scene.handle_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        self.__event._handle_mouse_position(mouse_pos)
        super()._handle_mouse_position(mouse_pos)
        actual_scene: Scene | None = self.__scenes.top()
        if actual_scene is not None:
            actual_scene.handle_mouse_position(mouse_pos)

    def used_framerate(self) -> int:
        for scene in self.__scenes.from_top_to_bottom():
            framerate: int = scene.use_framerate()
            if framerate > 0:
                return framerate
        return super().used_framerate()

    @final
    def get_default_fixed_framerate(self) -> int:
        return self.__default_fixed_framerate

    @final
    def set_default_fixed_framerate(self, value: int) -> None:
        self.__default_fixed_framerate = max(int(value), 0)

    def used_fixed_framerate(self) -> int:
        for scene in self.__scenes.from_top_to_bottom():
            framerate: int = scene.use_fixed_framerate()
            if framerate > 0:
                return framerate
        return self.__default_fixed_framerate

    def get_busy_loop(self) -> bool:
        actual_scene: Scene | None = self.__scenes.top()
        return super().get_busy_loop() or (actual_scene is not None and actual_scene.__class__.require_busy_loop())

    def _remove_window_callback(self, window_callback: WindowCallback) -> None:
        if not isinstance(window_callback, _SceneWindowCallback):
            return super()._remove_window_callback(window_callback)
        scene = window_callback.scene
        scene_callback_after: _WindowCallbackList | None = self.__callback_after_scenes.get(scene)
        if scene_callback_after is None:
            return
        with suppress(ValueError):
            scene_callback_after.remove(window_callback)
            window_callback.kill()
        if not scene_callback_after:
            self.__callback_after_scenes.pop(scene, None)

    def __stop_all_window_callbacks(self, scene: Scene) -> None:
        for window_callback in list(self.__callback_after_scenes.get(scene, ())):
            window_callback.kill()

    def __reset_interpolation_data(self) -> None:
        return self.__compute_interpolation_data(-1)

    def __compute_interpolation_data(self, elapsed_time: float) -> None:
        self.__nb_fixed_update_call = 0
        if elapsed_time < 0:
            self.__accumulator = 0
        else:
            self.__accumulator += elapsed_time
        dt: float = Time.fixed_delta()
        if dt > 0:
            while self.__accumulator >= dt:
                self.__nb_fixed_update_call += 1
                self.__accumulator -= dt
            self.__alpha_interpolation = min(max(self.__accumulator / dt, 0.0), 1.0)
        else:
            self.__alpha_interpolation = 1.0

    @property
    def event(self) -> EventManager:
        return self.__event


from .dialog import Dialog  # Import here because of circular import

_S = TypeVar("_S", bound=Scene)


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

    __theme_initialized: WeakSet[type[Scene]] = WeakSet()
    __scene_manager_attribute: Final[str] = mangle_private_attribute(Scene, "manager")
    __dialog_master_attribute: Final[str] = mangle_private_attribute(Dialog, "master")

    def __init__(self, window: SceneWindow) -> None:
        self.__window: SceneWindow = window
        self.__all_scenes: dict[type[Scene], Scene] = {}
        self.__stack: deque[Scene] = deque()
        self.__returning_transitions: dict[type[Scene], ReturningSceneTransitionProtocol] = {}
        self.__awaken: set[Scene] = set()
        self.__dialogs: deque[Dialog] = deque()

    def __new_scene(self, cls: type[_S]) -> _S:
        if not issubclass(cls, Scene):
            raise TypeError("Bad argument type")
        scene: _S = cls.__new__(cls)
        scene.__dict__[self.__scene_manager_attribute] = self
        if issubclass(cls, Dialog):
            if not self.__stack:
                raise RuntimeError("Trying to open dialog without open scene")
            scene.__dict__[self.__dialog_master_attribute] = self.__dialogs[0] if self.__dialogs else self.__stack[0]
        type(scene).__init__(scene)
        return scene

    def __delete_scene(self, scene: Scene) -> None:
        try:
            stack_quit: ExitStack = getattr_pv(scene, "stack_quit", owner=Scene)
            stack_destroy: ExitStack = getattr_pv(scene, "stack_destroy", owner=Scene)
            with stack_destroy.pop_all():
                try:
                    stack_quit.close()
                finally:
                    type(scene).__del_scene__(scene)
        finally:
            self.__awaken.discard(scene)
            scene_cls = scene.__class__
            if self.__all_scenes.get(scene_cls) is scene:
                self.__all_scenes.pop(scene_cls)

    def __awake_scene(self, scene: Scene, awake_kwargs: dict[str, Any]) -> None:
        scene_cls = scene.__class__
        if scene_cls not in self.__theme_initialized:
            scene_cls.theme_initialize()
            self.__theme_initialized.add(scene_cls)
        scene.awake(**awake_kwargs)
        self.__awaken.add(scene)

    def __exit_scene(self, scene: Scene) -> None:
        stack_quit: ExitStack = getattr_pv(scene, "stack_quit", owner=Scene)
        with stack_quit.pop_all():
            scene.on_quit()

    @contextmanager
    def closing_scenes(self, *scenes: Scene) -> Iterator[None]:
        if tuple(set(scenes)) != scenes:
            raise ValueError("Duplicates found")
        with ExitStack() as stack:
            for scene in scenes:
                if not self.started(scene):
                    stack.callback(self.__delete_scene, scene)
                stack.callback(self.__exit_scene, scene)
            yield

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
        all_scenes = list(self.from_top_to_bottom())
        self.__dialogs.clear()
        self.__stack.clear()
        self.__returning_transitions.clear()
        with self.closing_scenes(*all_scenes):
            pass

    def render(self, scene_cls: type[Scene]) -> None:
        if issubclass(scene_cls, Dialog):
            raise TypeError("Trying to draw a Dialog scene")
        try:
            scene = self.__all_scenes[scene_cls]
            if not self.started(scene):
                raise KeyError(scene_cls)
        except KeyError:
            raise RuntimeError("Scene not started") from None
        if not self.is_awaken(scene):
            raise RuntimeError("Trying to draw non-awaken scene")
        if self.top() is scene:
            raise RuntimeError("Trying to draw actual looping scene")
        self._render(scene, fill_background_color=False)

    def _render(self, scene: Scene, *, fill_background_color: bool = True) -> None:
        if self._is_dialog(scene):
            self._render(scene.master, fill_background_color=fill_background_color)
            self.window.clear(scene.background_color, blend_alpha=True)
        elif fill_background_color:
            self.window.clear(scene.background_color)
        scene.render()

    def go_to(
        self,
        scene_cls: type[Scene],
        *,
        transition: SceneTransitionProtocol | None = None,
        remove_actual: bool = False,
        awake_kwargs: dict[str, Any] | None = None,
    ) -> NoReturn:
        if not isconcreteclass(scene_cls):
            raise TypeError(f"{scene_cls.__name__} is an abstract class")
        if issubclass(scene_cls, Dialog):
            raise TypeError(f"{scene_cls.__name__} must be open with open_dialog()")
        if awake_kwargs is None:
            awake_kwargs = {}
        stack = self.__stack
        actual_scene = stack[0] if stack else None
        try:
            next_scene = self.__all_scenes[scene_cls]
        except KeyError:
            self.__all_scenes[scene_cls] = next_scene = self.__new_scene(scene_cls)
            self.__awake_scene(next_scene, awake_kwargs)
        else:
            if actual_scene is next_scene:
                raise _SceneManager.SameScene(actual_scene)
            assert self.is_awaken(next_scene)
            next_scene.on_restart(**awake_kwargs)
        scene_transition: Callable[[AbstractRenderer, Surface, Surface], SceneTransitionCoroutine] | None = None
        closing_scenes: list[Scene] = []
        if actual_scene is None or next_scene not in stack:
            stack.insert(0, next_scene)
            if actual_scene is not None:
                if isinstance(transition, ReturningSceneTransitionProtocol):
                    self.__returning_transitions[actual_scene.__class__] = transition
                if transition is not None:
                    scene_transition = transition.show_new_scene
                if remove_actual:
                    stack.remove(actual_scene)
        else:
            returning_transition = self.__returning_transitions.pop(scene_cls, None)
            while stack[0] is not next_scene:
                closed_scene = stack.popleft()
                if closed_scene is not actual_scene:
                    closing_scenes.append(closed_scene)
                self.__returning_transitions.pop(closed_scene.__class__, None)
            if returning_transition is not None:
                scene_transition = returning_transition.hide_actual_scene
            elif transition is not None:
                scene_transition = (
                    transition.hide_actual_scene
                    if isinstance(transition, ReturningSceneTransitionProtocol)
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
        dialog_cls: type[Dialog],
        *,
        awake_kwargs: dict[str, Any] | None = None,
    ) -> None:
        if not isconcreteclass(dialog_cls):
            raise TypeError(f"{dialog_cls.__name__} is an abstract class")
        if not issubclass(dialog_cls, Dialog):
            raise TypeError(f"{dialog_cls.__name__} must be open with go_to()")
        if awake_kwargs is None:
            awake_kwargs = {}

        dialog = self.__new_scene(dialog_cls)
        dialogs_stack = self.__dialogs

        with ExitStack() as exit_stack:
            exit_stack.callback(self.__delete_scene, dialog)
            dialogs_stack.insert(0, dialog)
            exit_stack.callback(dialogs_stack.remove, dialog)
            self.__awake_scene(dialog, awake_kwargs)
            exit_stack.callback(self.__exit_scene, dialog)

            window = self.window
            dialog.on_start_loop_before_transition()
            with window.stuck():
                dialog.run_start_transition()

            try:
                dialog.on_start_loop()
                while window.loop():
                    window.handle_events()
                    window.update_and_render_scene(fixed_update=True, interpolation_update=True)
                    window.refresh()
            except _SceneManager.DialogStop:
                dialog.on_quit_before_transition()
                with window.stuck():
                    dialog.run_quit_transition()

    def _is_dialog(self, scene: Scene) -> TypeGuard[Dialog]:
        return scene in self.__dialogs

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
