# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventTypeNotRegisteredError",
    "JoyAxisMotionEvent",
    "JoyBallMotionEvent",
    "JoyButtonDownEvent",
    "JoyButtonEvent",
    "JoyButtonUpEvent",
    "JoyDeviceAddedEvent",
    "JoyDeviceRemovedEvent",
    "JoyHatMotionEvent",
    "KeyDownEvent",
    "KeyEvent",
    "KeyUpEvent",
    "MouseButtonDownEvent",
    "MouseButtonEvent",
    "MouseButtonUpEvent",
    "MouseEvent",
    "MouseMotionEvent",
    "MouseWheelEvent",
    "MusicEndEvent",
    "TextEditingEvent",
    "TextEvent",
    "TextInputEvent",
    "UnknownEventTypeError",
    "UserEvent",
    "WindowEnterEvent",
    "WindowExposedEvent",
    "WindowFocusGainedEvent",
    "WindowFocusLostEvent",
    "WindowHiddenEvent",
    "WindowLeaveEvent",
    "WindowMaximizedEvent",
    "WindowMinimizedEvent",
    "WindowMovedEvent",
    "WindowResizedEvent",
    "WindowRestoredEvent",
    "WindowShownEvent",
    "WindowSizeChangedEvent",
    "WindowTakeFocusEvent",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import suppress
from dataclasses import dataclass, field, fields
from enum import IntEnum, unique
from operator import truth
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Final, Literal, Sequence, TypeAlias, TypeVar, cast

import pygame.constants as _pg_constants
from pygame.event import Event as _PygameEvent, event_name as _pg_event_name, get_blocked as _pg_event_get_blocked

from ..audio.music import Music, MusicStream
from ..system.namespace import ClassNamespaceMeta
from .keyboard import Keyboard
from .mouse import Mouse

_T = TypeVar("_T")


class _EventMeta(type):
    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _EventMeta:
        try:
            EventFactory
        except NameError:
            pass
        else:
            raise TypeError("Trying to create custom event")
        try:
            Event
        except NameError:
            pass
        else:
            if bases != (Event,):
                raise TypeError(f"{name!r} must only inherits from Event without multiple inheritance")
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls is Event:
            raise TypeError("Cannot instantiate base class Event")
        return super().__call__(*args, **kwargs)


@dataclass(frozen=True, kw_only=True, slots=True)
class Event(metaclass=_EventMeta):
    @unique
    class Type(IntEnum):
        # Built-in events
        KEYDOWN = _pg_constants.KEYDOWN
        KEYUP = _pg_constants.KEYUP
        MOUSEMOTION = _pg_constants.MOUSEMOTION
        MOUSEBUTTONUP = _pg_constants.MOUSEBUTTONUP
        MOUSEBUTTONDOWN = _pg_constants.MOUSEBUTTONDOWN
        MOUSEWHEEL = _pg_constants.MOUSEWHEEL
        JOYAXISMOTION = _pg_constants.JOYAXISMOTION
        JOYBALLMOTION = _pg_constants.JOYBALLMOTION
        JOYHATMOTION = _pg_constants.JOYHATMOTION
        JOYBUTTONUP = _pg_constants.JOYBUTTONUP
        JOYBUTTONDOWN = _pg_constants.JOYBUTTONDOWN
        JOYDEVICEADDED = _pg_constants.JOYDEVICEADDED
        JOYDEVICEREMOVED = _pg_constants.JOYDEVICEREMOVED
        USEREVENT = _pg_constants.USEREVENT
        TEXTEDITING = _pg_constants.TEXTEDITING
        TEXTINPUT = _pg_constants.TEXTINPUT
        WINDOWSHOWN = _pg_constants.WINDOWSHOWN
        WINDOWHIDDEN = _pg_constants.WINDOWHIDDEN
        WINDOWEXPOSED = _pg_constants.WINDOWEXPOSED
        WINDOWMOVED = _pg_constants.WINDOWMOVED
        WINDOWRESIZED = _pg_constants.WINDOWRESIZED
        WINDOWSIZECHANGED = _pg_constants.WINDOWSIZECHANGED
        WINDOWMINIMIZED = _pg_constants.WINDOWMINIMIZED
        WINDOWMAXIMIZED = _pg_constants.WINDOWMAXIMIZED
        WINDOWRESTORED = _pg_constants.WINDOWRESTORED
        WINDOWENTER = _pg_constants.WINDOWENTER
        WINDOWLEAVE = _pg_constants.WINDOWLEAVE
        WINDOWFOCUSGAINED = _pg_constants.WINDOWFOCUSGAINED
        WINDOWFOCUSLOST = _pg_constants.WINDOWFOCUSLOST
        WINDOWTAKEFOCUS = _pg_constants.WINDOWTAKEFOCUS

        # Custom events
        MUSICEND = MusicStream.MUSICEND

        def __repr__(self) -> str:
            return f"<{self.name} ({self.real_name}): {self.value}>"

        def __str__(self) -> str:
            return self.real_name

        def is_allowed(self) -> bool:
            return not _pg_event_get_blocked(self)

        def is_blocked(self) -> bool:
            return truth(_pg_event_get_blocked(self))

        @property
        def real_name(self) -> str:
            return _pg_event_name(self)

    type: ClassVar[Event.Type] = field(init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class KeyDownEvent(Event):
    type: ClassVar[Literal[Event.Type.KEYDOWN]] = field(default=Event.Type.KEYDOWN, init=False)
    key: int
    mod: int
    unicode: str
    scancode: int


@dataclass(frozen=True, kw_only=True, slots=True)
class KeyUpEvent(Event):
    type: ClassVar[Literal[Event.Type.KEYUP]] = field(default=Event.Type.KEYUP, init=False)
    key: int
    mod: int


KeyEvent: TypeAlias = KeyDownEvent | KeyUpEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseButtonDownEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEBUTTONDOWN]] = field(default=Event.Type.MOUSEBUTTONDOWN, init=False)
    pos: tuple[int, int]
    button: int


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseButtonUpEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEBUTTONUP]] = field(default=Event.Type.MOUSEBUTTONUP, init=False)
    pos: tuple[int, int]
    button: int


MouseButtonEvent: TypeAlias = MouseButtonDownEvent | MouseButtonUpEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseMotionEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEMOTION]] = field(default=Event.Type.MOUSEMOTION, init=False)
    pos: tuple[int, int]
    rel: tuple[int, int]
    buttons: tuple[bool, bool, bool]


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseWheelEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEWHEEL]] = field(default=Event.Type.MOUSEWHEEL, init=False)
    flipped: bool
    x: int
    y: int


MouseEvent: TypeAlias = MouseButtonEvent | MouseWheelEvent | MouseMotionEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyAxisMotionEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYAXISMOTION]] = field(default=Event.Type.JOYAXISMOTION, init=False)
    instance_id: int
    axis: int
    value: float


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyBallMotionEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYBALLMOTION]] = field(default=Event.Type.JOYBALLMOTION, init=False)
    instance_id: int
    ball: int
    rel: float


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyHatMotionEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYHATMOTION]] = field(default=Event.Type.JOYHATMOTION, init=False)
    instance_id: int
    hat: int
    value: tuple[int, int]


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyButtonDownEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYBUTTONDOWN]] = field(default=Event.Type.JOYBUTTONDOWN, init=False)
    instance_id: int
    button: int


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyButtonUpEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYBUTTONUP]] = field(default=Event.Type.JOYBUTTONUP, init=False)
    instance_id: int
    button: int


JoyButtonEvent: TypeAlias = JoyButtonDownEvent | JoyButtonUpEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyDeviceAddedEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYDEVICEADDED]] = field(default=Event.Type.JOYDEVICEADDED, init=False)
    device_index: int


@dataclass(frozen=True, kw_only=True, slots=True)
class JoyDeviceRemovedEvent(Event):
    type: ClassVar[Literal[Event.Type.JOYDEVICEREMOVED]] = field(default=Event.Type.JOYDEVICEREMOVED, init=False)
    instance_id: int


@dataclass(frozen=True, kw_only=True, slots=True)
class TextEditingEvent(Event):
    type: ClassVar[Literal[Event.Type.TEXTEDITING]] = field(default=Event.Type.TEXTEDITING, init=False)
    text: str
    start: int
    length: int


@dataclass(frozen=True, kw_only=True, slots=True)
class TextInputEvent(Event):
    type: ClassVar[Literal[Event.Type.TEXTINPUT]] = field(default=Event.Type.TEXTINPUT, init=False)
    text: str


TextEvent: TypeAlias = TextEditingEvent | TextInputEvent


@dataclass(frozen=True, kw_only=True, slots=True)
class UserEvent(Event):
    type: ClassVar[Literal[Event.Type.USEREVENT]] = field(default=Event.Type.USEREVENT, init=False)
    code: int = -1


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowShownEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWSHOWN]] = field(default=Event.Type.WINDOWSHOWN, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowHiddenEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWHIDDEN]] = field(default=Event.Type.WINDOWHIDDEN, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowExposedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWEXPOSED]] = field(default=Event.Type.WINDOWEXPOSED, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowMovedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWMOVED]] = field(default=Event.Type.WINDOWMOVED, init=False)
    x: int
    y: int


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowResizedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWRESIZED]] = field(default=Event.Type.WINDOWRESIZED, init=False)
    x: int
    y: int


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowSizeChangedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWSIZECHANGED]] = field(default=Event.Type.WINDOWSIZECHANGED, init=False)
    x: int
    y: int


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowMinimizedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWMINIMIZED]] = field(default=Event.Type.WINDOWMINIMIZED, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowMaximizedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWMAXIMIZED]] = field(default=Event.Type.WINDOWMAXIMIZED, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowRestoredEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWRESTORED]] = field(default=Event.Type.WINDOWRESTORED, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowEnterEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWENTER]] = field(default=Event.Type.WINDOWENTER, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowLeaveEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWLEAVE]] = field(default=Event.Type.WINDOWLEAVE, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowFocusGainedEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWFOCUSGAINED]] = field(default=Event.Type.WINDOWFOCUSGAINED, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowFocusLostEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWFOCUSLOST]] = field(default=Event.Type.WINDOWFOCUSLOST, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class WindowTakeFocusEvent(Event):
    type: ClassVar[Literal[Event.Type.WINDOWTAKEFOCUS]] = field(default=Event.Type.WINDOWTAKEFOCUS, init=False)


@dataclass(frozen=True, kw_only=True, slots=True)
class MusicEndEvent(Event):
    type: ClassVar[Literal[Event.Type.MUSICEND]] = field(default=Event.Type.MUSICEND, init=False)
    finished: Music
    next: Music | None


_EventCallback: TypeAlias = Callable[[Event], bool | None]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback: TypeAlias = Callable[[tuple[float, float]], None]


class EventFactoryError(Exception):
    pass


class UnknownEventTypeError(EventFactoryError):
    pass


class EventTypeNotRegisteredError(EventFactoryError):
    pass


class EventFactory(metaclass=ClassNamespaceMeta, frozen=True):
    associations: Final[MappingProxyType[Event.Type, type[Event]]] = MappingProxyType(
        {obj.type: obj for obj in globals().values() if isinstance(obj, type) and issubclass(obj, Event) and obj is not Event}
    )

    @staticmethod
    def from_pygame_event(event: _PygameEvent) -> Event:
        try:
            event_type = Event.Type(event.type)
            event_cls: type[Event] = EventFactory.associations[event_type]
        except ValueError as exc:
            raise UnknownEventTypeError(f"Unknown event {event!r}") from exc
        except KeyError as exc:
            raise EventTypeNotRegisteredError(f"Unknown event {event!r}") from exc
        event_fields: Sequence[str] = tuple(f.name for f in fields(event_cls))
        kwargs: dict[str, Any] = {k: event.__dict__[k] for k in filter(event_fields.__contains__, event.__dict__)}
        return event_cls(**kwargs)


class EventManager:

    __slots__ = (
        "__event_handler_dict",
        "__key_pressed_handler_dict",
        "__key_released_handler_dict",
        "__mouse_button_pressed_handler_dict",
        "__mouse_button_released_handler_dict",
        "__mouse_pos_handler_list",
        "__other_manager_list",
    )

    def __init__(self) -> None:
        self.__event_handler_dict: dict[Event.Type, list[_EventCallback]] = dict()
        self.__key_pressed_handler_dict: dict[Keyboard.Key, list[_EventCallback]] = dict()
        self.__key_released_handler_dict: dict[Keyboard.Key, list[_EventCallback]] = dict()
        self.__mouse_button_pressed_handler_dict: dict[Mouse.Button, list[_EventCallback]] = dict()
        self.__mouse_button_released_handler_dict: dict[Mouse.Button, list[_EventCallback]] = dict()
        self.__mouse_pos_handler_list: list[_MousePositionCallback] = list()
        self.__other_manager_list: list[EventManager] = list()

    @staticmethod
    def __bind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        try:
            event_list: list[_EventCallback] = handler_dict[key]
        except KeyError:
            handler_dict[key] = event_list = []
        if callback not in event_list:
            event_list.append(cast(_EventCallback, callback))

    @staticmethod
    def __unbind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        with suppress(KeyError, ValueError):
            handler_dict[key].remove(cast(_EventCallback, callback))

    def bind(self, event_cls: type[_TE], callback: Callable[[_TE], bool | None]) -> None:
        EventManager.__bind(self.__event_handler_dict, event_cls.type, callback)

    def unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_TE], bool | None]) -> None:
        EventManager.__unbind(self.__event_handler_dict, event_cls.type, callback_to_remove)

    def unbind_all(self) -> None:
        self.__event_handler_dict.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()

    def bind_key(self, key: Keyboard.Key, callback: Callable[[KeyEvent], bool | None]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, key: Keyboard.Key, callback: Callable[[KeyDownEvent], bool | None]) -> None:
        EventManager.__bind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback)

    def bind_key_release(self, key: Keyboard.Key, callback: Callable[[KeyUpEvent], bool | None]) -> None:
        EventManager.__bind(self.__key_released_handler_dict, Keyboard.Key(key), callback)

    def unbind_key(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyEvent], bool | None]) -> None:
        self.unbind_key_press(key, callback_to_remove)
        self.unbind_key_release(key, callback_to_remove)

    def unbind_key_press(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyDownEvent], bool | None]) -> None:
        EventManager.__unbind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback_to_remove)

    def unbind_key_release(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyUpEvent], bool | None]) -> None:
        EventManager.__unbind(self.__key_released_handler_dict, Keyboard.Key(key), callback_to_remove)

    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[[MouseButtonEvent], bool | None]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(self, button: Mouse.Button, callback: Callable[[MouseButtonDownEvent], bool | None]) -> None:
        EventManager.__bind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback)

    def bind_mouse_button_release(self, button: Mouse.Button, callback: Callable[[MouseButtonUpEvent], bool | None]) -> None:
        EventManager.__bind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback)

    def unbind_mouse_button(self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonEvent], bool | None]) -> None:
        self.unbind_mouse_button_press(button, callback_to_remove)
        self.unbind_mouse_button_release(button, callback_to_remove)

    def unbind_mouse_button_press(
        self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonDownEvent], bool | None]
    ) -> None:
        EventManager.__unbind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback_to_remove)

    def unbind_mouse_button_release(
        self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonUpEvent], bool | None]
    ) -> None:
        EventManager.__unbind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback_to_remove)

    def bind_mouse_position(self, callback: _MousePositionCallback) -> None:
        mouse_pos_handler_list: list[_MousePositionCallback] = self.__mouse_pos_handler_list
        if callback not in mouse_pos_handler_list:
            mouse_pos_handler_list.append(callback)

    def unbind_mouse_position(self, callback_to_remove: _MousePositionCallback) -> None:
        mouse_pos_handler_list: list[_MousePositionCallback] = self.__mouse_pos_handler_list
        with suppress(ValueError):
            mouse_pos_handler_list.remove(callback_to_remove)

    def bind_event_manager(self, manager: EventManager) -> None:
        other_manager_list: list[EventManager] = self.__other_manager_list
        if manager not in other_manager_list:
            other_manager_list.append(manager)

    def unbind_event_manager(self, manager: EventManager) -> None:
        other_manager_list: list[EventManager] = self.__other_manager_list
        with suppress(ValueError):
            other_manager_list.remove(manager)

    def process_event(self, event: Event) -> bool:
        if isinstance(event, (KeyUpEvent, KeyDownEvent)):
            if self.__handle_key_event(event):
                return True
        elif isinstance(event, (MouseButtonUpEvent, MouseButtonDownEvent)):
            if self.__handle_mouse_event(event):
                return True
        event_dict: dict[Event.Type, list[_EventCallback]] = self.__event_handler_dict
        for callback in event_dict.get(event.type, ()):
            if callback(event):
                return True
        for manager in self.__other_manager_list:
            if manager.process_event(event):
                return True
        return False

    def handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)
        for manager in self.__other_manager_list:
            manager.handle_mouse_position(mouse_pos)

    def __handle_key_event(self, event: KeyEvent) -> bool | None:
        key_handler_dict: dict[Keyboard.Key, list[_EventCallback]] | None = None
        if event.type == Event.Type.KEYDOWN:
            key_handler_dict = self.__key_pressed_handler_dict
        elif event.type == Event.Type.KEYUP:
            key_handler_dict = self.__key_released_handler_dict
        if key_handler_dict:
            try:
                key = Keyboard.Key(event.key)
            except ValueError:
                return None
            for callback in key_handler_dict.get(key, ()):
                output: bool | None = callback(event)
                if output:
                    return output
        return None

    def __handle_mouse_event(self, event: MouseButtonEvent) -> bool | None:
        mouse_handler_dict: dict[Mouse.Button, list[_EventCallback]] | None = None
        if event.type == Event.Type.MOUSEBUTTONDOWN:
            mouse_handler_dict = self.__mouse_button_pressed_handler_dict
        elif event.type == Event.Type.MOUSEBUTTONUP:
            mouse_handler_dict = self.__mouse_button_released_handler_dict
        if mouse_handler_dict:
            try:
                mouse_button = Mouse.Button(event.button)
            except ValueError:
                return None
            for callback in mouse_handler_dict.get(mouse_button, ()):
                output: bool | None = callback(event)
                if output:
                    return output
        return None


del _pg_constants, _EventMeta, MusicStream

del _T, _TE
