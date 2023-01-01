# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window display module"""

from __future__ import annotations

__all__ = ["Window", "WindowCallback", "WindowError", "WindowExit", "WindowRenderer"]

import gc
import os
import os.path
from abc import abstractmethod
from collections import deque
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import dataclass
from datetime import datetime
from inspect import isgeneratorfunction
from itertools import count as itertools_count, filterfalse
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
from weakref import ref as weakref

import pygame.display as _pg_display
import pygame.event as _pg_event
import pygame.key as _pg_key
import pygame.mouse as _pg_mouse
from pygame import error as _pg_error
from pygame.constants import (
    CONTROLLERDEVICEADDED as _PG_CONTROLLERDEVICEADDED,
    CONTROLLERDEVICEREMOVED as _PG_CONTROLLERDEVICEREMOVED,
    FULLSCREEN as _PG_FULLSCREEN,
    QUIT as _PG_QUIT,
    RESIZABLE as _PG_RESIZABLE,
    WINDOWCLOSE as _PG_WINDOWCLOSE,
)
from typing_extensions import assert_never, final

from ..audio.music import MusicStream
from ..environ.executable import get_executable_path
from ..graphics.color import BLACK, Color
from ..graphics.renderer import AbstractRenderer
from ..graphics.surface import AbstractSurfaceRenderer, Surface, create_surface, save_image
from ..math.rect import ImmutableRect
from ..system.clock import Clock
from ..system.object import Object
from ..system.path import ConstantFileNotFoundError, set_constant_file
from ..system.threading import Thread, thread_factory_method
from ..system.time import Time
from ..system.utils._mangling import setattr_pv
from ..system.utils.contextlib import ExitStackView
from ..system.utils.functools import wraps
from .controller import Controller
from .cursor import Cursor
from .event import Event, EventFactory, EventFactoryError, ScreenshotEvent, UnknownEventTypeError
from .keyboard import Keyboard
from .mouse import Mouse

if TYPE_CHECKING:
    from pygame._common import ColorValue

    from ..graphics.drawable import SupportsDrawing

_P = ParamSpec("_P")


class WindowError(_pg_error):
    pass


class WindowExit(BaseException):
    pass


class Window(Object, no_slots=True):
    if TYPE_CHECKING:
        __slots__: Final[tuple[str, ...]] = ("__dict__", "__weakref__")

        __Self = TypeVar("__Self", bound="Window")

    DEFAULT_TITLE: Final[str] = "PyDiamond window"
    DEFAULT_FRAMERATE: Final[int] = 60
    DEFAULT_SIZE: Final[tuple[int, int]] = (800, 600)

    __instance: ClassVar[Callable[[], "Window" | None]] = lambda: None

    def __new__(cls, *args: Any, **kwargs: Any) -> Any:
        instance = Window.__instance()
        try:
            if instance is not None:
                raise WindowError("Cannot have multiple open windows")
        finally:
            del instance

        def reset_singleton(_: Any) -> None:
            Window.__instance = lambda: None

        instance = super().__new__(cls)
        Window.__instance = weakref(instance, reset_singleton)
        return instance

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

        self.__close_on_next_frame: bool = True
        self.__close_event: Literal["close", "iconify", "nothing"] = "close"
        self.__display_renderer: _WindowRendererImpl | None = None
        self.__rect: ImmutableRect = ImmutableRect(0, 0, 0, 0)
        self.__main_clock: _FramerateManager = _FramerateManager()
        self.__event_queue: deque[_pg_event.Event] = deque()

        self.last_tick_time: float = -1

        self.__default_framerate: int = self.DEFAULT_FRAMERATE
        self.__busy_loop: bool = False

        self.__callback_after: _WindowCallbackList = _WindowCallbackList()
        self.__process_callbacks: bool = True
        self.__handle_mouse_position: bool = True
        self.__handle_mouse_button: bool | None = False
        self.__handle_keyboard: bool | None = False

        self.__mouse_position_callbacks: set[Callable[[Any, tuple[int, int]], Any]] = set()
        self.__loop_callbacks: set[Callable[[Any], Any]] = set()

        self.__stack = ExitStack()

        self.__screenshot_threads: list[Thread] = []
        self.__context_cursor: _TemporaryCursor | None = None

    def __window_init__(self) -> None:
        pass

    def __window_quit__(self) -> None:
        pass

    @contextmanager
    def open(self) -> Iterator[None]:
        if _pg_display.get_surface() is not None:
            raise WindowError("Trying to open already open window")

        with ExitStack() as stack, suppress(WindowExit):
            _pg_display.init()
            stack.callback(_pg_display.quit)

            import pygame._sdl2.controller as _pg_controller

            if not _pg_controller.get_init():
                _pg_controller.init()
                stack.callback(_pg_controller.quit)
            del _pg_controller

            size: tuple[int, int] = self.__size
            flags: int = self.__flags
            vsync: bool = self.__vsync
            _pg_display.set_mode(size, flags=flags, vsync=vsync)
            self.__display_renderer = _WindowRendererImpl()
            self.__rect = ImmutableRect.convert(self.__display_renderer.get_rect())

            @stack.callback
            def _() -> None:
                self.__close_on_next_frame = False
                self.__display_renderer = None
                self.__rect = ImmutableRect(0, 0, 0, 0)
                self.last_tick_time = -1
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
            def _() -> None:
                with ExitStack() as stack:
                    for controller in list(Controller._ALL_CONTROLLERS.values()):
                        stack.callback(controller.quit)

            del _

            from .cursor import SystemCursor

            self.set_cursor(SystemCursor.ARROW)

            self.__event_queue.clear()
            self.__main_clock.tick()
            self.last_tick_time = -1
            self.__close_on_next_frame = False
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
        raise WindowExit

    @final
    def delayed_close(self) -> None:
        self.__close_on_next_frame = True

    @final
    def is_open(self) -> bool:
        return _pg_display.get_surface() is not None and self.__display_renderer is not None

    @final
    def loop(self) -> Literal[True]:
        if self.__close_on_next_frame:
            raise WindowExit

        screen: Surface | None = _pg_display.get_surface()

        if screen is None or (renderer := self.__display_renderer) is None:
            raise WindowError("Closed window")

        framerate: int = self.used_framerate()
        if framerate <= 0:
            self.last_tick_time = self.__main_clock.tick()
        else:
            self.last_tick_time = self.__main_clock.tick(framerate, self.get_busy_loop())

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
                type.__setattr__(Mouse, "_MOUSE_BUTTON_STATE", _pg_mouse.get_pressed(5))
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

        if screen.get_size() != self.__rect.size:
            renderer._resize()
            self.__rect = ImmutableRect.convert(screen.get_rect())

        for loop_callback in list(self.__loop_callbacks):
            loop_callback(self)

        if self.__process_callbacks:
            self.__callback_after.process()

        handle_music_event = MusicStream._handle_event
        for event in _pg_event.get():
            if event.type == _PG_QUIT:
                continue
            if event.type == _PG_WINDOWCLOSE:
                match self.__close_event:
                    case "close":
                        add_event(event)
                        self.__close_on_next_frame = True
                        break
                    case "iconify":
                        self.iconify()
                        continue
                    case "nothing":
                        continue
                    case _:
                        assert_never(self.__close_event)
            if event.type == _PG_CONTROLLERDEVICEADDED:
                try:
                    Controller(event.device_index)
                except _pg_error:  # Should not happen: ignore event
                    continue
            elif event.type == _PG_CONTROLLERDEVICEREMOVED:
                try:
                    _controller = Controller._ALL_CONTROLLERS[event.instance_id]
                except KeyError:
                    pass
                else:
                    _controller.quit()
            elif not handle_music_event(event):  # If it's a music event which is not expected
                continue
            add_event(event)

        if self.__handle_mouse_position:
            mouse_pos: tuple[int, int] = Mouse.get_pos()
            for mouse_pos_callback in list(self.__mouse_position_callbacks):
                mouse_pos_callback(self, mouse_pos)

        return True

    def set_close_event_behavior(self, value: Literal["close", "iconify", "nothing"]) -> None:
        if value not in ("close", "iconify", "nothing"):
            raise ValueError(f"Invalid value: {value!r}")
        self.__close_event = value

    def register_loop_callback(self: __Self, callback: Callable[[__Self], Any]) -> None:
        if not callable(callback):
            raise TypeError("must be a callable object")
        self.__loop_callbacks.add(callback)

    def register_window_callback(self, window_callback: WindowCallback) -> None:
        if not isinstance(window_callback, WindowCallback):
            raise TypeError("must be a WindowCallback object")
        if window_callback.master is not self:
            raise ValueError("window callback's master is not self")
        if window_callback not in self.__callback_after:
            self.__callback_after.append(window_callback)

    def clear(self, color: ColorValue = BLACK, *, blend_alpha: bool = False) -> None:
        screen = self.__display_renderer
        if screen is None:
            raise WindowError("No active renderer")
        if blend_alpha and (color := Color(color)).a < 255:
            fake_screen: Surface = create_surface(screen.get_size(), default_color=color)
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

    def refresh(self) -> None:
        screen = self.__display_renderer
        if screen is None:
            raise WindowError("No active renderer")
        screen.present()

    def draw(self, *targets: SupportsDrawing) -> None:
        renderer = self.__display_renderer
        if renderer is None:
            raise WindowError("No active renderer")
        for target in targets:
            target.draw_onto(renderer)

    def take_screenshot(self) -> None:
        self.__screenshot_threads.append(self.__screenshot_thread())

    @thread_factory_method(global_lock=True, shared_lock=True)
    def __screenshot_thread(self) -> None:
        renderer = self.__display_renderer
        if renderer is None:
            raise WindowError("No active renderer")
        screen: Surface = renderer.get_screen_copy()
        filename_fmt: str = self.get_screenshot_filename_format()
        extension: str = ".png"

        import ntpath
        import posixpath

        if any(c in filename_fmt for c in {posixpath.sep, ntpath.sep}):
            raise ValueError("filename format contains invalid characters")

        screenshot_dir: str = os.path.abspath(os.path.realpath(self.get_screenshot_directory()))
        os.makedirs(screenshot_dir, exist_ok=True)

        filename_fmt = os.path.join(screenshot_dir, filename_fmt)
        date = datetime.now()
        file: str = ""
        try:
            set_constant_file(date.strftime(f"{filename_fmt}{extension}"), raise_error=True)
            for i in itertools_count(start=1):
                set_constant_file(date.strftime(f"{filename_fmt}_{i}{extension}"), raise_error=True)
        except ConstantFileNotFoundError as exc:
            file = str(exc.filename)
        save_image(screen, file)
        self.post_event(ScreenshotEvent(file=file))

    def get_screenshot_filename_format(self) -> str:
        return "Screenshot_%Y-%m-%d_%H-%M-%S"

    def get_screenshot_directory(self) -> str:
        return os.path.join(os.path.dirname(get_executable_path()), "screenshots")

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

    def process_events(self) -> Generator[Event, None, None]:
        poll_event = self.__event_queue.popleft
        make_event = EventFactory.from_pygame_event
        while True:
            try:
                pg_event = poll_event()
            except IndexError:
                break
            try:
                event = make_event(pg_event, raise_if_blocked=True)
            except UnknownEventTypeError:
                if EventFactory.NOEVENT < pg_event.type < EventFactory.USEREVENT:  # pygame's built-in event
                    _pg_event.set_blocked(pg_event.type)
                continue
            except EventFactoryError:
                continue
            yield event

    @final
    def post_event(self, event: Event) -> bool:
        return _pg_event.post(EventFactory.make_pygame_event(event))

    def register_mouse_position_callback(self: __Self, callback: Callable[[__Self, tuple[int, int]], Any]) -> None:
        if not callable(callback):
            raise TypeError("must be a callable object")
        self.__mouse_position_callbacks.add(callback)

    @final
    def get_cursor(self) -> Cursor:
        return Cursor(_pg_mouse.get_cursor())

    @final
    def set_cursor(self, cursor: Cursor, *, nb_frames: int = 0) -> None:
        if nb_frames <= 0:
            self.__context_cursor = None
            _pg_mouse.set_cursor(cursor)
            return
        context_cursor = self.__context_cursor
        if context_cursor is None:
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
        size = (width, height)
        renderer = self.__display_renderer
        if renderer is None:
            raise WindowError("No active renderer")
        screen: Surface = renderer._get_screen_surface()
        if size == screen.get_size():
            return
        flags: int = self.__flags
        vsync: bool = self.__vsync
        screen = _pg_display.set_mode(size, flags=flags, vsync=vsync)
        self.__rect = ImmutableRect.convert(screen.get_rect())

    @final
    def set_width(self, width: int) -> None:
        renderer = self.__display_renderer
        if renderer is None:
            raise WindowError("No active renderer")
        return self.set_size((width, renderer._get_screen_surface().get_height()))

    @final
    def set_height(self, height: int) -> None:
        renderer = self.__display_renderer
        if renderer is None:
            raise WindowError("No active renderer")
        return self.set_size((renderer._get_screen_surface().get_width(), height))

    @final
    def event_grabbed(self) -> bool:
        return bool(_pg_event.get_grab())

    @final
    def set_event_grab(self, state: bool) -> None:
        _pg_event.set_grab(bool(state))

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
    def renderer(self) -> WindowRenderer:
        renderer = self.__display_renderer
        if renderer is None:
            raise WindowError("No active renderer")
        return renderer

    @property
    def framerate(self) -> float:
        return self.__main_clock.get_fps()

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


class WindowRenderer(AbstractRenderer):
    __slots__ = ()

    @abstractmethod
    def get_screen_copy(self) -> Surface:
        raise NotImplementedError

    @abstractmethod
    def system_rendering(self) -> ContextManager[None]:
        raise NotImplementedError

    @abstractmethod
    def capture(self, draw_on_default_at_end: bool) -> ContextManager[Surface]:
        raise NotImplementedError

    @abstractmethod
    def is_capturing(self) -> bool:
        raise NotImplementedError


class _FramerateManager:
    __slots__ = (
        "Time",
        "get_ticks",
        "delay",
        "wait",
        "__fps",
        "__fps_count",
        "__fps_tick",
        "__last_tick",
    )

    def __init__(self) -> None:
        self.Time = Time
        self.get_ticks = Time.get_ticks
        self.delay = Time.delay
        self.wait = Time.wait
        self.__fps: float = 0
        self.__fps_count: int = 0
        self.__fps_tick: float = self.get_ticks()
        self.__last_tick: float = self.__fps_tick

    def tick(self, framerate: int = 0, use_accurate_delay: bool = False) -> float:
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
        if self.__loop:
            callback(*args, **(kwargs or {}))  # At least a 1st call

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
            master = self.__master
        except AttributeError:
            return
        with suppress(AttributeError):
            del self.__master, self.__args, self.__kwargs, self.__callback, self.__clock
        master._remove_window_callback(self)

    @property
    def master(self) -> Window:
        return self.__master


class _WindowCallbackList(list[WindowCallback]):
    def process(self) -> None:
        if not self:
            return
        for callback in tuple(self):
            callback()


@final
class _WindowRendererImpl(AbstractSurfaceRenderer, WindowRenderer):
    __slots__ = (
        "__target",
        "__capture_queue",
        "__last_frame",
        "__system_surface",
        "__system_surface_cache",
        "__get_screen",
        "__update_window",
    )

    def __init__(self) -> None:
        screen: Surface | None = _pg_display.get_surface()
        if screen is None:
            raise _pg_error("No display mode configured")
        self.__get_screen = _pg_display.get_surface
        self.__capture_queue: deque[Surface] = deque()
        self.__last_frame: Surface | None = None
        self.__system_surface: Surface | None = None
        self.__system_surface_cache: Surface = create_surface(screen.get_size())
        self.__update_window = _pg_display.flip
        self.__target: Surface = screen
        super().__init__()

    def get_target(self) -> Surface:
        return self.__target

    def _resize(self) -> None:
        new_surface = screen = self._get_screen_surface()
        if (system_surface := self.__system_surface) is not None:
            self.__system_surface_cache = self.__system_surface = new_system_surface = create_surface(screen.get_size())
            new_system_surface.blit(system_surface, (0, 0))
            if self.__target is system_surface:
                new_surface = new_system_surface
        if self.__capture_queue:
            return
        self.__target = new_surface

    def present(self) -> None:
        system_surface = self.__system_surface
        if self.__capture_queue or system_surface is not None:
            screen = self._get_screen_surface()
            used_target = self.__target
            if system_surface is not None:
                if used_target is system_surface:
                    raise WindowError("Screen refresh occured in system display context")
                self.__last_frame = screen.copy()
                screen.blit(system_surface, (0, 0))
                system_surface.fill((0, 0, 0, 0))
                self.__system_surface = None
            else:
                screen.fill((0, 0, 0))
                screen.blit(used_target, (0, 0))
                self.__last_frame = None
        else:
            self.__last_frame = None
        self.__update_window()

    def get_screen_copy(self) -> Surface:
        return (self.__last_frame or self._get_screen_surface()).copy()

    @contextmanager
    def capture(self, draw_on_default_at_end: bool) -> Iterator[Surface]:
        if self.__target is self.__system_surface:
            raise WindowError("Screen capturing disabled in system display context")

        capture_queue = self.__capture_queue

        captured_surface = self.__target.copy()
        self.__target = captured_surface
        capture_queue.append(captured_surface)
        try:
            yield captured_surface
        finally:
            capture_queue.pop()
            try:
                default_surface = capture_queue[-1]
            except IndexError:
                default_surface = self._get_screen_surface()
            self.__target = default_surface
            if draw_on_default_at_end:
                default_surface.blit(captured_surface, (0, 0))

    def is_capturing(self) -> bool:
        return bool(self.__capture_queue)

    @contextmanager
    def system_rendering(self) -> Iterator[None]:
        if self.__capture_queue:
            raise WindowError("system display disabled in screen capturing context")

        if (system_surface := self.__system_surface) is None:
            self.__system_surface = system_surface = self.__system_surface_cache
        elif self.__target is system_surface:
            yield
            return

        self.__target = system_surface
        try:
            yield
        finally:
            self.__target = self._get_screen_surface()

    def _get_screen_surface(self) -> Surface:
        screen: Surface | None = self.__get_screen()
        assert screen is not None, "No display mode configured"
        return screen


@dataclass
class _TemporaryCursor:
    cursor: Cursor
    replaced_cursor: Cursor
    nb_frames: int
