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
]

from abc import abstractmethod
from contextlib import ExitStack, suppress
from enum import auto, unique
from inspect import isgeneratorfunction
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
    TypeVar,
    overload,
    runtime_checkable,
)

from typing_extensions import final

from ..graphics.color import Color
from ..graphics.renderer import AbstractRenderer
from ..graphics.surface import Surface
from ..system.object import Object
from ..system.theme import ClassWithThemeNamespaceMeta, no_theme_decorator
from ..system.utils.abc import concreteclassmethod, isabstractclass
from ..system.utils.contextlib import ExitStackView
from ..system.utils.enum import AutoLowerNameEnum
from ..system.utils.functools import wraps
from ..window.event import Event, EventManager

if TYPE_CHECKING:
    from ..window.display import WindowCallback
    from .dialog import Dialog
    from .window import SceneWindow, _SceneManager

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
        if not isabstractclass(cls):
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
            self.__manager
        except AttributeError:
            raise TypeError(f"Trying to instantiate {self.__class__.__name__!r} scene outside a SceneWindow manager") from None

        self.__event: EventManager = EventManager()
        self.__bg_color: Color = Color(0, 0, 0)
        self.__stack_quit: ExitStack = ExitStack()
        self.__stack_destroy: ExitStack = ExitStack()

    @classmethod
    def __theme_init__(cls) -> None:
        pass

    @no_theme_decorator
    def __del_scene__(self) -> None:
        with self.__stack_destroy, ExitStack() as stack:
            stack.callback(self.__dict__.clear)
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
        from .dialog import Dialog

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
            from .window import _SceneWindowCallback

            window_callback: WindowCallback = _SceneWindowCallback(self, __milliseconds, __callback, args, kwargs)
            self.__manager.window.register_window_callback(window_callback)
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
            from .window import _SceneWindowCallback

            window_callback: WindowCallback

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

            self.__manager.window.register_window_callback(window_callback)
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
        if not isabstractclass(cls):
            cls.set_closed_theme_namespace()
