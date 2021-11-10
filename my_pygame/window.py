# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import abstractmethod
from functools import wraps
from inspect import isgeneratorfunction
from types import MethodType
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    NoReturn,
    Optional,
    Protocol,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)
from enum import IntEnum
from operator import truth

import pygame
import pygame.display
import pygame.event
import pygame.mixer
import pygame.time

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.color import Color
from pygame.time import get_ticks

from .renderer import Renderer, SurfaceRenderer
from .event import EventManager, Event, MetaEvent, UnknownEventTypeError
from .text import Text
from .colors import BLACK, WHITE
from .scene import Scene, WindowCallback, _WindowCallbackList
from .clock import Clock
from .surface import create_surface
from .mouse import Mouse
from .keyboard import Keyboard
from .cursor import Cursor, SystemCursor
from .theme import NoTheme

__ignore_imports__: Tuple[str, ...] = tuple(globals())

_EventType = int

_ColorInput = Union[Color, str, List[int], Tuple[int, int, int], Tuple[int, int, int, int]]

_ScheduledFunc = TypeVar("_ScheduledFunc", bound=Callable[..., None])


class _SupportsDrawing(Protocol):
    @abstractmethod
    def draw_onto(self, /, target: Renderer) -> None:
        raise NotImplementedError


class WindowError(pygame.error):
    pass


class _SceneTransitionEnum(IntEnum):
    SHOW = 1
    HIDE = 2


class ScheduledFunction(Generic[_ScheduledFunc]):
    def __init__(self, /, milliseconds: float, func: _ScheduledFunc) -> None:
        super().__init__()
        self.__clock = Clock()
        self.__milliseconds: float = milliseconds
        self.__func__: _ScheduledFunc = func

    def __call__(self, /, *args: Any, **kwargs: Any) -> None:
        func: _ScheduledFunc = self.__func__
        if self.__clock.elapsed_time(self.__milliseconds):
            func(*args, **kwargs)

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Callable[..., None]:
        if obj is None:
            return self
        return MethodType(self, obj)


def scheduled(milliseconds: float) -> Callable[[_ScheduledFunc], _ScheduledFunc]:
    def decorator(func: _ScheduledFunc, /) -> _ScheduledFunc:
        return cast(_ScheduledFunc, ScheduledFunction(milliseconds, func))

    return decorator


class Window(EventManager):
    class Exit(BaseException):
        pass

    Config = Dict[str, Any]

    DEFAULT_TITLE = "pygame window"
    DEFAULT_FRAMERATE = 60

    __main_window: bool = True
    __default_cursor: Cursor = SystemCursor.CURSOR_ARROW
    __cursor: Cursor = __default_cursor

    def __new__(cls, /, *args: Any, **kwargs: Any) -> Any:
        if not Window.__main_window:
            raise WindowError("Cannot have multiple open windows")
        Window.__main_window = False
        return super().__new__(cls)

    def __init__(self, /, title: Optional[str] = None, size: Tuple[int, int] = (0, 0), fullscreen: bool = False) -> None:
        super().__init__()
        self.set_title(title)
        size = (max(size[0], 0), max(size[1], 0))
        flags: int = 0
        if fullscreen:
            flags |= pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
        screen: Surface = pygame.display.set_mode(size, flags=flags)
        self.__surface: Surface = create_surface(screen.get_size())
        self.__rect: Rect = self.__surface.get_rect()
        self.clear_all_events()

        self.__main_clock: _FramerateManager = _FramerateManager()

        self.__framerate_update_clock: Clock = Clock(start=True)
        self.__default_framerate: int = Window.DEFAULT_FRAMERATE
        self.__busy_loop: bool = False
        self.__text_framerate: Text = Text(color=WHITE, theme=NoTheme)
        self.__text_framerate.hide()
        self.__text_framerate.midtop = (self.centerx, self.top + 10)

        self.__loop: bool = True
        self.__scenes: _SceneManager = _SceneManager(self)
        self.__actual_scene: Optional[Scene] = None
        self.__transition: _SceneTransitionEnum = _SceneTransitionEnum.SHOW

        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__callback_after_scenes: Dict[Scene, _WindowCallbackList] = dict()

    def __del__(self, /) -> None:
        Window.__main_window = True

    def __contains__(self, /, scene: Scene) -> bool:
        return scene in self.__scenes

    def set_title(self, /, title: Optional[str]) -> None:
        pygame.display.set_caption(title or Window.DEFAULT_TITLE)

    def iconify(self, /) -> bool:
        return truth(pygame.display.iconify())

    def mainloop(self, /) -> None:
        try:
            self.__loop = True
            while self.is_open():
                Window.__cursor.set()
                Window.__cursor = Window.__default_cursor
                self.handle_events()
                self.update()
                self.draw_and_refresh()
        except Window.Exit:
            pass
        finally:
            self.__loop = False
            self.__callback_after.clear()
            self.__callback_after_scenes.clear()
            for scene in self.__scenes.from_top_to_bottom():
                scene.on_quit()

    def close(self, /) -> NoReturn:
        self.__loop = False
        raise Window.Exit

    def is_open(self, /) -> bool:
        return self.__loop

    def clear(self, /, color: _ColorInput = BLACK) -> None:
        self.__surface.fill(color)

    def get_default_framerate(self, /) -> int:
        return self.__default_framerate

    def set_default_framerate(self, /, value: int) -> None:
        self.__default_framerate = max(int(value), 0)

    def set_busy_loop(self, /, status: bool) -> None:
        self.__busy_loop = truth(status)

    def refresh(self, /) -> None:
        screen: Surface = pygame.display.get_surface()
        screen.fill(BLACK)
        text_framerate: Text = self.__text_framerate
        if text_framerate.is_shown():
            if not text_framerate.message or self.__framerate_update_clock.elapsed_time(200):
                text_framerate.message = f"{round(self.framerate)} FPS"
            self.draw(self.text_framerate)
        screen.blit(self.__surface, (0, 0))
        pygame.display.flip()

        framerate: int = self.__default_framerate
        actual_scene: Optional[Scene] = self.__scenes.top()
        for scene in self.__scenes.from_bottom_to_top():
            f: int = scene.get_required_framerate()
            if f > 0:
                framerate = f
                break
        if framerate == 0:
            self.__main_clock.tick()
        elif self.__busy_loop or (actual_scene is not None and actual_scene.require_busy_loop()):
            self.__main_clock.tick_busy_loop(framerate)
        else:
            self.__main_clock.tick(framerate)

    def draw_screen(self, /) -> None:
        scene: Optional[Scene] = self.__update_actual_scene()
        if scene:
            if scene.master:
                scene.master.draw()
            else:
                self.clear(scene.background_color)
            scene.draw()

    def update(self, /) -> None:
        scene: Optional[Scene] = self.__update_actual_scene()
        if scene:
            scene.update()

    def draw_and_refresh(self, /) -> None:
        self.draw_screen()
        self.refresh()

    def draw(self, /, target: _SupportsDrawing, *targets: _SupportsDrawing) -> None:
        surface: Surface = self.__surface
        renderer: SurfaceRenderer = SurfaceRenderer(surface)

        def draw_target(target: _SupportsDrawing) -> None:
            try:
                target.draw_onto(renderer)
            except pygame.error:
                pass

        draw_target(target)
        for t in targets:
            draw_target(t)

    def handle_events(self, /) -> None:
        Keyboard.update()
        Mouse.update()

        self.__callback_after.process()
        actual_scene: Optional[Scene] = self.__update_actual_scene()
        if actual_scene:
            try:
                self.__callback_after_scenes[actual_scene].process()
            except KeyError:
                pass

        self.handle_mouse_pos()
        if actual_scene:
            actual_scene.handle_mouse_pos()
        self.__handle_all_events(actual_scene)

    def __handle_all_events(self, /, actual_scene: Optional[Scene]) -> None:
        scene_handler: Optional[Callable[[Event], None]] = actual_scene.process_event if actual_scene is not None else None
        for pg_event in pygame.event.get():
            try:
                event = MetaEvent.from_pygame_event(pg_event)
            except UnknownEventTypeError:
                continue
            self.process_event(event)
            if scene_handler:
                scene_handler(event)
            if event.type == Event.Type.QUIT:
                self.close()

    def set_temporary_window_cursor(self, /, cursor: Cursor) -> None:
        if isinstance(cursor, Cursor):
            Window.__cursor = cursor

    def set_window_cursor(self, /, cursor: Cursor) -> None:
        if isinstance(cursor, Cursor):
            Window.__cursor = Window.__default_cursor = cursor

    def allow_only_event(self, /, *event_types: _EventType) -> None:
        pygame.event.set_allowed(event_types)

    def allow_all_events(self, /) -> None:
        pygame.event.set_allowed(None)

    def clear_all_events(self, /) -> None:
        pygame.event.clear()

    def block_only_event(self, /, *event_types: _EventType) -> None:
        pygame.event.set_blocked(event_types)

    def after(self, /, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        window_callback: WindowCallback = WindowCallback(self, milliseconds, callback, args, kwargs)
        self.__callback_after.append(window_callback)
        return window_callback

    @overload
    def every(self, /, milliseconds: float, callback: Callable[..., None], *args: Any, **kwargs: Any) -> WindowCallback:
        ...

    @overload
    def every(self, /, milliseconds: float, callback: Callable[..., Iterator[None]], *args: Any, **kwargs: Any) -> WindowCallback:
        ...

    def every(self, /, milliseconds: float, callback: Callable[..., Any], *args: Any, **kwargs: Any) -> WindowCallback:
        window_callback: WindowCallback

        if isgeneratorfunction(callback):
            generator: Iterator[None] = callback(*args, **kwargs)

            @wraps(callback)
            def wrapper() -> None:
                try:
                    next(generator)
                except ValueError:
                    pass
                except StopIteration:
                    window_callback.kill()

            window_callback = WindowCallback(self, milliseconds, wrapper)

        else:
            window_callback = WindowCallback(self, milliseconds, callback, args, kwargs, loop=True)
        self.__callback_after.append(window_callback)
        return window_callback

    def remove_window_callback(self, /, window_callback: WindowCallback) -> None:
        scene: Optional[Scene] = window_callback.scene
        if scene is not None:
            scene_callback_after: Optional[_WindowCallbackList] = self.__callback_after_scenes.get(scene)
            if scene_callback_after is None:
                return
            try:
                scene_callback_after.remove(window_callback)
            except ValueError:
                pass
            if not scene_callback_after:
                self.__callback_after_scenes.pop(scene)
        else:
            try:
                self.__callback_after.remove(window_callback)
            except ValueError:
                pass

    def get_actual_scene(self, /) -> Optional[Scene]:
        return self.__scenes.top()

    def __check_scene(self, /, scene: Scene) -> None:
        if scene.window is not self:
            raise WindowError(f"{type(scene).__name__}: Trying to deal with a scene bound to an another window")

    def start_scene(self, /, scene: Scene) -> None:
        self.__check_scene(scene)
        if scene.looping():
            return
        transition: _SceneTransitionEnum = _SceneTransitionEnum.SHOW
        try:
            self.__scenes.clear(until=scene)
        except WindowError:
            self.__scenes.push(scene)
        if self.__actual_scene is None or self.__actual_scene is scene:
            return
        if self.__actual_scene not in self.__scenes:
            transition = _SceneTransitionEnum.HIDE
        self.__transition = transition

    def stop_scene(self, /, scene: Scene) -> None:
        self.__check_scene(scene)
        if scene.looping():
            self.__transition = _SceneTransitionEnum.HIDE
        self.__scenes.remove(scene)
        self.__callback_after_scenes.pop(scene, None)

    def __update_actual_scene(self, /) -> Optional[Scene]:
        actual_scene: Optional[Scene] = self.__scenes.top()
        previous_scene: Optional[Scene] = self.__actual_scene
        if actual_scene is not previous_scene:
            self.__actual_scene = actual_scene
            if actual_scene is None:
                if previous_scene is not None:
                    previous_scene.on_quit()
            elif previous_scene is None:
                actual_scene.on_start_loop()
            else:
                previous_scene.on_quit()
                actual_scene.on_start_loop()
                if self.__transition == _SceneTransitionEnum.SHOW and previous_scene.transition is not None:
                    previous_scene.transition.show_new_scene(previous_scene, actual_scene)
                elif self.__transition == _SceneTransitionEnum.HIDE and actual_scene.transition is not None:
                    actual_scene.transition.hide_actual_scene(previous_scene, actual_scene)
        return actual_scene

    @property
    def framerate(self, /) -> float:
        return self.__main_clock.get_fps()

    @property
    def text_framerate(self, /) -> Text:
        return self.__text_framerate

    @property
    def rect(self, /) -> Rect:
        return self.__rect.copy()

    @property
    def left(self, /) -> int:
        return self.__rect.left

    @property
    def right(self, /) -> int:
        return self.__rect.right

    @property
    def top(self, /) -> int:
        return self.__rect.top

    @property
    def bottom(self, /) -> int:
        return self.__rect.bottom

    @property
    def size(self, /) -> Tuple[int, int]:
        return self.__rect.size

    @property
    def width(self, /) -> int:
        return self.__rect.width

    @property
    def height(self, /) -> int:
        return self.__rect.height

    @property
    def center(self, /) -> Tuple[int, int]:
        return self.__rect.center

    @property
    def centerx(self, /) -> int:
        return self.__rect.centerx

    @property
    def centery(self, /) -> int:
        return self.__rect.centery

    @property
    def topleft(self, /) -> Tuple[int, int]:
        return self.__rect.topleft

    @property
    def topright(self, /) -> Tuple[int, int]:
        return self.__rect.topright

    @property
    def bottomleft(self, /) -> Tuple[int, int]:
        return self.__rect.bottomleft

    @property
    def bottomright(self, /) -> Tuple[int, int]:
        return self.__rect.bottomright

    @property
    def midtop(self, /) -> Tuple[int, int]:
        return self.__rect.midtop

    @property
    def midbottom(self, /) -> Tuple[int, int]:
        return self.__rect.midbottom

    @property
    def midleft(self, /) -> Tuple[int, int]:
        return self.__rect.midleft

    @property
    def midright(self, /) -> Tuple[int, int]:
        return self.__rect.midright


class _FramerateManager:
    def __init__(self, /) -> None:
        self.__fps: float = 0
        self.__fps_count: int = 0
        self.__fps_tick: int = get_ticks()
        self.__last_tick: int = self.__fps_tick

    def __tick_impl(self, /, framerate: int, use_accurate_delay: bool) -> None:
        if framerate > 0:
            tick_time: int = round(1000 / framerate)
            elapsed: int = get_ticks() - self.__last_tick
            if elapsed < tick_time:
                delay: int = tick_time - elapsed
                if use_accurate_delay:
                    pygame.time.delay(delay)
                else:
                    pygame.time.wait(delay)

        self.__last_tick = get_ticks()
        self.__fps_count += 1
        if self.__fps_count >= 10:
            self.__fps = self.__fps_count / ((get_ticks() - self.__fps_tick) / 1000.0)
            self.__fps_count = 0
            self.__fps_tick = get_ticks()

    def tick(self, /, framerate: int = 0) -> None:
        return self.__tick_impl(framerate, False)

    def tick_busy_loop(self, /, framerate: int = 0) -> None:
        return self.__tick_impl(framerate, True)

    def get_fps(self, /) -> float:
        return self.__fps


class _SceneManager:
    def __init__(self, /, window: Window) -> None:
        self.__stack: List[Scene] = []
        self.__window: Window = window

    def __iter__(self, /) -> Iterator[Scene]:
        return self.from_top_to_bottom()

    def __len__(self, /) -> int:
        return len(self.__stack)

    def __contains__(self, /, scene: Scene) -> bool:
        if scene.window is not self.__window:
            return False
        return scene in self.__stack

    def from_top_to_bottom(self, /) -> Iterator[Scene]:
        return iter(self.__stack)

    def from_bottom_to_top(self, /) -> Iterator[Scene]:
        return iter(reversed(self.__stack))

    def empty(self, /) -> bool:
        return not self.__stack

    def top(self, /) -> Optional[Scene]:
        return self.__stack[0] if self.__stack else None

    def index(self, /, scene: Scene) -> int:
        return self.__stack.index(scene)

    def clear(self, /, until: Optional[Scene] = None) -> None:
        if until is None:
            self.__stack.clear()
            return
        if until not in self:
            raise WindowError(f"{type(until).__name__} not stacked")
        while self.__stack[0] is not until:
            self.__stack.pop(0)

    def remove(self, /, scene: Scene) -> None:
        if scene.window is not self.__window:
            raise WindowError("Trying to remove a scene bound to an another window")
        try:
            self.__stack.remove(scene)
        except ValueError:
            pass

    def push(self, /, scene: Scene) -> None:
        if scene.window is not self.__window:
            raise WindowError("Trying to push a scene bound to an another window")
        self.remove(scene)
        if any(type(stacked_scene) is type(scene) for stacked_scene in self):
            raise TypeError(f"A scene with the same type is stacked: {type(scene).__name__}")
        self.__stack.insert(0, scene)


__all__ = [n for n in globals() if not n.startswith("_") and n not in __ignore_imports__]
