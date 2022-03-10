# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window display module"""

from __future__ import annotations

__all__ = ["ScheduledFunction", "Window", "WindowCallback", "WindowError", "scheduled"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from contextlib import ExitStack, contextmanager, suppress
from inspect import isgeneratorfunction
from operator import truth
from types import MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Final,
    Generic,
    Iterator,
    NoReturn,
    ParamSpec,
    Protocol,
    Sequence,
    TypeVar,
    final,
    overload,
)

import pygame.display as _pg_display
import pygame.event as _pg_event
from pygame import error as _pg_error
from pygame.constants import (
    FULLSCREEN as _PG_FULLSCREEN,
    QUIT as _PG_QUIT,
    RESIZABLE as _PG_RESIZABLE,
    VIDEORESIZE as _PG_VIDEORESIZE,
    WINDOWCLOSE as _PG_WINDOWCLOSE,
)
from pygame.mixer import music as _pg_music

from ..audio.music import MusicStream
from ..graphics.color import BLACK, WHITE
from ..graphics.rect import ImmutableRect
from ..graphics.renderer import Renderer, SurfaceRenderer
from ..graphics.surface import Surface, create_surface
from ..graphics.text import Text
from ..graphics.theme import NoTheme
from ..system._mangling import getattr_pv, setattr_pv
from ..system.utils import wraps
from .clock import Clock
from .cursor import Cursor
from .event import Event, EventFactory, EventManager, UnknownEventTypeError, WindowSizeChangedEvent
from .keyboard import Keyboard
from .mouse import Mouse
from .time import Time

if TYPE_CHECKING:
    from pygame._common import _ColorValue  # pyright: reportMissingModuleSource=false

_P = ParamSpec("_P")
_ScheduledFunc = TypeVar("_ScheduledFunc", bound=Callable[..., None])


class _SupportsDrawing(Protocol):
    @abstractmethod
    def draw_onto(self, target: Renderer) -> None:
        raise NotImplementedError


class WindowError(_pg_error):
    pass


class ScheduledFunction(Generic[_P]):
    def __init__(self, milliseconds: float, func: Callable[_P, None]) -> None:
        super().__init__()
        self.__clock = Clock()
        self.__milliseconds: float = milliseconds
        self.__wrapped__: Callable[_P, None] = func
        self.__first_start: bool = True

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> None:
        func: Callable[_P, None] = self.__wrapped__
        if self.__first_start or self.__clock.elapsed_time(self.__milliseconds):
            self.__first_start = False
            func(*args, **kwargs)

    def __get__(self, obj: object, objtype: type | None = None, /) -> Callable[..., None]:
        if obj is None:
            return self
        return MethodType(self, obj)


def scheduled(milliseconds: float) -> Callable[[Callable[_P, None]], ScheduledFunction[_P]]:
    def decorator(func: Callable[_P, None], /) -> ScheduledFunction[_P]:
        return ScheduledFunction[_P](milliseconds, func)

    return decorator  # type: ignore


class Window:
    class __Exit(BaseException):
        pass

    DEFAULT_TITLE: Final[str] = "PyDiamond window"
    DEFAULT_FRAMERATE: Final[int] = 60
    DEFAULT_FIXED_FRAMERATE: Final[int] = 50

    __main_window: ClassVar[bool] = True

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if not Window.__main_window:
            raise WindowError("Cannot have multiple open windows")
        Window.__main_window = False
        return super().__new__(cls)

    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] = (0, 0),
        *,
        resizable: bool = False,
        fullscreen: bool = False,
        vsync: bool = True,
    ) -> None:
        self.set_title(title)
        self.__size: tuple[int, int] = (max(size[0], 0), max(size[1], 0))
        self.__flags: int = 0
        if resizable:
            self.__flags |= _PG_RESIZABLE
        elif fullscreen:
            self.__flags |= _PG_FULLSCREEN
            self.__size = (0, 0)
        self.__vsync: bool = bool(vsync)
        self.__surface: Surface = Surface((0, 0))
        self.__rect: ImmutableRect = ImmutableRect.convert(self.__surface.get_rect())

        self.__main_clock: _FramerateManager = _FramerateManager()
        self.__event: EventManager = EventManager()

        self.__framerate_update_clock: Clock = Clock(start=True)
        self.__default_framerate: int = self.DEFAULT_FRAMERATE
        self.__default_fixed_framerate: int = self.DEFAULT_FIXED_FRAMERATE
        self.__busy_loop: bool = False

        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__process_callbacks: bool = True

        self.__text_framerate: Text
        self.__stack = ExitStack()

    def __window_init__(self) -> None:
        pass

    def __window_quit__(self) -> None:
        pass

    def __del__(self) -> None:
        Window.__main_window = True

    __Self = TypeVar("__Self", bound="Window")

    @contextmanager
    def open(self: __Self) -> Iterator[__Self]:
        if self.looping():
            raise WindowError("Trying to open already opened window")

        def cleanup() -> None:
            self.__window_quit__()
            with suppress(AttributeError):
                del self.__text_framerate
            self.__callback_after.clear()
            self.__surface = Surface((0, 0))
            self.__rect = ImmutableRect.convert(self.__surface.get_rect())
            self.__event.unbind_all()

        self.__event.unbind_all()
        with self.__stack as stack, suppress(Window.__Exit):
            _pg_display.init()
            stack.callback(_pg_display.quit)

            from pygame.font import init as _pg_font_init, quit as _pg_font_quit

            _pg_font_init()
            stack.callback(_pg_font_quit)
            del _pg_font_init, _pg_font_quit

            size: tuple[int, int] = self.__size
            flags: int = self.__flags
            vsync = int(truth(self.__vsync))
            screen: Surface = _pg_display.set_mode(size, flags=flags, vsync=vsync)
            size = screen.get_size()
            self.__surface = create_surface(size)
            self.__rect = ImmutableRect.convert(self.__surface.get_rect())
            stack.callback(cleanup)
            self.__text_framerate = Text(color=WHITE, theme=NoTheme)
            self.__text_framerate.hide()
            self.__text_framerate.midtop = (self.centerx, self.top + 10)
            self.__window_init__()
            self.clear_all_events()
            self.__main_clock.tick()
            yield self

    def set_title(self, title: str | None) -> None:
        _pg_display.set_caption(title or Window.DEFAULT_TITLE)

    def iconify(self) -> bool:
        return truth(_pg_display.iconify())

    @final
    def close(self) -> NoReturn:
        _pg_display.quit()
        raise Window.__Exit

    @final
    def looping(self) -> bool:
        return _pg_display.get_surface() is not None

    def clear(self, color: _ColorValue = BLACK) -> None:
        self.__surface.fill(color)

    def get_default_framerate(self) -> int:
        return self.__default_framerate

    def set_default_framerate(self, value: int) -> None:
        self.__default_framerate = max(int(value), 0)

    def used_framerate(self) -> int:
        return self.__default_framerate

    def get_default_fixed_framerate(self) -> int:
        return self.__default_fixed_framerate

    def set_default_fixed_framerate(self, value: int) -> None:
        self.__default_fixed_framerate = max(int(value), 0)

    def used_fixed_framerate(self) -> int:
        return self.__default_fixed_framerate

    def get_busy_loop(self) -> bool:
        return self.__busy_loop

    def set_busy_loop(self, status: bool) -> None:
        self.__busy_loop = truth(status)

    def refresh(self) -> float:
        screen = SurfaceRenderer(_pg_display.get_surface())
        text_framerate: Text = self.__text_framerate
        screen.draw(self.__surface, (0, 0))
        if text_framerate.is_shown():
            if not text_framerate.message or self.__framerate_update_clock.elapsed_time(200):
                text_framerate.message = f"{round(self.framerate)} FPS"
            self.text_framerate.draw_onto(screen)
        Cursor.update()
        _pg_display.flip()

        framerate: int = self.used_framerate()
        real_time: float
        if framerate <= 0:
            real_time = self.__main_clock.tick()
        elif self.get_busy_loop():
            real_time = self.__main_clock.tick_busy_loop(framerate)
        else:
            real_time = self.__main_clock.tick(framerate)
        fixed_framerate: int = self.used_fixed_framerate()
        setattr_pv(Time, "fixed_delta", 1 / fixed_framerate if fixed_framerate > 0 else Time.delta())
        return real_time

    def draw(self, *targets: _SupportsDrawing) -> None:
        renderer: SurfaceRenderer = SurfaceRenderer(self.__surface)

        for target in targets:
            with suppress(_pg_error):
                target.draw_onto(renderer)

    @contextmanager
    def capture(self, draw_on_default_at_end: bool = True) -> Iterator[Surface]:
        default_surface = self.__surface
        self.__surface = captured_surface = self.get_screen_copy()
        try:
            yield captured_surface
        finally:
            if draw_on_default_at_end:
                default_surface.blit(captured_surface, (0, 0))
            self.__surface = default_surface

    def get_screen_copy(self) -> Surface:
        return self.__surface.copy()

    def handle_events(self) -> Sequence[Event]:
        return tuple(self.process_events())

    @contextmanager
    def no_window_callback_processing(self) -> Iterator[None]:
        self.__process_callbacks = False
        try:
            yield
        finally:
            self.__process_callbacks = True

    def _process_callbacks(self) -> None:
        self.__callback_after.process()

    def process_events(self) -> Iterator[Event]:
        Keyboard.update()
        Mouse.update()

        if self.__process_callbacks:
            self._process_callbacks()

        manager: EventManager = self.event

        process_event = manager.process_event
        make_event = EventFactory.from_pygame_event
        update_music_stream: Callable[[], None] = getattr_pv(MusicStream, "update")
        for pg_event in _pg_event.get():
            if pg_event.type in (_PG_QUIT, _PG_WINDOWCLOSE):
                self._handle_close_event()
                continue
            if pg_event.type == _PG_VIDEORESIZE:
                if not WindowSizeChangedEvent.type.is_allowed():
                    _pg_display.set_mode(self.__surface.get_size(), flags=self.__flags, vsync=int(self.__vsync))
                continue
            if pg_event.type == _pg_music.get_endevent():
                update_music_stream()
                continue
            try:
                event = make_event(pg_event)
            except UnknownEventTypeError:
                continue
            if isinstance(event, WindowSizeChangedEvent):
                former_surface = self.__surface
                new_surface = create_surface((event.x, event.y))
                new_surface.blit(former_surface, (0, 0))
                self.__surface = new_surface
                self.__rect = ImmutableRect.convert(new_surface.get_rect())
                del former_surface, new_surface
            if not event.type.is_allowed():
                continue
            if not process_event(event):
                yield event
        manager.handle_mouse_position()

    def _handle_close_event(self) -> None:
        self.close()

    @final
    def set_size(self, size: tuple[int, int]) -> None:
        width, height = size
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            raise ValueError("Invalid window size")
        if not self.looping():
            raise WindowError("Trying to resize not opened window")
        if not self.resizable:
            raise WindowError("Trying to resize not resizable window")
        size = (width, height)
        screen: Surface = _pg_display.get_surface()
        if size == screen.get_size():
            return
        flags: int = self.__flags
        vsync = int(truth(self.__vsync))
        _pg_display.set_mode(size, flags=flags, vsync=vsync)

    @final
    def set_width(self, width: int) -> None:
        height = self.__surface.get_size()[1]
        return self.set_size((width, height))

    @final
    def set_height(self, height: int) -> None:
        width = self.__surface.get_size()[0]
        return self.set_size((width, height))

    def allow_only_event(self, *event_types: Event.Type) -> None:
        event_types = tuple(Event.Type(e) for e in event_types)
        self.block_only_event(*(event for event in Event.Type if event not in event_types))

    @contextmanager
    def allow_only_event_context(self, *event_types: Event.Type) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_only_event(*event_types)
            yield

    def allow_all_events(self) -> None:
        _pg_event.set_allowed(None)

    @contextmanager
    def allow_all_events_context(self) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_all_events()
            yield

    def clear_all_events(self) -> None:
        _pg_event.clear()

    def block_only_event(self, *event_types: Event.Type) -> None:
        _pg_event.set_blocked([Event.Type(event) for event in event_types])

    @contextmanager
    def block_only_event_context(self, *event_types: Event.Type) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_only_event(*event_types)
            yield

    def block_all_events(self) -> None:
        _pg_event.set_blocked(tuple(Event.Type))

    @contextmanager
    def block_all_events_context(self) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_all_events()
            yield

    @contextmanager
    def __save_blocked_events(self) -> Iterator[None]:
        all_blocked_events: Sequence[Event.Type] = tuple(event for event in Event.Type if not event.is_allowed())

        def set_blocked_events() -> None:
            if not _pg_display.get_init():
                return
            if not all_blocked_events:
                self.allow_all_events()
            else:
                self.block_only_event(*all_blocked_events)

        with ExitStack() as stack:
            stack.callback(set_blocked_events)
            yield

    def after(
        self, __milliseconds: float, __callback: Callable[_P, None], /, *args: _P.args, **kwargs: _P.kwargs
    ) -> WindowCallback:
        window_callback: WindowCallback = WindowCallback(self, __milliseconds, __callback, args, kwargs)  # type: ignore[arg-type]
        self.__callback_after.append(window_callback)
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

            window_callback = WindowCallback(self, __milliseconds, wrapper, loop=True)
        else:
            window_callback = WindowCallback(self, __milliseconds, __callback, args, kwargs, loop=True)
        self.__callback_after.append(window_callback)
        return window_callback

    def remove_window_callback(self, window_callback: WindowCallback) -> None:
        with suppress(ValueError):
            self.__callback_after.remove(window_callback)

    @property
    def framerate(self) -> float:
        return self.__main_clock.get_fps()

    @property
    def text_framerate(self) -> Text:
        return self.__text_framerate

    @property
    def event(self) -> EventManager:
        return self.__event

    @property
    def exit_stack(self) -> ExitStack:
        return self.__stack

    @property
    def resizable(self) -> bool:
        out: int = self.__flags & _PG_RESIZABLE
        return out != 0

    @property
    def rect(self) -> ImmutableRect:
        return self.__rect

    @property
    def left(self) -> int:
        return self.__rect.left

    @property
    def right(self) -> int:
        return self.__rect.right

    @property
    def top(self) -> int:
        return self.__rect.top

    @property
    def bottom(self) -> int:
        return self.__rect.bottom

    @property
    def size(self) -> tuple[int, int]:
        return self.__rect.size

    @property
    def width(self) -> int:
        return self.__rect.width

    @property
    def height(self) -> int:
        return self.__rect.height

    @property
    def center(self) -> tuple[int, int]:
        return self.__rect.center

    @property
    def centerx(self) -> int:
        return self.__rect.centerx

    @property
    def centery(self) -> int:
        return self.__rect.centery

    @property
    def topleft(self) -> tuple[int, int]:
        return self.__rect.topleft

    @property
    def topright(self) -> tuple[int, int]:
        return self.__rect.topright

    @property
    def bottomleft(self) -> tuple[int, int]:
        return self.__rect.bottomleft

    @property
    def bottomright(self) -> tuple[int, int]:
        return self.__rect.bottomright

    @property
    def midtop(self) -> tuple[int, int]:
        return self.__rect.midtop

    @property
    def midbottom(self) -> tuple[int, int]:
        return self.__rect.midbottom

    @property
    def midleft(self) -> tuple[int, int]:
        return self.__rect.midleft

    @property
    def midright(self) -> tuple[int, int]:
        return self.__rect.midright

    del __Self


class _FramerateManager:
    def __init__(self) -> None:
        self.__fps: float = 0
        self.__fps_count: int = 0
        self.__fps_tick: float = Time.get_ticks()
        self.__last_tick: float = self.__fps_tick

    def __tick_impl(self, framerate: int, use_accurate_delay: bool) -> float:
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
        setattr_pv(Time, "delta", elapsed / 1000)
        self.__last_tick = actual_tick

        self.__fps_count += 1
        if self.__fps_count >= 10:
            self.__fps = self.__fps_count / ((actual_tick - self.__fps_tick) / 1000.0)
            self.__fps_count = 0
            self.__fps_tick = actual_tick
        return elapsed

    def tick(self, framerate: int = 0) -> float:
        return self.__tick_impl(framerate, False)

    def tick_busy_loop(self, framerate: int = 0) -> float:
        return self.__tick_impl(framerate, True)

    def get_fps(self) -> float:
        return self.__fps


class WindowCallback:
    def __init__(
        self,
        master: Window,
        wait_time: float,
        callback: Callable[..., None],
        args: tuple[Any, ...] = (),
        kwargs: dict[str, Any] = {},
        loop: bool = False,
    ) -> None:
        self.__master: Window = master
        self.__wait_time: float = wait_time
        self.__callback: Callable[..., None] = callback
        self.__args: tuple[Any, ...] = args
        self.__kwargs: dict[str, Any] = kwargs
        self.__clock = Clock(start=True)
        self.__loop: bool = bool(loop)

    def __call__(self) -> None:
        loop: bool = self.__loop
        if self.__clock.elapsed_time(self.__wait_time, restart=loop):
            args = self.__args
            kwargs = self.__kwargs
            callback = self.__callback
            callback(*args, **kwargs)
            if not loop:
                self.kill()

    def kill(self) -> None:
        self.__master.remove_window_callback(self)


class _WindowCallbackList(list[WindowCallback]):
    def process(self) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()


del _P, _ScheduledFunc
