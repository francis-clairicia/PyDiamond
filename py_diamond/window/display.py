# -*- coding: Utf-8 -*

from __future__ import annotations

__all__ = ["WindowError", "ScheduledFunction", "scheduled", "Window", "WindowCallback"]

from abc import abstractmethod
from contextlib import ExitStack, contextmanager, suppress
from inspect import isgeneratorfunction
from operator import truth
from types import MethodType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Final,
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
    final,
    overload,
)

import pygame
import pygame.display
import pygame.event
import pygame.mixer

from .cursor import Cursor
from .event import EventManager, Event, MetaEvent, UnknownEventTypeError
from ..graphics.color import Color, BLACK, WHITE
from ..graphics.rect import Rect
from ..graphics.renderer import Renderer, SurfaceRenderer
from ..graphics.surface import Surface, create_surface
from ..graphics.text import Text
from ..graphics.theme import NoTheme
from .keyboard import Keyboard
from .mouse import Mouse
from ..system.clock import Clock
from ..system.time import Time
from ..system.utils import wraps

_EventType = int

_ColorInput = Union[Color, str, List[int], Tuple[int, int, int], Tuple[int, int, int, int]]

_ScheduledFunc = TypeVar("_ScheduledFunc", bound=Callable[..., None])


class _SupportsDrawing(Protocol):
    @abstractmethod
    def draw_onto(self, /, target: Renderer) -> None:
        raise NotImplementedError


class WindowError(pygame.error):
    pass


class ScheduledFunction(Generic[_ScheduledFunc]):
    def __init__(self, /, milliseconds: float, func: _ScheduledFunc) -> None:
        super().__init__()
        self.__clock = Clock()
        self.__milliseconds: float = milliseconds
        self.__func__: _ScheduledFunc = func
        self.__first_start: bool = True

    def __call__(self, /, *args: Any, **kwargs: Any) -> None:
        func: _ScheduledFunc = self.__func__
        if self.__first_start or self.__clock.elapsed_time(self.__milliseconds):
            self.__first_start = False
            func(*args, **kwargs)

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Callable[..., None]:
        if obj is None:
            return self
        return MethodType(self, obj)


def scheduled(milliseconds: float) -> Callable[[_ScheduledFunc], _ScheduledFunc]:
    def decorator(func: _ScheduledFunc, /) -> _ScheduledFunc:
        return cast(_ScheduledFunc, ScheduledFunction(milliseconds, func))

    return decorator


class Window:
    class Exit(BaseException):
        pass

    Config = Dict[str, Any]

    DEFAULT_TITLE: Final[str] = "PyDiamond window"
    DEFAULT_FRAMERATE: Final[int] = 60

    __main_window: ClassVar[bool] = True

    def __new__(cls, /, *args: Any, **kwargs: Any) -> Any:
        if not Window.__main_window:
            raise WindowError("Cannot have multiple open windows")
        Window.__main_window = False
        return super().__new__(cls)

    def __init__(self, /, title: Optional[str] = None, size: Tuple[int, int] = (0, 0), fullscreen: bool = False) -> None:
        super().__init__()
        self.set_title(title)
        self.__size: Tuple[int, int] = (max(size[0], 0), max(size[1], 0))
        self.__flags: int = 0
        if fullscreen:
            self.__flags |= pygame.FULLSCREEN | pygame.DOUBLEBUF | pygame.HWSURFACE
            self.__size = (0, 0)
        self.__surface: Surface = Surface((0, 0))
        self.__rect: Rect = self.__surface.get_rect()

        self.__event_buffer: List[pygame.event.Event] = []
        self.__main_clock: _FramerateManager = _FramerateManager()
        self.__event: EventManager = EventManager()

        self.__framerate_update_clock: Clock = Clock(start=True)
        self.__default_framerate: int = Window.DEFAULT_FRAMERATE
        self.__busy_loop: bool = False
        self.__text_framerate: Text = Text(color=WHITE, theme=NoTheme)
        self.__text_framerate.hide()

        self.__loop: bool = False
        self.__callback_after: _WindowCallbackList = _WindowCallbackList()

    def __window_init__(self, /) -> None:
        self.__text_framerate.midtop = (self.centerx, self.top + 10)

    def __del__(self, /) -> None:
        Window.__main_window = True

    __W = TypeVar("__W", bound="Window")

    @contextmanager
    def open(self: __W, /) -> Iterator[__W]:
        def clear_window_callbacks() -> None:
            self.__loop = False
            self.__callback_after.clear()
            self.__event_buffer.clear()
            self.__surface = Surface((0, 0))
            self.__rect = self.__surface.get_rect()

        with ExitStack() as stack:
            pygame.display.init()
            stack.callback(pygame.display.quit)
            size = self.__size
            flags = self.__flags
            screen: Surface = pygame.display.set_mode(size, flags=flags)
            self.__surface = create_surface(screen.get_size())
            self.__rect = self.__surface.get_rect()
            stack.callback(clear_window_callbacks)
            self.__window_init__()
            self.__loop = True
            with suppress(Window.Exit):
                yield self

    def set_title(self, /, title: Optional[str]) -> None:
        pygame.display.set_caption(title or Window.DEFAULT_TITLE)

    def iconify(self, /) -> bool:
        return truth(pygame.display.iconify())

    @final
    def close(self, /) -> NoReturn:
        self.__loop = False
        raise Window.Exit

    @final
    def is_open(self, /) -> bool:
        return self.__loop

    def clear(self, /, color: _ColorInput = BLACK) -> None:
        self.__surface.fill(color)

    def get_default_framerate(self, /) -> int:
        return self.__default_framerate

    def set_default_framerate(self, /, value: int) -> None:
        self.__default_framerate = max(int(value), 0)

    def used_framerate(self, /) -> int:
        return self.__default_framerate

    def get_busy_loop(self, /) -> bool:
        return self.__busy_loop

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
        Cursor.update()
        pygame.display.flip()

        framerate: int = self.used_framerate()
        if framerate <= 0:
            self.__main_clock.tick()
        elif self.get_busy_loop():
            self.__main_clock.tick_busy_loop(framerate)
        else:
            self.__main_clock.tick(framerate)

    def draw(self, /, *targets: _SupportsDrawing) -> None:
        surface: Surface = self.__surface
        renderer: SurfaceRenderer = SurfaceRenderer(surface)

        for target in targets:
            with suppress(pygame.error):
                target.draw_onto(renderer)

    def handle_events(self, /) -> List[Event]:
        return [event for event in self.process_events()]

    def _process_callbacks(self, /) -> None:
        self.__callback_after.process()

    def process_events(self, /) -> Iterator[Event]:
        Keyboard.update()
        Mouse.update()
        self._process_callbacks()

        buffer = self.__event_buffer
        buffer.extend(pygame.event.get())
        while buffer:
            pg_event = buffer.pop(0)
            if pg_event.type == pygame.QUIT:
                self.close()
            try:
                event = MetaEvent.from_pygame_event(pg_event)
            except UnknownEventTypeError:
                continue
            self.event.process_event(event)
            yield event

        self.event.handle_mouse_position()

    def allow_only_event(self, /, *event_types: _EventType) -> None:
        pygame.event.set_allowed(event_types)

    def allow_all_events(self, /) -> None:
        pygame.event.set_allowed(None)

    def clear_all_events(self, /) -> None:
        pygame.event.clear()
        self.__event_buffer.clear()

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

            window_callback = WindowCallback(self, milliseconds, wrapper, loop=True)
        else:
            window_callback = WindowCallback(self, milliseconds, callback, args, kwargs, loop=True)
        self.__callback_after.append(window_callback)
        return window_callback

    def remove_window_callback(self, /, window_callback: WindowCallback) -> None:
        with suppress(ValueError):
            self.__callback_after.remove(window_callback)

    @property
    def framerate(self, /) -> float:
        return self.__main_clock.get_fps()

    @property
    def text_framerate(self, /) -> Text:
        return self.__text_framerate

    @property
    def event(self, /) -> EventManager:
        return self.__event

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
        self.__fps_tick: int = Time.get_ticks()
        self.__last_tick: int = self.__fps_tick

    def __tick_impl(self, /, framerate: int, use_accurate_delay: bool) -> None:
        actual_tick: int = Time.get_ticks()
        last_tick, self.__last_tick = self.__last_tick, actual_tick

        self.__fps_count += 1
        if self.__fps_count >= 10:
            self.__fps = self.__fps_count / ((actual_tick - self.__fps_tick) / 1000.0)
            self.__fps_count = 0
            self.__fps_tick = actual_tick

        if framerate > 0:
            tick_time: int = round(1000 / framerate)
            elapsed: int = actual_tick - last_tick
            if elapsed < tick_time:
                delay: int = tick_time - elapsed
                if use_accurate_delay:
                    Time.delay(delay)
                else:
                    Time.wait(delay)

    def tick(self, /, framerate: int = 0) -> None:
        return self.__tick_impl(framerate, False)

    def tick_busy_loop(self, /, framerate: int = 0) -> None:
        return self.__tick_impl(framerate, True)

    def get_fps(self, /) -> float:
        return self.__fps


class WindowCallback:
    def __init__(
        self,
        /,
        master: Window,
        wait_time: float,
        callback: Callable[..., None],
        args: Tuple[Any, ...] = (),
        kwargs: Dict[str, Any] = {},
        loop: bool = False,
    ) -> None:
        self.__master: Window = master
        self.__wait_time: float = wait_time
        self.__callback: Callable[..., None] = callback
        self.__args: Tuple[Any, ...] = args
        self.__kwargs: Dict[str, Any] = kwargs
        self.__clock = Clock(start=True)
        self.__loop: bool = bool(loop)

    def __call__(self, /) -> None:
        loop: bool = self.__loop
        if self.__clock.elapsed_time(self.__wait_time, restart=loop):
            self.__callback(*self.__args, **self.__kwargs)
            if not loop:
                self.kill()

    def kill(self, /) -> None:
        self.__master.remove_window_callback(self)


class _WindowCallbackList(List[WindowCallback]):
    def process(self, /) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()
