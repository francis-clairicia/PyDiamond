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

from ..graphics.color import BLACK, WHITE, Color
from ..graphics.rect import Rect, pg_rect_convert
from ..graphics.renderer import Renderer, SurfaceRenderer
from ..graphics.surface import Surface, create_surface
from ..graphics.text import Text
from ..graphics.theme import NoTheme
from ..system.clock import Clock
from ..system.mangling import mangle_private_attribute
from ..system.time import Time
from ..system.utils import wraps
from .cursor import Cursor
from .event import Event, EventManager, UnknownEventTypeError
from .keyboard import Keyboard
from .mouse import Mouse

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
    DEFAULT_FIXED_FRAMERATE: Final[int] = 50

    __main_window: ClassVar[bool] = True

    def __new__(cls, /, *args: Any, **kwargs: Any) -> Any:
        if not Window.__main_window:
            raise WindowError("Cannot have multiple open windows")
        Window.__main_window = False
        return super().__new__(cls)

    def __init__(
        self, /, title: Optional[str] = None, size: Tuple[int, int] = (0, 0), fullscreen: bool = False, vsync: bool = True
    ) -> None:
        super().__init__()
        self.set_title(title)
        self.__size: Tuple[int, int] = (max(size[0], 0), max(size[1], 0))
        self.__flags: int = 0
        if fullscreen:
            self.__flags |= pygame.FULLSCREEN
            self.__size = (0, 0)
        self.__vsync: bool = bool(vsync)
        self.__surface: Surface = Surface((0, 0))
        self.__rect: Rect = pg_rect_convert(self.__surface.get_rect())

        self.__event_buffer: List[pygame.event.Event] = []
        self.__main_clock: _FramerateManager = _FramerateManager()
        self.__event: EventManager = EventManager()

        self.__framerate_update_clock: Clock = Clock(start=True)
        self.__default_framerate: int = self.DEFAULT_FRAMERATE
        self.__default_fixed_framerate: int = self.DEFAULT_FIXED_FRAMERATE
        self.__busy_loop: bool = False

        self.__loop: bool = False
        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__process_callbacks: bool = True

    def __window_init__(self, /) -> None:
        pass

    def __window_quit__(self, /) -> None:
        pass

    def __del__(self, /) -> None:
        Window.__main_window = True

    __W = TypeVar("__W", bound="Window")

    @contextmanager
    def open(self: __W, /) -> Iterator[__W]:
        if self.__loop:
            raise WindowError("Trying to open already opened window")

        def cleanup() -> None:
            self.__window_quit__()
            del self.__text_framerate
            self.__loop = False
            self.__callback_after.clear()
            self.__event_buffer.clear()
            self.__surface = Surface((0, 0))
            self.__rect = pg_rect_convert(self.__surface.get_rect())
            self.__event.unbind_all()

        self.__event.unbind_all()
        with ExitStack() as stack, suppress(Window.Exit):
            pygame.display.init()
            stack.callback(pygame.display.quit)
            size = self.__size
            flags = self.__flags
            vsync = int(truth(self.__vsync))
            screen: Surface = pygame.display.set_mode(size, flags=flags, vsync=vsync)
            self.__surface = create_surface(screen.get_size())
            self.__rect = pg_rect_convert(self.__surface.get_rect())
            stack.callback(cleanup)
            self.__text_framerate: Text = Text(color=WHITE, theme=NoTheme)
            self.__text_framerate.hide()
            self.__text_framerate.midtop = (self.centerx, self.top + 10)
            self.__window_init__()
            self.__main_clock.tick()
            self.__loop = True
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

    def get_default_fixed_framerate(self, /) -> int:
        return self.__default_fixed_framerate

    def set_default_fixed_framerate(self, /, value: int) -> None:
        self.__default_fixed_framerate = max(int(value), 0)

    def used_fixed_framerate(self, /) -> int:
        return self.__default_fixed_framerate

    def get_busy_loop(self, /) -> bool:
        return self.__busy_loop

    def set_busy_loop(self, /, status: bool) -> None:
        self.__busy_loop = truth(status)

    def refresh(self, /) -> float:
        screen = SurfaceRenderer(pygame.display.get_surface())
        text_framerate: Text = self.__text_framerate
        screen.draw(self.__surface, (0, 0))
        if text_framerate.is_shown():
            if not text_framerate.message or self.__framerate_update_clock.elapsed_time(200):
                text_framerate.message = f"{round(self.framerate)} FPS"
            self.text_framerate.draw_onto(screen)
        Cursor.update()
        pygame.display.flip()

        framerate: int = self.used_framerate()
        real_time: float
        if framerate <= 0:
            real_time = self.__main_clock.tick()
        elif self.get_busy_loop():
            real_time = self.__main_clock.tick_busy_loop(framerate)
        else:
            real_time = self.__main_clock.tick(framerate)
        fixed_framerate: int = self.used_fixed_framerate()
        fixed_delta_attribute: str = mangle_private_attribute(Time, "fixed_delta")
        setattr(Time, fixed_delta_attribute, 1 / fixed_framerate if fixed_framerate > 0 else Time.delta())
        return real_time

    def draw(self, /, *targets: _SupportsDrawing) -> None:
        renderer: SurfaceRenderer = SurfaceRenderer(self.__surface)

        for target in targets:
            with suppress(pygame.error):
                target.draw_onto(renderer)

    @contextmanager
    def capture(self, /, draw_on_default_at_end: bool = True) -> Iterator[Surface]:
        default_surface = self.__surface
        self.__surface = captured_surface = self.get_screen_copy()
        try:
            yield captured_surface
        finally:
            if draw_on_default_at_end:
                default_surface.blit(captured_surface, (0, 0))
            self.__surface = default_surface

    def get_screen_copy(self, /) -> Surface:
        return self.__surface.copy()

    def handle_events(self, /) -> List[Event]:
        return list(self.process_events())

    @contextmanager
    def no_window_callback_processing(self, /) -> Iterator[None]:
        self.__process_callbacks = False
        try:
            yield
        finally:
            self.__process_callbacks = True

    def _process_callbacks(self, /) -> None:
        self.__callback_after.process()

    def process_events(self, /) -> Iterator[Event]:
        Keyboard.update()
        Mouse.update()
        if self.__process_callbacks:
            self._process_callbacks()

        buffer = self.__event_buffer
        buffer.extend(pygame.event.get())
        while buffer:
            pg_event = buffer.pop(0)
            if pg_event.type == pygame.QUIT:
                self.close()
            try:
                event = Event.from_pygame_event(pg_event)
            except UnknownEventTypeError:
                continue
            if not event.type.is_allowed():
                continue
            self.event.process_event(event)
            yield event

        self.event.handle_mouse_position()

    def allow_only_event(self, /, *event_types: Event.Type) -> None:
        self.block_only_event(*(event for event in Event.Type if event not in event_types))

    @contextmanager
    def allow_only_event_context(self, /, *event_types: Event.Type) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_only_event(*event_types)
            yield

    def allow_all_events(self, /) -> None:
        pygame.event.set_allowed(None)

    @contextmanager
    def allow_all_events_context(self, /) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_all_events()
            yield

    def clear_all_events(self, /) -> None:
        pygame.event.clear()
        self.__event_buffer.clear()

    def block_only_event(self, /, *event_types: Event.Type) -> None:
        pygame.event.set_blocked([Event.Type(event) for event in event_types])

    @contextmanager
    def block_only_event_context(self, /, *event_types: Event.Type) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_only_event(*event_types)
            yield

    def block_all_events(self, /) -> None:
        pygame.event.set_blocked(list(Event.Type))

    @contextmanager
    def block_all_events_context(self, /) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_all_events()
            yield

    @contextmanager
    def __save_blocked_events(self, /) -> Iterator[None]:
        all_blocked_events: List[Event.Type] = [event for event in Event.Type if not event.is_allowed()]

        def set_blocked_events() -> None:
            if not all_blocked_events:
                self.allow_all_events()
            else:
                self.block_only_event(*all_blocked_events)

        with ExitStack() as stack:
            stack.callback(set_blocked_events)
            yield

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
        rect = self.__rect
        return Rect((0, 0), rect.size)

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
        self.__fps_tick: float = Time.get_ticks()
        self.__last_tick: float = self.__fps_tick

    def __tick_impl(self, /, framerate: int, use_accurate_delay: bool) -> float:
        actual_tick: float = Time.get_ticks()
        elapsed: float = actual_tick - self.__last_tick
        if framerate > 0:
            tick_time: float = 1000 / framerate
            if elapsed < tick_time:
                delay: float = tick_time - elapsed
                if delay >= 2:
                    if use_accurate_delay:
                        actual_tick += Time.delay(delay)
                    else:
                        actual_tick += Time.wait(delay)
        elapsed = actual_tick - self.__last_tick
        setattr(Time, mangle_private_attribute(Time, "delta"), elapsed / 1000)
        self.__last_tick = actual_tick

        self.__fps_count += 1
        if self.__fps_count >= 10:
            self.__fps = self.__fps_count / ((actual_tick - self.__fps_tick) / 1000.0)
            self.__fps_count = 0
            self.__fps_tick = actual_tick
        return elapsed

    def tick(self, /, framerate: int = 0) -> float:
        return self.__tick_impl(framerate, False)

    def tick_busy_loop(self, /, framerate: int = 0) -> float:
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
            args = self.__args
            kwargs = self.__kwargs
            callback = self.__callback
            callback(*args, **kwargs)
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
