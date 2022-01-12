# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "Event",
    "EventFactory",
    "EventManager",
    "JoyAxisMotionEvent",
    "JoyBallMotionEvent",
    "JoyButtonDownEvent",
    "JoyButtonEventType",
    "JoyButtonUpEvent",
    "JoyDeviceAddedEvent",
    "JoyDeviceRemovedEvent",
    "JoyHatMotionEvent",
    "KeyDownEvent",
    "KeyEventType",
    "KeyUpEvent",
    "MouseButtonDownEvent",
    "MouseButtonEventType",
    "MouseButtonUpEvent",
    "MouseEventType",
    "MouseMotionEvent",
    "MouseWheelEvent",
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
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import suppress
from dataclasses import dataclass, field, fields
from enum import IntEnum
from types import MappingProxyType
from typing import Any, Callable, ClassVar, Dict, Final, List, Literal, Optional, Sequence, Tuple, Type, TypeVar, Union, cast

import pygame.constants as _pg_constants
from pygame.event import Event as _PygameEvent, event_name as _pg_event_name, get_blocked as _pg_event_get_blocked

from .keyboard import Keyboard
from .mouse import Mouse

_T = TypeVar("_T")


class UnknownEventTypeError(TypeError):
    pass


class _MetaEvent(type):
    def __new__(metacls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> _MetaEvent:
        if name != "Event" or "Event" in globals():
            if bases != (Event,):
                raise TypeError(f"{name!r} must only inherits from Event without multiple inheritance")
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls is Event:
            raise TypeError("Cannot instantiate base class Event")
        return super().__call__(*args, **kwargs)


@dataclass(frozen=True, kw_only=True, slots=True)
class Event(metaclass=_MetaEvent):
    class Type(IntEnum):
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

        value: int

        def __repr__(self) -> str:
            return f"<{self.real_name}: {self.value}>"

        def __str__(self) -> str:
            return self.real_name

        def is_allowed(self) -> bool:
            return not _pg_event_get_blocked(self)

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


KeyEventType = Union[KeyDownEvent, KeyUpEvent]


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseButtonDownEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEBUTTONDOWN]] = field(default=Event.Type.MOUSEBUTTONDOWN, init=False)
    pos: Tuple[int, int]
    button: int


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseButtonUpEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEBUTTONUP]] = field(default=Event.Type.MOUSEBUTTONUP, init=False)
    pos: Tuple[int, int]
    button: int


MouseButtonEventType = Union[MouseButtonDownEvent, MouseButtonUpEvent]


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseMotionEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEMOTION]] = field(default=Event.Type.MOUSEMOTION, init=False)
    pos: Tuple[int, int]
    rel: Tuple[int, int]
    buttons: Tuple[bool, bool, bool]


@dataclass(frozen=True, kw_only=True, slots=True)
class MouseWheelEvent(Event):
    type: ClassVar[Literal[Event.Type.MOUSEWHEEL]] = field(default=Event.Type.MOUSEWHEEL, init=False)
    flipped: bool
    x: int
    y: int


MouseEventType = Union[MouseButtonEventType, MouseWheelEvent, MouseMotionEvent]


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
    value: Tuple[int, int]


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


JoyButtonEventType = Union[JoyButtonDownEvent, JoyButtonUpEvent]


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


TextEvent = Union[TextEditingEvent, TextInputEvent]


@dataclass(frozen=True, kw_only=True, slots=True)
class UserEvent(Event):
    type: ClassVar[Literal[Event.Type.USEREVENT]] = field(default=Event.Type.USEREVENT, init=False)
    code: int


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


_EventCallback = Callable[[Event], Optional[bool]]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback = Callable[[Tuple[float, float]], None]


class EventFactory:
    associations: Final[MappingProxyType[Event.Type, Type[Event]]] = MappingProxyType(
        {obj.type: obj for obj in globals().values() if isinstance(obj, type) and issubclass(obj, Event) and obj is not Event}
    )

    __slots__ = ()

    @staticmethod
    def from_pygame_event(event: _PygameEvent) -> Event:
        try:
            event_type = Event.Type(event.type)
            event_cls: Type[Event] = EventFactory.associations[event_type]
        except (KeyError, ValueError) as exc:
            raise UnknownEventTypeError(f"Unknown event {event!r}") from exc
        event_fields: Sequence[str] = tuple(f.name for f in fields(event_cls))
        kwargs: Dict[str, Any] = {k: event.__dict__[k] for k in filter(event_fields.__contains__, event.__dict__)}
        return event_cls(**kwargs)


class EventManager:

    __slots__ = (
        "__event_handler_dict",
        "__key_pressed_handler_dict",
        "__key_released_handler_dict",
        "__mouse_button_pressed_handler_dict",
        "__mouse_button_released_handler_dict",
        "__mouse_pos_handler_list",
    )

    def __init__(self) -> None:
        self.__event_handler_dict: Dict[Event.Type, List[_EventCallback]] = dict()
        self.__key_pressed_handler_dict: Dict[Keyboard.Key, List[_EventCallback]] = dict()
        self.__key_released_handler_dict: Dict[Keyboard.Key, List[_EventCallback]] = dict()
        self.__mouse_button_pressed_handler_dict: Dict[Mouse.Button, List[_EventCallback]] = dict()
        self.__mouse_button_released_handler_dict: Dict[Mouse.Button, List[_EventCallback]] = dict()
        self.__mouse_pos_handler_list: List[_MousePositionCallback] = list()

    @staticmethod
    def __bind(handler_dict: Dict[_T, List[_EventCallback]], key: _T, callback: Callable[[_TE], Optional[bool]]) -> None:
        try:
            event_list: List[_EventCallback] = handler_dict[key]
        except KeyError:
            handler_dict[key] = event_list = []
        if callback not in event_list:
            event_list.append(cast(_EventCallback, callback))

    @staticmethod
    def __unbind(handler_dict: Dict[_T, List[_EventCallback]], key: _T, callback: Callable[[_TE], Optional[bool]]) -> None:
        with suppress(KeyError, ValueError):
            handler_dict[key].remove(cast(_EventCallback, callback))

    def bind_event(self, event_cls: Type[_TE], callback: Callable[[_TE], Optional[bool]]) -> None:
        EventManager.__bind(self.__event_handler_dict, event_cls.type, callback)

    def unbind_event(self, event_cls: Type[_TE], callback_to_remove: Callable[[_TE], Optional[bool]]) -> None:
        EventManager.__unbind(self.__event_handler_dict, event_cls.type, callback_to_remove)

    def unbind_all(self) -> None:
        self.__event_handler_dict.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()

    def bind_key(self, key: Keyboard.Key, callback: Callable[[KeyEventType], Optional[bool]]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, key: Keyboard.Key, callback: Callable[[KeyDownEvent], Optional[bool]]) -> None:
        EventManager.__bind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback)

    def bind_key_release(self, key: Keyboard.Key, callback: Callable[[KeyUpEvent], Optional[bool]]) -> None:
        EventManager.__bind(self.__key_released_handler_dict, Keyboard.Key(key), callback)

    def unbind_key(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyEventType], Optional[bool]]) -> None:
        self.unbind_key_press(key, callback_to_remove)
        self.unbind_key_release(key, callback_to_remove)

    def unbind_key_press(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyDownEvent], Optional[bool]]) -> None:
        EventManager.__unbind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback_to_remove)

    def unbind_key_release(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyUpEvent], Optional[bool]]) -> None:
        EventManager.__unbind(self.__key_released_handler_dict, Keyboard.Key(key), callback_to_remove)

    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[[MouseButtonEventType], Optional[bool]]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(self, button: Mouse.Button, callback: Callable[[MouseButtonDownEvent], Optional[bool]]) -> None:
        EventManager.__bind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback)

    def bind_mouse_button_release(self, button: Mouse.Button, callback: Callable[[MouseButtonUpEvent], Optional[bool]]) -> None:
        EventManager.__bind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback)

    def unbind_mouse_button(
        self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonEventType], Optional[bool]]
    ) -> None:
        self.unbind_mouse_button_press(button, callback_to_remove)
        self.unbind_mouse_button_release(button, callback_to_remove)

    def unbind_mouse_button_press(
        self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonDownEvent], Optional[bool]]
    ) -> None:
        EventManager.__unbind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback_to_remove)

    def unbind_mouse_button_release(
        self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonUpEvent], Optional[bool]]
    ) -> None:
        EventManager.__unbind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback_to_remove)

    def bind_mouse_position(self, callback: _MousePositionCallback) -> None:
        mouse_pos_handler_list: List[_MousePositionCallback] = self.__mouse_pos_handler_list
        if callback not in mouse_pos_handler_list:
            mouse_pos_handler_list.append(callback)

    def unbind_mouse_position(self, callback_to_remove: _MousePositionCallback) -> None:
        mouse_pos_handler_list: List[_MousePositionCallback] = self.__mouse_pos_handler_list
        with suppress(ValueError):
            mouse_pos_handler_list.remove(callback_to_remove)

    def process_event(self, event: Event) -> bool:
        if isinstance(event, (KeyUpEvent, KeyDownEvent)):
            if self.__handle_key_event(event):
                return True
        elif isinstance(event, (MouseButtonUpEvent, MouseButtonDownEvent)):
            if self.__handle_mouse_event(event):
                return True
        event_dict: Dict[Event.Type, List[_EventCallback]] = self.__event_handler_dict
        for callback in event_dict.get(event.type, ()):
            if callback(event):
                return True
        return False

    def handle_mouse_position(self) -> None:
        mouse_pos: Tuple[float, float] = Mouse.get_pos()
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)

    def __handle_key_event(self, event: KeyEventType) -> Optional[bool]:
        key_handler_dict: Optional[Dict[Keyboard.Key, List[_EventCallback]]] = None
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
                output: Optional[bool] = callback(event)
                if output:
                    return output
        return None

    def __handle_mouse_event(self, event: MouseButtonEventType) -> Optional[bool]:
        mouse_handler_dict: Optional[Dict[Mouse.Button, List[_EventCallback]]] = None
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
                output: Optional[bool] = callback(event)
                if output:
                    return output
        return None


del _pg_constants
