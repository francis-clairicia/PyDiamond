# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window display module"""

from __future__ import annotations

__all__ = ["Window", "WindowCallback", "WindowError"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os
import os.path
from contextlib import ExitStack, contextmanager, suppress
from datetime import datetime
from inspect import isgeneratorfunction
from itertools import count as itertools_count, filterfalse
from threading import RLock
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Final,
    Iterable,
    Iterator,
    NoReturn,
    ParamSpec,
    Sequence,
    TypeVar,
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
)

from ..audio.music import MusicStream
from ..environ.executable import get_executable_path
from ..graphics.color import BLACK, Color
from ..graphics.rect import ImmutableRect
from ..graphics.renderer import AbstractRenderer, SurfaceRenderer
from ..graphics.surface import Surface, create_surface, save_image
from ..system.object import Object, final
from ..system.path import ConstantFileNotFoundError, set_constant_file
from ..system.threading import Thread, thread_factory
from ..system.utils._mangling import setattr_pv
from ..system.utils.functools import wraps
from .clock import Clock
from .cursor import AbstractCursor
from .event import (
    Event,
    EventFactory,
    EventFactoryError,
    EventManager,
    EventType,
    ScreenshotEvent,
    UnknownEventTypeError,
    UserEvent,
    WindowSizeChangedEvent,
)
from .keyboard import Keyboard
from .mouse import Mouse
from .time import Time

if TYPE_CHECKING:
    from pygame._common import _ColorValue  # pyright: reportMissingModuleSource=false

    from ..graphics.drawable import SupportsDrawing

_P = ParamSpec("_P")


class WindowError(_pg_error):
    pass


class Window(Object):
    class __Exit(BaseException):
        pass

    DEFAULT_TITLE: Final[str] = "PyDiamond window"
    DEFAULT_FRAMERATE: Final[int] = 60
    DEFAULT_FIXED_FRAMERATE: Final[int] = 50

    __main_window: ClassVar[bool] = True
    __screenshot_lock = RLock()

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
        vsync: bool = False,
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
        self.__surface: SurfaceRenderer = SurfaceRenderer(Surface((0, 0)))
        self.__clear_surface: Surface = Surface((0, 0))
        self.__rect: ImmutableRect = ImmutableRect.convert(self.__surface.get_rect())

        self.__display_renderer: SurfaceRenderer | None = None
        self.__main_clock: _FramerateManager = _FramerateManager()
        self.__event: EventManager = EventManager()

        self.__default_framerate: int = self.DEFAULT_FRAMERATE
        self.__default_fixed_framerate: int = self.DEFAULT_FIXED_FRAMERATE
        self.__busy_loop: bool = False

        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__process_callbacks: bool = True

        self.__stack = ExitStack()

        self.__screenshot_threads: list[Thread] = []

    def __window_init__(self) -> None:
        pass

    def __window_quit__(self) -> None:
        pass

    def __del__(self) -> None:
        super().__del__()
        Window.__main_window = True

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="Window")

    @contextmanager
    def open(self: __Self) -> Iterator[__Self]:
        if self.looping():
            raise WindowError("Trying to open already opened window")

        def cleanup() -> None:
            screenshot_threads = self.__screenshot_threads
            while screenshot_threads:
                screenshot_threads.pop(0).join(timeout=1, terminate_on_timeout=True)
            self.__window_quit__()
            self.__callback_after.clear()
            self.__surface = SurfaceRenderer(Surface((0, 0)))
            self.__clear_surface = Surface((0, 0))
            self.__rect = ImmutableRect.convert(self.__surface.get_rect())
            self.__display_renderer = None
            self.__event.unbind_all()

        self.__event.unbind_all()
        with ExitStack() as stack, self.__stack, suppress(Window.__Exit):
            _pg_display.init()
            stack.callback(_pg_display.quit)

            import pygame.font as _pg_font
            import pygame.freetype as _pg_freetype

            _pg_font.init()
            stack.callback(_pg_font.quit)
            if not _pg_freetype.get_init():
                _pg_freetype.init()
                stack.callback(_pg_freetype.quit)
            del _pg_font, _pg_freetype

            size: tuple[int, int] = self.__size
            flags: int = self.__flags
            vsync = int(bool(self.__vsync))
            screen: Surface = _pg_display.set_mode(size, flags=flags, vsync=vsync)
            size = screen.get_size()
            self.__surface = SurfaceRenderer(size)
            self.__clear_surface = create_surface(size)
            self.__rect = ImmutableRect.convert(self.__surface.get_rect())
            self.__display_renderer = SurfaceRenderer(screen)
            stack.callback(cleanup)
            self.__window_init__()
            self.clear_all_events()
            self.__main_clock.tick()
            yield self

    def set_title(self, title: str | None) -> None:
        _pg_display.set_caption(title or Window.DEFAULT_TITLE)

    @final
    def get_title(self) -> str:
        return _pg_display.get_caption()[0]

    def iconify(self) -> bool:
        return bool(_pg_display.iconify())

    @final
    def close(self) -> NoReturn:
        screenshot_threads = self.__screenshot_threads
        while screenshot_threads:
            screenshot_threads.pop(0).join(timeout=1, terminate_on_timeout=True)
        self.__display_renderer = None
        raise Window.__Exit

    @final
    def looping(self) -> bool:
        return _pg_display.get_surface() is not None and self.__display_renderer is not None

    def clear(self, color: _ColorValue = BLACK, *, blend_alpha: bool = False) -> None:
        screen: SurfaceRenderer = self.__surface
        color = Color(color)
        if blend_alpha and color.a < 255:
            fake_screen: Surface = self.__clear_surface
            fake_screen.fill(color)
            screen.draw_surface(fake_screen, (0, 0))
        else:
            screen.fill(color)

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
        self.__busy_loop = bool(status)

    def refresh(self) -> float:
        screen = self.__display_renderer
        if screen is None:
            return 0
        screen.fill((0, 0, 0))
        screen.draw_surface(self.__surface.surface, (0, 0))
        self.system_display(screen)
        AbstractCursor._update()
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

    def system_display(self, screen: AbstractRenderer) -> None:
        pass

    def draw(self, *targets: SupportsDrawing) -> None:
        renderer: SurfaceRenderer = self.__surface

        for target in targets:
            with suppress(_pg_error):
                target.draw_onto(renderer)

    @contextmanager
    def capture(self, draw_on_default_at_end: bool = True) -> Iterator[Surface]:
        default_surface = self.__surface.surface
        captured_surface = self.get_screen_copy()
        self.__surface = SurfaceRenderer(captured_surface)
        try:
            yield captured_surface
        finally:
            if draw_on_default_at_end:
                default_surface.blit(captured_surface, (0, 0))
            self.__surface = SurfaceRenderer(default_surface)

    def get_screen_copy(self) -> Surface:
        return self.__surface.surface.copy()

    def screenshot(self) -> None:
        screen: Surface = self.get_screen_copy()
        self.__screenshot_threads.append(self.__screenshot_thread(screen))

    @thread_factory(daemon=True)
    def __screenshot_thread(self, screen: Surface) -> None:
        with self.__screenshot_lock:
            filename_fmt: str = self.get_screenshot_filename_format()
            extension: str = ".png"

            if any(c in filename_fmt for c in ("/", "\\", os.sep)):
                raise ValueError("filename format contains invalid characters")

            screeshot_dir: str = os.path.abspath(os.path.realpath(self.get_screenshot_directory()))
            os.makedirs(screeshot_dir, exist_ok=True)

            filename_fmt = os.path.join(screeshot_dir, filename_fmt)
            date = datetime.now()
            file: str = ""
            try:
                set_constant_file(date.strftime(f"{filename_fmt}{extension}"), raise_error=True)
                for i in itertools_count(start=1):
                    set_constant_file(date.strftime(f"{filename_fmt}_{i}{extension}"), raise_error=True)
            except ConstantFileNotFoundError as exc:
                file = str(exc.filename)
            save_image(screen, file)
            self.post_event(ScreenshotEvent(filepath=file, screen=screen))

    def get_screenshot_filename_format(self) -> str:
        return "Screenshot_%Y-%m-%d_%H-%M-%S"

    def get_screenshot_directory(self) -> str:
        return os.path.join(os.path.dirname(get_executable_path()), "screenshots")

    def handle_events(self) -> None:
        for _ in self.process_events():
            continue

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
        Keyboard._update()
        Mouse._update()

        if screenshot_threads := self.__screenshot_threads:
            self.__screenshot_threads[:] = [t for t in screenshot_threads if t.is_alive()]

        if self.__process_callbacks:
            self._process_callbacks()

        process_event = self._process_event
        make_event = EventFactory.from_pygame_event
        for pg_event in _pg_event.get():
            if pg_event.type == _PG_QUIT:
                self._handle_close_event()
                continue
            if pg_event.type == _PG_VIDEORESIZE:
                screen = _pg_display.set_mode(self.__surface.get_size(), flags=self.__flags, vsync=int(self.__vsync))
                self.__display_renderer = SurfaceRenderer(screen)
                continue
            if MusicStream._handle_event(pg_event):
                continue
            try:
                event = make_event(pg_event)
            except UnknownEventTypeError:
                if pg_event.type < UserEvent.type:  # Built-in pygame event
                    _pg_event.set_blocked(pg_event.type)
                continue
            except EventFactoryError:
                continue
            if isinstance(event, WindowSizeChangedEvent):
                former_surface = self.__surface.surface
                new_surface = SurfaceRenderer((event.x, event.y))
                new_surface.draw_surface(former_surface, (0, 0))
                self.__surface = new_surface
                self.__clear_surface = create_surface(new_surface.get_size())
                self.__rect = ImmutableRect.convert(new_surface.get_rect())
                del former_surface, new_surface
            if not process_event(event):
                yield event
        self._handle_mouse_position(Mouse.get_pos())

    def _process_event(self, event: Event) -> bool:
        return self.event.process_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        return self.event.handle_mouse_position(mouse_pos)

    def post_event(self, event: Event) -> bool:
        event_dict = event.to_dict()
        event_dict.pop("type", None)
        event_type = int(event.__class__.type)
        return _pg_event.post(_pg_event.Event(event_type, event_dict))

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
        vsync = int(bool(self.__vsync))
        screen = _pg_display.set_mode(size, flags=flags, vsync=vsync)
        self.__display_renderer = SurfaceRenderer(screen)

    @final
    def set_width(self, width: int) -> None:
        height = int(self.__surface.get_height())
        return self.set_size((width, height))

    @final
    def set_height(self, height: int) -> None:
        width = int(self.__surface.get_width())
        return self.set_size((width, height))

    @final
    def event_is_allowed(self, event_type: EventType) -> bool:
        return not _pg_event.get_blocked(event_type)

    @final
    def allow_event(self, *event_types: EventType) -> None:
        if tuple(filterfalse(EventFactory.is_valid_type, event_types)):
            raise ValueError(f"Invalid event types caught")
        _pg_event.set_allowed(event_types)

    @contextmanager
    def allow_event_context(self, *event_types: EventType) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_event(*event_types)
            yield

    @final
    def allow_only_event(self, *event_types: EventType) -> None:
        if not event_types:
            return
        with self.__save_blocked_events(do_not_reinitialize_on_success=True):
            self.block_all_events()
            self.allow_event(*event_types)

    @contextmanager
    def allow_only_event_context(self, *event_types: EventType) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_only_event(*event_types)
            yield

    @final
    def allow_all_events(self, *, except_for: Iterable[EventType] = ()) -> None:
        except_for = tuple(except_for)
        if tuple(filterfalse(EventFactory.is_valid_type, except_for)):
            raise ValueError(f"Invalid event types caught")
        if not except_for:
            _pg_event.set_allowed(EventFactory.get_all_event_types())
            return
        _pg_event.set_allowed(tuple(filterfalse(except_for.__contains__, EventFactory.get_all_event_types())))
        _pg_event.set_blocked(except_for)

    @contextmanager
    def allow_all_events_context(self, *, except_for: Iterable[EventType] = ()) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_all_events(except_for=except_for)
            yield

    @final
    def clear_all_events(self) -> None:
        _pg_event.clear()

    @final
    def event_is_blocked(self, event_type: EventType) -> bool:
        return bool(_pg_event.get_blocked(event_type))

    @final
    def block_event(self, *event_types: EventType) -> None:
        if tuple(filterfalse(EventFactory.is_valid_type, event_types)):
            raise ValueError(f"Invalid event types caught")
        _pg_event.set_blocked(event_types)

    @contextmanager
    def block_event_context(self, *event_types: EventType) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_event(*event_types)
            yield

    @final
    def block_only_event(self, *event_types: EventType) -> None:
        if not event_types:
            return
        with self.__save_blocked_events(do_not_reinitialize_on_success=True):
            self.allow_all_events()
            self.block_event(*event_types)

    @contextmanager
    def block_only_event_context(self, *event_types: EventType) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_only_event(*event_types)
            yield

    @final
    def block_all_events(self, *, except_for: Iterable[EventType] = ()) -> None:
        except_for = tuple(except_for)
        if tuple(filterfalse(EventFactory.is_valid_type, except_for)):
            raise ValueError(f"Invalid event types caught")
        if not except_for:
            _pg_event.set_blocked(EventFactory.get_all_event_types())
            return
        _pg_event.set_blocked(tuple(filterfalse(except_for.__contains__, EventFactory.get_all_event_types())))
        _pg_event.set_allowed(except_for)

    @contextmanager
    def block_all_events_context(self, *, except_for: Iterable[EventType] = ()) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_all_events(except_for=except_for)
            yield

    @contextmanager
    def __save_blocked_events(self, *, do_not_reinitialize_on_success: bool = False) -> Iterator[None]:
        all_blocked_events: Sequence[EventType] = tuple(filter(self.event_is_blocked, EventFactory.get_all_event_types()))

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
            if do_not_reinitialize_on_success:
                stack.pop_all()

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
            window_callback: WindowCallback = WindowCallback(self, __milliseconds, __callback, args, kwargs)
            self.__callback_after.append(window_callback)
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

        if __callback is not None:
            return decorator(__callback)
        return decorator

    def _remove_window_callback(self, window_callback: WindowCallback) -> None:
        with suppress(ValueError):
            self.__callback_after.remove(window_callback)

    @property
    def renderer(self) -> AbstractRenderer:
        return self.__surface

    @property
    def framerate(self) -> float:
        return self.__main_clock.get_fps()

    @property
    def event(self) -> EventManager:
        return self.__event

    @property
    def exit_stack(self) -> ExitStack:
        return self.__stack

    @property
    def resizable(self) -> bool:
        return (self.__flags & _PG_RESIZABLE) == _PG_RESIZABLE

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
        kwargs: dict[str, Any] | None = None,
        loop: bool = False,
    ) -> None:
        self.__master: Window = master
        self.__wait_time: float = wait_time
        self.__callback: Callable[..., None] = callback
        self.__args: tuple[Any, ...] = args
        self.__kwargs: dict[str, Any] = kwargs or {}
        self.__clock = Clock(start=True)
        self.__loop: bool = bool(loop)

    def __call__(self) -> None:
        try:
            clock = self.__clock
        except AttributeError:  # killed
            return
        loop: bool = self.__loop
        if clock.elapsed_time(self.__wait_time, restart=loop):
            args = self.__args
            kwargs = self.__kwargs
            callback = self.__callback
            callback(*args, **kwargs)
            if not loop:
                self.kill()

    def kill(self) -> None:
        self.__master._remove_window_callback(self)
        with suppress(AttributeError):
            del self.__master, self.__args, self.__kwargs, self.__callback, self.__clock


class _WindowCallbackList(list[WindowCallback]):
    def process(self) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()
