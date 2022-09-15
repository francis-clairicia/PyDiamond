# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window display module"""

from __future__ import annotations

__all__ = ["Window", "WindowCallback", "WindowError", "WindowExit"]

import gc
import os
import os.path
from bisect import insort_left
from collections import deque
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from inspect import isgeneratorfunction
from itertools import count as itertools_count, filterfalse, islice
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Final,
    Generator,
    Iterable,
    Iterator,
    Literal,
    NoReturn,
    ParamSpec,
    Sequence,
    TypeVar,
    overload,
)

import pygame.display as _pg_display
import pygame.event as _pg_event
import pygame.key as _pg_key
import pygame.mouse as _pg_mouse
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
from ..graphics.rect import ImmutableRect, Rect
from ..graphics.surface import Surface, SurfaceRenderer, create_surface, save_image
from ..system.clock import Clock
from ..system.object import Object, ObjectMeta, final
from ..system.path import ConstantFileNotFoundError, set_constant_file
from ..system.threading import Thread, thread_factory_method
from ..system.time import Time
from ..system.utils._mangling import setattr_pv
from ..system.utils.contextlib import ExitStackView
from ..system.utils.functools import wraps
from ..system.utils.itertools import consume
from .cursor import Cursor, SystemCursor, make_cursor_from_pygame_cursor
from .event import Event, EventFactory, EventManager, ScreenshotEvent, UnknownEventTypeError
from .keyboard import Keyboard
from .mouse import Mouse

if TYPE_CHECKING:
    from pygame._common import _ColorValue  # pyright: reportMissingModuleSource=false

    from ..graphics.drawable import SupportsDrawing
    from ..graphics.renderer import AbstractRenderer

_P = ParamSpec("_P")


class WindowError(_pg_error):
    pass


class WindowExit(BaseException):
    pass


class Window(Object):
    DEFAULT_TITLE: Final[str] = "PyDiamond window"
    DEFAULT_FRAMERATE: Final[int] = 60
    DEFAULT_SIZE: Final[tuple[int, int]] = (800, 600)

    __main_window: ClassVar[bool] = True

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        if not Window.__main_window:
            raise WindowError("Cannot have multiple open windows")
        Window.__main_window = False
        return super().__new__(cls)

    def __init__(
        self,
        title: str | None = None,
        size: tuple[int, int] | None = None,
        *,
        resizable: bool = False,
        fullscreen: bool = False,
        vsync: bool = False,
    ) -> None:
        self.set_title(title)
        if size is not None:
            width, height = size
            if not isinstance(width, int) or not isinstance(height, int):
                raise TypeError("Invalid 'size' argument")
            if width < 0:
                raise ValueError("'size': Negative width")
            if height < 0:
                raise ValueError("'size': Negative height")
        self.__flags: int = 0
        if resizable and fullscreen:
            raise WindowError("Choose between resizable or fullscreen window, both cannot exist")
        if resizable:
            self.__flags |= _PG_RESIZABLE
        if fullscreen:
            if size is not None:
                raise WindowError("'size' parameter must not be given if 'fullscreen' is set")
            size = (0, 0)
            self.__flags |= _PG_FULLSCREEN
        if size is None:
            size = self.DEFAULT_SIZE
        self.__size: tuple[int, int] = size
        self.__vsync: bool = bool(vsync)

        self.__display_renderer: _WindowRenderer | None = None
        self.__rect: ImmutableRect = ImmutableRect(0, 0, 0, 0)
        self.__main_clock: _FramerateManager = _FramerateManager()
        self.__event: EventManager = EventManager()
        self.__event_queue: deque[_pg_event.Event] = deque()

        self._last_tick_time: float = -1

        self.__default_framerate: int = self.DEFAULT_FRAMERATE
        self.__busy_loop: bool = False

        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__process_callbacks: bool = True
        self.__handle_mouse_position: bool = True
        self.__handle_mouse_button: bool | None = False
        self.__handle_keyboard: bool | None = False

        self.__stack = ExitStack()

        self.__screenshot_threads: list[Thread] = []
        self.__context_cursor: _TemporaryCursor | None = None

    def __window_init__(self) -> None:
        pass

    def __window_quit__(self) -> None:
        pass

    def __del__(self) -> None:
        Window.__main_window = True

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="Window")

    def __enter__(self: __Self) -> __Self:
        cm = self.open()
        cm.__enter__()
        cm_exit = cm.__exit__
        setattr(self, "__exit__", cm_exit)
        return self

    def __exit__(self, *args: Any) -> bool | None:
        # When using the 'with' statement, the __exit__ method will be retrieved through the class, not the object
        # The __exit__ mock made in __enter__ will, therefore, not be used
        try:
            open_exit: Callable[..., bool | None] = self.__dict__["__exit__"]
        except KeyError:
            return False
        return open_exit(*args)

    @contextmanager
    def open(self) -> Iterator[None]:
        if _pg_display.get_surface() is not None:
            raise WindowError("Trying to open already open window")

        with ExitStack() as stack, suppress(WindowExit):
            _pg_display.init()
            stack.callback(_pg_display.quit)

            import pygame.freetype as _pg_freetype

            if not _pg_freetype.get_init():
                _pg_freetype.init()
                stack.callback(_pg_freetype.quit)
            del _pg_freetype

            size: tuple[int, int] = self.__size
            flags: int = self.__flags
            vsync = int(bool(self.__vsync))
            _pg_display.set_mode(size, flags=flags, vsync=vsync)
            self.__display_renderer = _WindowRenderer()
            self.__rect = ImmutableRect.convert(self.__display_renderer.get_rect())

            @stack.callback
            def _() -> None:
                self.__display_renderer = None
                self.__rect = ImmutableRect(0, 0, 0, 0)
                self._last_tick_time = -1
                self.__event.unbind_all()
                self.__event_queue.clear()

            stack.enter_context(self.__stack)
            self.__window_init__()
            stack.callback(self.__window_quit__)

            @stack.callback
            def _() -> None:
                try:
                    for callback in list(self.__callback_after):
                        with suppress(Exception):
                            callback.kill()
                finally:
                    self.__callback_after.clear()

            @stack.callback
            def _() -> None:
                screenshot_threads = self.__screenshot_threads
                while screenshot_threads:
                    screenshot_threads.pop(0).join(timeout=1, terminate_on_timeout=True)

            @stack.callback
            def _() -> None:  # Ensure patches added by __enter__ are deleted
                with suppress(AttributeError):
                    delattr(self, "__exit__")

            del _

            self.set_cursor(SystemCursor.ARROW)

            self.clear_all_events()
            self.__main_clock.tick()
            self._last_tick_time = -1
            yield

        gc.collect()  # Run a full collection at the window close

    @final
    def set_title(self, title: str | None) -> None:
        _pg_display.set_caption(title or self.DEFAULT_TITLE)

    @final
    def get_title(self) -> str:
        return _pg_display.get_caption()[0]

    @final
    def iconify(self) -> bool:
        return bool(_pg_display.iconify())

    @final
    def close(self) -> NoReturn:
        screenshot_threads = self.__screenshot_threads
        while screenshot_threads:
            screenshot_threads.pop(0).join(timeout=1, terminate_on_timeout=True)
        self.__display_renderer = None
        raise WindowExit

    @final
    def is_open(self) -> bool:
        return _pg_display.get_surface() is not None and self.__display_renderer is not None

    @final
    def loop(self) -> Literal[True]:
        self._last_tick_time = self._handle_framerate()

        if _pg_display.get_surface() is None or (renderer := self.__display_renderer) is None:
            self.close()

        event_queue = self.__event_queue
        event_queue.clear()

        add_event = event_queue.append

        if self.__handle_keyboard is not None:
            if self.__handle_keyboard:
                type.__setattr__(Keyboard, "_KEY_STATES", _pg_key.get_pressed())
            else:
                type.__setattr__(Keyboard, "_KEY_STATES", [])
        if self.__handle_mouse_button is not None:
            if self.__handle_mouse_button:
                type.__setattr__(Mouse, "_MOUSE_BUTTON_STATE", _pg_mouse.get_pressed(3))
            else:
                type.__setattr__(Mouse, "_MOUSE_BUTTON_STATE", ())

        if screenshot_threads := self.__screenshot_threads:
            screenshot_threads[:] = [t for t in screenshot_threads if t.is_alive()]

        if context_cursor := self.__context_cursor:
            if context_cursor.nb_frames > 0:
                _pg_mouse.set_cursor(context_cursor.cursor)
                context_cursor.nb_frames -= 1
            else:
                _pg_mouse.set_cursor(context_cursor.replaced_cursor)
                self.__context_cursor = None

        if self.__process_callbacks:
            self._process_callbacks()

        handle_music_event = MusicStream._handle_event
        for event in _pg_event.get():
            if event.type == _PG_QUIT:
                try:
                    self._handle_close_event()
                except WindowExit:
                    self.__display_renderer = None
                    raise
                continue
            if event.type == _PG_VIDEORESIZE:
                self.__rect = ImmutableRect.convert(renderer.screen.get_rect())
                continue
            if not handle_music_event(event):  # If it's a music event which is not expected
                continue
            add_event(event)

        return True

    def clear(self, color: _ColorValue = BLACK, *, blend_alpha: bool = False) -> None:
        screen = self.__display_renderer
        if screen is None:
            return
        if blend_alpha and (color := Color(color)).a < 255:
            fake_screen: Surface = create_surface(screen.get_size())
            fake_screen.fill(color)
            screen.draw_surface(fake_screen, (0, 0))
        else:
            screen.fill(color)

    @final
    def get_default_framerate(self) -> int:
        return self.__default_framerate

    @final
    def set_default_framerate(self, value: int) -> None:
        self.__default_framerate = max(int(value), 0)

    def used_framerate(self) -> int:
        return self.__default_framerate

    def get_busy_loop(self) -> bool:
        return self.__busy_loop

    def set_busy_loop(self, status: bool) -> None:
        self.__busy_loop = bool(status)

    def _handle_framerate(self) -> float:
        framerate: int = self.used_framerate()
        real_time: float
        if framerate <= 0:
            real_time = self.__main_clock.tick()
        elif self.get_busy_loop():
            real_time = self.__main_clock.tick_busy_loop(framerate)
        else:
            real_time = self.__main_clock.tick(framerate)
        return real_time

    def refresh(self) -> None:
        screen = self.__display_renderer
        if screen is None:
            return
        screen.present()

    def draw(self, *targets: SupportsDrawing) -> None:
        renderer = self.__display_renderer
        if renderer is None:
            return
        for target in targets:
            target.draw_onto(renderer)

    def capture(self, draw_on_default_at_end: bool = True) -> ContextManager[Surface]:
        renderer = self.__display_renderer
        assert renderer is not None, "No active renderer"
        return renderer.capture(draw_on_default_at_end=draw_on_default_at_end)

    @final
    def get_screen_copy(self) -> Surface:
        renderer = self.__display_renderer
        assert renderer is not None, "No active renderer"
        return renderer.surface.copy()

    def screenshot(self) -> None:
        screen: Surface = self.get_screen_copy()
        self.__screenshot_threads.append(self.__screenshot_thread(screen))

    @thread_factory_method(daemon=True, shared_lock=True)
    def __screenshot_thread(self, screen: Surface) -> None:
        filename_fmt: str = self.get_screenshot_filename_format()
        extension: str = ".png"

        if any(c in filename_fmt for c in {"/", "\\", os.path.sep}):
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
        consume(self.process_events())

    @final
    @contextmanager
    def no_window_callback_processing(self) -> Iterator[None]:
        if not self.__process_callbacks:
            yield
            return
        self.__process_callbacks = False
        try:
            yield
        finally:
            self.__process_callbacks = True

    @final
    @contextmanager
    def no_mouse_update(self) -> Iterator[None]:
        handle_mouse_position: bool = self.__handle_mouse_position
        handle_mouse_button: bool | None = self.__handle_mouse_button
        self.__handle_mouse_position = False
        self.__handle_mouse_button = None
        try:
            yield
        finally:
            self.__handle_mouse_position = handle_mouse_position
            self.__handle_mouse_button = handle_mouse_button

    @final
    @contextmanager
    def no_keyboard_update(self) -> Iterator[None]:
        handle_keyboard: bool | None = self.__handle_keyboard
        self.__handle_keyboard = None
        try:
            yield
        finally:
            self.__handle_keyboard = handle_keyboard

    @final
    @contextmanager
    def disable_mouse_button_state_update(self) -> Iterator[None]:
        if not self.__handle_mouse_button:
            yield
            return
        self.__handle_mouse_button = False
        try:
            yield
        finally:
            self.__handle_mouse_button = True

    @final
    @contextmanager
    def disable_keyboard_state_update(self) -> Iterator[None]:
        if not self.__handle_keyboard:
            yield
            return
        self.__handle_keyboard = False
        try:
            yield
        finally:
            self.__handle_keyboard = True

    @final
    @contextmanager
    def enable_mouse_button_state_update(self) -> Iterator[None]:
        if self.__handle_mouse_button is None:
            raise WindowError("Window.no_mouse_update() context is active, cannot enable mouse button state update")
        if self.__handle_mouse_button:
            yield
            return
        self.__handle_mouse_button = True
        try:
            yield
        finally:
            self.__handle_mouse_button = False

    @final
    @contextmanager
    def enable_keyboard_state_update(self) -> Iterator[None]:
        if self.__handle_keyboard is None:
            raise WindowError("Window.no_keyboard_update() context is active, cannot enable keyboard state update")
        if self.__handle_keyboard:
            yield
            return
        self.__handle_keyboard = True
        try:
            yield
        finally:
            self.__handle_keyboard = False

    @final
    @contextmanager
    def stuck(self) -> Iterator[None]:
        with (
            self.block_all_events_context(),
            self.no_window_callback_processing(),
            self.no_keyboard_update(),
            self.no_mouse_update(),
        ):
            yield

    def _process_callbacks(self) -> None:
        self.__callback_after.process()

    def process_events(self) -> Generator[Event, None, None]:
        if self.__handle_mouse_position:
            self._handle_mouse_position(Mouse.get_pos())
        poll_event = self.__event_queue.popleft
        process_event = self._process_event
        make_event = EventFactory.from_pygame_event
        while True:
            try:
                pg_event = poll_event()
            except IndexError:
                break
            try:
                event = make_event(pg_event, handle_user_events=True)
            except UnknownEventTypeError:
                _pg_event.set_blocked(pg_event.type)
                continue
            if not process_event(event):
                yield event

    def _process_event(self, event: Event) -> bool:
        return self.event.process_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        return self.event.handle_mouse_position(mouse_pos)

    @final
    def post_event(self, event: Event) -> bool:
        return _pg_event.post(EventFactory.make_pygame_event(event))

    def _handle_close_event(self) -> None:
        self.close()

    @final
    def get_cursor(self) -> Cursor:
        return make_cursor_from_pygame_cursor(_pg_mouse.get_cursor())

    @final
    def set_cursor(self, cursor: Cursor, *, nb_frames: int = 0) -> None:
        if nb_frames <= 0:
            self.__context_cursor = None
            _pg_mouse.set_cursor(cursor)
            return
        context_cursor = self.__context_cursor
        if not context_cursor:
            self.__context_cursor = _TemporaryCursor(cursor, self.get_cursor(), nb_frames)
        else:
            context_cursor.cursor = cursor
            context_cursor.nb_frames = nb_frames

    @final
    def set_size(self, size: tuple[int, int]) -> None:
        width, height = size
        width = int(width)
        height = int(height)
        if width <= 0 or height <= 0:
            raise ValueError("Invalid window size")
        if not self.is_open():
            raise WindowError("Trying to resize not open window")
        if not self.resizable:
            raise WindowError("Trying to resize not resizable window")
        size = (width, height)
        renderer = self.__display_renderer
        assert renderer is not None, "No active renderer"
        screen: Surface = renderer.screen
        if size == screen.get_size():
            return
        flags: int = self.__flags
        vsync = int(bool(self.__vsync))
        screen = _pg_display.set_mode(size, flags=flags, vsync=vsync)
        self.__rect = ImmutableRect.convert(screen.get_rect())

    @final
    def set_width(self, width: int) -> None:
        height = int(self.renderer.get_height())
        return self.set_size((width, height))

    @final
    def set_height(self, height: int) -> None:
        width = int(self.renderer.get_width())
        return self.set_size((width, height))

    @final
    def event_is_allowed(self, event_type: type[Event]) -> bool:
        return not _pg_event.get_blocked(EventFactory.get_pygame_event_type(event_type))

    @final
    def allow_event(self, *event_types: type[Event]) -> None:
        pg_event_types = tuple(map(EventFactory.get_pygame_event_type, event_types))
        _pg_event.set_allowed(pg_event_types)

    @contextmanager
    def allow_event_context(self, *event_types: type[Event]) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_event(*event_types)
            yield

    @final
    def allow_only_event(self, *event_types: type[Event]) -> None:
        if not event_types:
            return
        with self.__save_blocked_events(do_not_reinitialize_on_success=True):
            self.block_all_events()
            self.allow_event(*event_types)

    @contextmanager
    def allow_only_event_context(self, *event_types: type[Event]) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_only_event(*event_types)
            yield

    @final
    def allow_all_events(self, *, except_for: Iterable[type[Event]] = ()) -> None:
        ignored_pg_events = tuple(map(EventFactory.get_pygame_event_type, except_for))
        if not ignored_pg_events:
            _pg_event.set_allowed(tuple(EventFactory.pygame_type.keys()))
            return
        _pg_event.set_allowed(tuple(filterfalse(ignored_pg_events.__contains__, EventFactory.pygame_type.keys())))
        _pg_event.set_blocked(ignored_pg_events)

    @contextmanager
    def allow_all_events_context(self, *, except_for: Iterable[type[Event]] = ()) -> Iterator[None]:
        with self.__save_blocked_events():
            self.allow_all_events(except_for=except_for)
            yield

    @final
    def clear_all_events(self) -> None:
        _pg_event.clear()
        self.__event_queue.clear()

    @final
    def event_is_blocked(self, event_type: type[Event]) -> bool:
        return bool(_pg_event.get_blocked(EventFactory.get_pygame_event_type(event_type)))

    @final
    def block_event(self, *event_types: type[Event]) -> None:
        pg_event_types = tuple(map(EventFactory.get_pygame_event_type, event_types))
        _pg_event.set_blocked(pg_event_types)

    @contextmanager
    def block_event_context(self, *event_types: type[Event]) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_event(*event_types)
            yield

    @final
    def block_only_event(self, *event_types: type[Event]) -> None:
        if not event_types:
            return
        with self.__save_blocked_events(do_not_reinitialize_on_success=True):
            self.allow_all_events()
            self.block_event(*event_types)

    @contextmanager
    def block_only_event_context(self, *event_types: type[Event]) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_only_event(*event_types)
            yield

    @final
    def block_all_events(self, *, except_for: Iterable[type[Event]] = ()) -> None:
        ignored_pg_events = tuple(map(EventFactory.get_pygame_event_type, except_for))
        blockable_events = tuple(filter(EventFactory.is_blockable, EventFactory.pygame_type))
        if not ignored_pg_events:
            _pg_event.set_blocked(blockable_events)
            return
        _pg_event.set_blocked(tuple(filterfalse(ignored_pg_events.__contains__, blockable_events)))
        _pg_event.set_allowed(ignored_pg_events)

    @contextmanager
    def block_all_events_context(self, *, except_for: Iterable[type[Event]] = ()) -> Iterator[None]:
        with self.__save_blocked_events():
            self.block_all_events(except_for=except_for)
            yield

    @contextmanager
    def __save_blocked_events(self, *, do_not_reinitialize_on_success: bool = False) -> Iterator[None]:
        all_blocked_events: Sequence[type[Event]] = tuple(filter(self.event_is_blocked, EventFactory.associations))

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
            window_callback.kill()

    @property
    @final
    def renderer(self) -> AbstractRenderer:
        renderer = self.__display_renderer
        assert renderer is not None, "No active renderer"
        return renderer

    @property
    def framerate(self) -> float:
        return self.__main_clock.get_fps()

    @property
    @final
    def event(self) -> EventManager:
        return self.__event

    @property
    @final
    def exit_stack(self) -> ExitStackView:
        return ExitStackView(self.__stack)

    @property
    @final
    def resizable(self) -> bool:
        return (self.__flags & _PG_RESIZABLE) == _PG_RESIZABLE

    @property
    @final
    def fullscreen(self) -> bool:
        return (self.__flags & _PG_FULLSCREEN) == _PG_FULLSCREEN

    @property
    @final
    def vsync(self) -> bool:
        return self.__vsync

    @property
    @final
    def rect(self) -> ImmutableRect:
        return self.__rect

    @property
    @final
    def left(self) -> int:
        return self.__rect.left

    @property
    @final
    def right(self) -> int:
        return self.__rect.right

    @property
    @final
    def top(self) -> int:
        return self.__rect.top

    @property
    @final
    def bottom(self) -> int:
        return self.__rect.bottom

    @property
    @final
    def size(self) -> tuple[int, int]:
        return self.__rect.size

    @property
    @final
    def width(self) -> int:
        return self.__rect.width

    @property
    @final
    def height(self) -> int:
        return self.__rect.height

    @property
    @final
    def center(self) -> tuple[int, int]:
        return self.__rect.center

    @property
    @final
    def centerx(self) -> int:
        return self.__rect.centerx

    @property
    @final
    def centery(self) -> int:
        return self.__rect.centery

    @property
    @final
    def topleft(self) -> tuple[int, int]:
        return self.__rect.topleft

    @property
    @final
    def topright(self) -> tuple[int, int]:
        return self.__rect.topright

    @property
    @final
    def bottomleft(self) -> tuple[int, int]:
        return self.__rect.bottomleft

    @property
    @final
    def bottomright(self) -> tuple[int, int]:
        return self.__rect.bottomright

    @property
    @final
    def midtop(self) -> tuple[int, int]:
        return self.__rect.midtop

    @property
    @final
    def midbottom(self) -> tuple[int, int]:
        return self.__rect.midbottom

    @property
    @final
    def midleft(self) -> tuple[int, int]:
        return self.__rect.midleft

    @property
    @final
    def midright(self) -> tuple[int, int]:
        return self.__rect.midright


class _FramerateManager:
    def __init__(self) -> None:
        self.Time = Time
        self.get_ticks = Time.get_ticks
        self.delay = Time.delay
        self.wait = Time.wait
        self.__fps: float = 0
        self.__fps_count: int = 0
        self.__fps_tick: float = self.get_ticks()
        self.__last_tick: float = self.__fps_tick

    def __tick_impl(self, framerate: int, use_accurate_delay: bool) -> float:
        actual_tick: float = self.get_ticks()
        elapsed: float = actual_tick - self.__last_tick
        if framerate >= 1:
            tick_time: float = 1000 / framerate
            if elapsed < tick_time:
                delay: float = tick_time - elapsed
                if delay >= 2:
                    if use_accurate_delay:
                        actual_tick += self.delay(delay)
                    else:
                        actual_tick += self.wait(delay)
                    elapsed = actual_tick - self.__last_tick
        setattr_pv(self.Time, "delta", elapsed / 1000)
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
        try:
            self.__master
        except AttributeError:
            return
        self.__master._remove_window_callback(self)
        with suppress(AttributeError):
            del self.__master, self.__args, self.__kwargs, self.__callback, self.__clock


class _WindowCallbackList(list[WindowCallback]):
    def process(self) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()


@final
class _WindowRendererMeta(ObjectMeta):
    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> _WindowRendererMeta:
        if os.environ.get("PYDIAMOND_RENDER_UPDATE", "0") == "1":
            draw_function_names = {
                "fill",
                "draw_surface",
                "draw_rect",
                "draw_polygon",
                "draw_circle",
                "draw_ellipse",
                "draw_arc",
                "draw_line",
                "draw_lines",
                "draw_aaline",
                "draw_aalines",
            }
            for draw_function_name in draw_function_names:
                draw_function: Callable[..., Rect] = getattr(SurfaceRenderer, draw_function_name)

                @wraps(draw_function)  # type: ignore[arg-type]
                def draw_wrapper(
                    self: _WindowRenderer,
                    /,
                    *args: Any,
                    __name: str = str(draw_function_name),
                    **kwargs: Any,
                ) -> Rect:
                    rect: Rect = getattr(super(_WindowRenderer, self), __name)(*args, **kwargs)
                    self._dirty.append(rect)
                    return rect

                namespace[draw_function_name] = draw_wrapper

            @wraps(SurfaceRenderer.draw_many_surfaces)
            def draw_many_surfaces(
                self: _WindowRenderer,
                /,
                sequence: Iterable[Any],
                doreturn: bool = True,
            ) -> list[Rect] | None:
                rects = super(_WindowRenderer, self).draw_many_surfaces(sequence, doreturn=True)
                if rects:
                    self._dirty.extend(rects)
                return rects if doreturn else None

            namespace["draw_many_surfaces"] = draw_many_surfaces

        return super().__new__(mcs, name, bases, namespace, **kwargs)


@final
class _WindowRenderer(SurfaceRenderer, metaclass=_WindowRendererMeta):
    __slots__ = ("_dirty", "__drawn_rects")

    __render_debug: bool = os.environ.get("PYDIAMOND_RENDER_DEBUG", "0") == "1"

    def __init__(self) -> None:
        screen: Surface | None = _pg_display.get_surface()
        if screen is None:
            raise _pg_error("No display mode configured")
        self.__drawn_rects: deque[Rect] = deque()
        self._dirty: deque[Rect] = deque()
        super().__init__(screen)

    def repaint_color(self, color: _ColorValue) -> None:
        self.surface.fill(color)

    if os.environ.get("PYDIAMOND_RENDER_UPDATE", "0") == "1":

        def present(self) -> None:
            screen = self.screen
            if self.surface is not screen:
                screen.fill((0, 0, 0))
                screen.blit(self.surface, (0, 0))
                _pg_display.flip()
                self.__drawn_rects = deque([screen.get_rect()])
            else:
                already_drawn_rects = self.__drawn_rects
                dirty_rects: deque[Rect] = deque(sorted(self._dirty, key=lambda r: r.w * r.h))
                self.__drawn_rects = dirty_rects
                self._dirty = deque()
                for rect in dirty_rects:
                    insort_left(already_drawn_rects, rect, key=lambda r: r.w * r.h)
                dirty_rects = self._merge_sorted_rect_list(already_drawn_rects)
                if dirty_rects:
                    if self.__render_debug:
                        draw_rect = super().draw_rect
                        for rect in dirty_rects:
                            draw_rect((127, 127, 127), rect, width=2)
                        dirty_rects = deque([screen.get_rect()])
                    _pg_display.update(dirty_rects)  # type: ignore[arg-type]
                del dirty_rects

    else:

        def present(self) -> None:
            screen = self.screen
            if self.surface is not screen:
                screen.fill((0, 0, 0))
                screen.blit(self.surface, (0, 0))
            _pg_display.flip()

    @contextmanager
    def capture(self, draw_on_default_at_end: bool = True) -> Iterator[Surface]:
        fset = SurfaceRenderer.surface.fset  # type: ignore[attr-defined]

        default_surface = self.surface
        captured_surface = default_surface.copy()
        fset(self, captured_surface)
        try:
            yield captured_surface
        finally:
            fset(self, default_surface)
            if draw_on_default_at_end:
                default_surface.blit(captured_surface, (0, 0))

    @classmethod
    def _merge_sorted_rect_list(cls, rects: deque[Rect]) -> deque[Rect]:
        if len(rects) < 2:
            return deque(rects)
        merged_rects_queue = deque([rects[0]])
        inner_merge = cls._merge_sorted_rect_list
        for r in islice(rects, 1, None):
            for actual_rect_index, actual_rect in zip(range(len(merged_rects_queue) - 1, -1, -1), reversed(merged_rects_queue)):
                if actual_rect.contains(r):
                    break
                if actual_rect.colliderect(r):
                    actual_rect = actual_rect.union(r)
                    if len(merged_rects_queue) > 1:
                        del merged_rects_queue[actual_rect_index]
                        insort_left(merged_rects_queue, actual_rect, key=lambda r: r.w * r.h)
                        merged_rects_queue = inner_merge(merged_rects_queue)
                    else:
                        merged_rects_queue[actual_rect_index] = actual_rect
                    break
            else:
                insort_left(merged_rects_queue, r, key=lambda r: r.w * r.h)
        return merged_rects_queue

    # @classmethod
    # def _append_dirty(cls, dirty_rects: deque[Rect], rect: Rect) -> None:
    #     nb_rects = len(dirty_rects)
    #     for nb_rotate in range(nb_rects):
    #         actual_rect = dirty_rects[0]
    #         if actual_rect.colliderect(rect):
    #             if not actual_rect.contains(rect):
    #                 actual_rect.union_ip(rect)
    #                 del rect
    #                 if nb_rects > 1:
    #                     dirty_rects.popleft()
    #                     cls._append_dirty(dirty_rects, actual_rect)
    #             dirty_rects.rotate(-nb_rotate)
    #             break
    #         dirty_rects.rotate(1)
    #     else:
    #         dirty_rects.append(rect)

    @property
    def screen(self) -> Surface:
        screen: Surface | None = _pg_display.get_surface()
        assert screen is not None, "No display mode configured"
        return screen

    if not TYPE_CHECKING:

        @SurfaceRenderer.surface.setter
        def surface(self, new_target: Surface) -> None:
            raise AttributeError("Read-only property")


@dataclass
class _TemporaryCursor:
    cursor: Cursor
    replaced_cursor: Cursor
    nb_frames: int
