# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "Event",
    "EventManager",
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
    "MetaEvent",
    "MouseButtonDownEvent",
    "MouseButtonEvent",
    "MouseButtonUpEvent",
    "MouseEvent",
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
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple, Type, TypeVar, Union, cast, overload

import pygame
from pygame.event import Event as _PygameEvent

from .keyboard import Keyboard
from .mouse import Mouse

_T = TypeVar("_T")


class UnknownEventTypeError(TypeError):
    pass


class MetaEvent(type):
    __associations: Dict[Event.Type, Type[Event]] = dict()

    def __new__(
        metacls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], *, event_type: Event.Type, **kwargs: Any
    ) -> MetaEvent:
        if name != "Event" or "Event" in globals():
            if bases != (Event,):
                raise TypeError(f"{name!r} must only inherits from Event without multiple inheritance")
            event_type = Event.Type(event_type)
            if event_type in metacls.__associations:
                raise TypeError(f"There is already a class with this type: {event_type}")
            annotations = namespace.setdefault("__annotations__", {})
            annotations["type"] = Event.Type
            namespace["type"] = field(default=event_type, init=False)
            cls: MetaEvent = super().__new__(metacls, name, bases, namespace, **kwargs)
            metacls.__associations[event_type] = cast(Type[Event], cls)
            return cls
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    def __call__(cls, /, *args: Any, **kwargs: Any) -> Any:
        if cls is Event:
            raise TypeError("Cannot instantiate base class Event")
        return super().__call__(*args, **kwargs)

    @staticmethod
    def from_pygame_event(event: _PygameEvent) -> Event:
        associations = MetaEvent.__associations
        try:
            event_type = Event.Type(event.type)
            event_cls: Type[Event] = associations[event_type]
        except (KeyError, ValueError) as exc:
            raise UnknownEventTypeError(f"Unknown event {event!r}") from exc
        fields = event_cls.__dataclass_fields__
        kwargs: Dict[str, Any] = {k: event.__dict__[k] for k in filter(fields.__contains__, event.__dict__)}
        return event_cls(**kwargs)


@dataclass(frozen=True)
class Event(metaclass=MetaEvent, event_type=-1):
    class Type(IntEnum):
        KEYDOWN = pygame.KEYDOWN
        KEYUP = pygame.KEYUP
        MOUSEMOTION = pygame.MOUSEMOTION
        MOUSEBUTTONUP = pygame.MOUSEBUTTONUP
        MOUSEBUTTONDOWN = pygame.MOUSEBUTTONDOWN
        MOUSEWHEEL = pygame.MOUSEWHEEL
        JOYAXISMOTION = pygame.JOYAXISMOTION
        JOYBALLMOTION = pygame.JOYBALLMOTION
        JOYHATMOTION = pygame.JOYHATMOTION
        JOYBUTTONUP = pygame.JOYBUTTONUP
        JOYBUTTONDOWN = pygame.JOYBUTTONDOWN
        JOYDEVICEADDED = pygame.JOYDEVICEADDED
        JOYDEVICEREMOVED = pygame.JOYDEVICEREMOVED
        USEREVENT = pygame.USEREVENT
        TEXTEDITING = pygame.TEXTEDITING
        TEXTINPUT = pygame.TEXTINPUT
        WINDOWSHOWN = pygame.WINDOWSHOWN
        WINDOWHIDDEN = pygame.WINDOWHIDDEN
        WINDOWEXPOSED = pygame.WINDOWEXPOSED
        WINDOWMOVED = pygame.WINDOWMOVED
        WINDOWRESIZED = pygame.WINDOWRESIZED
        WINDOWSIZECHANGED = pygame.WINDOWSIZECHANGED
        WINDOWMINIMIZED = pygame.WINDOWMINIMIZED
        WINDOWMAXIMIZED = pygame.WINDOWMAXIMIZED
        WINDOWRESTORED = pygame.WINDOWRESTORED
        WINDOWENTER = pygame.WINDOWENTER
        WINDOWLEAVE = pygame.WINDOWLEAVE
        WINDOWFOCUSGAINED = pygame.WINDOWFOCUSGAINED
        WINDOWFOCUSLOST = pygame.WINDOWFOCUSLOST
        WINDOWTAKEFOCUS = pygame.WINDOWTAKEFOCUS

        def is_allowed(self, /) -> bool:
            return not pygame.event.get_blocked(self)

        @property
        def real_name(self, /) -> str:
            return pygame.event.event_name(self)

    type: Event.Type = field(init=False)


@dataclass(frozen=True)
class KeyDownEvent(Event, event_type=Event.Type.KEYDOWN):
    key: int
    mod: int
    unicode: str
    scancode: int


@dataclass(frozen=True)
class KeyUpEvent(Event, event_type=Event.Type.KEYUP):
    key: int
    mod: int


KeyEvent = Union[KeyDownEvent, KeyUpEvent]


@dataclass(frozen=True)
class MouseButtonDownEvent(Event, event_type=Event.Type.MOUSEBUTTONDOWN):
    pos: Tuple[int, int]
    button: int


@dataclass(frozen=True)
class MouseButtonUpEvent(Event, event_type=Event.Type.MOUSEBUTTONUP):
    pos: Tuple[int, int]
    button: int


MouseButtonEvent = Union[MouseButtonDownEvent, MouseButtonUpEvent]


@dataclass(frozen=True)
class MouseMotionEvent(Event, event_type=Event.Type.MOUSEMOTION):
    pos: Tuple[int, int]
    rel: Tuple[int, int]
    buttons: Tuple[bool, bool, bool]


@dataclass(frozen=True)
class MouseWheelEvent(Event, event_type=Event.Type.MOUSEWHEEL):
    flipped: bool
    x: int
    y: int


MouseEvent = Union[MouseButtonEvent, MouseWheelEvent, MouseMotionEvent]


@dataclass(frozen=True)
class JoyAxisMotionEvent(Event, event_type=Event.Type.JOYAXISMOTION):
    instance_id: int
    axis: int
    value: float


@dataclass(frozen=True)
class JoyBallMotionEvent(Event, event_type=Event.Type.JOYBALLMOTION):
    instance_id: int
    ball: int
    rel: float


@dataclass(frozen=True)
class JoyHatMotionEvent(Event, event_type=Event.Type.JOYHATMOTION):
    instance_id: int
    hat: int
    value: Tuple[int, int]


@dataclass(frozen=True)
class JoyButtonDownEvent(Event, event_type=Event.Type.JOYBUTTONDOWN):
    instance_id: int
    button: int


@dataclass(frozen=True)
class JoyButtonUpEvent(Event, event_type=Event.Type.JOYBUTTONUP):
    instance_id: int
    button: int


JoyButtonEvent = Union[JoyButtonDownEvent, JoyButtonUpEvent]


@dataclass(frozen=True)
class JoyDeviceAddedEvent(Event, event_type=Event.Type.JOYDEVICEADDED):
    device_index: int


@dataclass(frozen=True)
class JoyDeviceRemovedEvent(Event, event_type=Event.Type.JOYDEVICEREMOVED):
    instance_id: int


@dataclass(frozen=True)
class TextEditingEvent(Event, event_type=Event.Type.TEXTEDITING):
    text: str
    start: int
    length: int


@dataclass(frozen=True)
class TextInputEvent(Event, event_type=Event.Type.TEXTINPUT):
    text: str


TextEvent = Union[TextEditingEvent, TextInputEvent]


@dataclass(frozen=True)
class UserEvent(Event, event_type=Event.Type.USEREVENT):
    code: int


@dataclass(frozen=True)
class WindowShownEvent(Event, event_type=Event.Type.WINDOWSHOWN):
    pass


@dataclass(frozen=True)
class WindowHiddenEvent(Event, event_type=Event.Type.WINDOWHIDDEN):
    pass


@dataclass(frozen=True)
class WindowExposedEvent(Event, event_type=Event.Type.WINDOWEXPOSED):
    pass


@dataclass(frozen=True)
class WindowMovedEvent(Event, event_type=Event.Type.WINDOWMOVED):
    x: int
    y: int


@dataclass(frozen=True)
class WindowResizedEvent(Event, event_type=Event.Type.WINDOWRESIZED):
    x: int
    y: int


@dataclass(frozen=True)
class WindowSizeChangedEvent(Event, event_type=Event.Type.WINDOWSIZECHANGED):
    x: int
    y: int


@dataclass(frozen=True)
class WindowMinimizedEvent(Event, event_type=Event.Type.WINDOWMINIMIZED):
    pass


@dataclass(frozen=True)
class WindowMaximizedEvent(Event, event_type=Event.Type.WINDOWMAXIMIZED):
    pass


@dataclass(frozen=True)
class WindowRestoredEvent(Event, event_type=Event.Type.WINDOWRESTORED):
    pass


@dataclass(frozen=True)
class WindowEnterEvent(Event, event_type=Event.Type.WINDOWENTER):
    pass


@dataclass(frozen=True)
class WindowLeaveEvent(Event, event_type=Event.Type.WINDOWLEAVE):
    pass


@dataclass(frozen=True)
class WindowFocusGainedEvent(Event, event_type=Event.Type.WINDOWFOCUSGAINED):
    pass


@dataclass(frozen=True)
class WindowFocusLostEvent(Event, event_type=Event.Type.WINDOWFOCUSLOST):
    pass


@dataclass(frozen=True)
class WindowTakeFocusEvent(Event, event_type=Event.Type.WINDOWTAKEFOCUS):
    pass


_EventCallback = Callable[[Event], Optional[bool]]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback = Callable[[Tuple[float, float]], None]


class EventManager:
    def __init__(self, /) -> None:
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

    @overload
    def bind_event(self, /, event_type: Literal[Event.Type.KEYDOWN], callback: Callable[[KeyDownEvent], Optional[bool]]) -> None:
        ...

    @overload
    def bind_event(self, /, event_type: Literal[Event.Type.KEYUP], callback: Callable[[KeyUpEvent], Optional[bool]]) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.MOUSEBUTTONDOWN], callback: Callable[[MouseButtonDownEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.MOUSEBUTTONUP], callback: Callable[[MouseButtonUpEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.MOUSEMOTION], callback: Callable[[MouseMotionEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.MOUSEWHEEL], callback: Callable[[MouseWheelEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYAXISMOTION], callback: Callable[[JoyAxisMotionEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYBALLMOTION], callback: Callable[[JoyBallMotionEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYHATMOTION], callback: Callable[[JoyHatMotionEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYBUTTONDOWN], callback: Callable[[JoyButtonDownEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYBUTTONUP], callback: Callable[[JoyButtonUpEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYDEVICEADDED], callback: Callable[[JoyDeviceAddedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.JOYDEVICEREMOVED], callback: Callable[[JoyDeviceRemovedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.TEXTEDITING], callback: Callable[[TextEditingEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.TEXTINPUT], callback: Callable[[TextInputEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(self, /, event_type: Literal[Event.Type.USEREVENT], callback: Callable[[UserEvent], Optional[bool]]) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWSHOWN], callback: Callable[[WindowShownEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWHIDDEN], callback: Callable[[WindowHiddenEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWEXPOSED], callback: Callable[[WindowExposedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWMOVED], callback: Callable[[WindowMovedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWRESIZED], callback: Callable[[WindowResizedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWSIZECHANGED], callback: Callable[[WindowSizeChangedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWMINIMIZED], callback: Callable[[WindowMinimizedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWMAXIMIZED], callback: Callable[[WindowMaximizedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWRESTORED], callback: Callable[[WindowRestoredEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWENTER], callback: Callable[[WindowEnterEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWLEAVE], callback: Callable[[WindowLeaveEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWFOCUSGAINED], callback: Callable[[WindowFocusGainedEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWFOCUSLOST], callback: Callable[[WindowFocusLostEvent], Optional[bool]]
    ) -> None:
        ...

    @overload
    def bind_event(
        self, /, event_type: Literal[Event.Type.WINDOWTAKEFOCUS], callback: Callable[[WindowTakeFocusEvent], Optional[bool]]
    ) -> None:
        ...

    def bind_event(self, /, event_type: Event.Type, callback: Callable[[_TE], Optional[bool]]) -> None:
        EventManager.__bind(self.__event_handler_dict, Event.Type(event_type), callback)

    def unbind_event(self, /, event_type: Event.Type, callback_to_remove: Callable[[_TE], Optional[bool]]) -> None:
        EventManager.__unbind(self.__event_handler_dict, Event.Type(event_type), callback_to_remove)

    def unbind_all(self, /) -> None:
        self.__event_handler_dict.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()

    def bind_key(self, /, key: Keyboard.Key, callback: Callable[[KeyEvent], Optional[bool]]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, /, key: Keyboard.Key, callback: Callable[[KeyDownEvent], Optional[bool]]) -> None:
        EventManager.__bind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback)

    def bind_key_release(self, /, key: Keyboard.Key, callback: Callable[[KeyUpEvent], Optional[bool]]) -> None:
        EventManager.__bind(self.__key_released_handler_dict, Keyboard.Key(key), callback)

    def unbind_key(self, /, key: Keyboard.Key, callback_to_remove: Callable[[KeyEvent], Optional[bool]]) -> None:
        self.unbind_key_press(key, callback_to_remove)
        self.unbind_key_release(key, callback_to_remove)

    def unbind_key_press(self, /, key: Keyboard.Key, callback_to_remove: Callable[[KeyDownEvent], Optional[bool]]) -> None:
        EventManager.__unbind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback_to_remove)

    def unbind_key_release(self, /, key: Keyboard.Key, callback_to_remove: Callable[[KeyUpEvent], Optional[bool]]) -> None:
        EventManager.__unbind(self.__key_released_handler_dict, Keyboard.Key(key), callback_to_remove)

    def bind_mouse_button(self, /, button: Mouse.Button, callback: Callable[[MouseButtonEvent], Optional[bool]]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(
        self, /, button: Mouse.Button, callback: Callable[[MouseButtonDownEvent], Optional[bool]]
    ) -> None:
        EventManager.__bind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback)

    def bind_mouse_button_release(
        self, /, button: Mouse.Button, callback: Callable[[MouseButtonUpEvent], Optional[bool]]
    ) -> None:
        EventManager.__bind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback)

    def unbind_mouse_button(
        self, /, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonEvent], Optional[bool]]
    ) -> None:
        self.unbind_mouse_button_press(button, callback_to_remove)
        self.unbind_mouse_button_release(button, callback_to_remove)

    def unbind_mouse_button_press(
        self, /, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonDownEvent], Optional[bool]]
    ) -> None:
        EventManager.__unbind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback_to_remove)

    def unbind_mouse_button_release(
        self, /, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonUpEvent], Optional[bool]]
    ) -> None:
        EventManager.__unbind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback_to_remove)

    def bind_mouse_position(self, /, callback: _MousePositionCallback) -> None:
        mouse_pos_handler_list: List[_MousePositionCallback] = self.__mouse_pos_handler_list
        if callback not in mouse_pos_handler_list:
            mouse_pos_handler_list.append(callback)

    def unbind_mouse_position(self, /, callback_to_remove: _MousePositionCallback) -> None:
        mouse_pos_handler_list: List[_MousePositionCallback] = self.__mouse_pos_handler_list
        with suppress(ValueError):
            mouse_pos_handler_list.remove(callback_to_remove)

    def process_event(self, /, event: Event) -> bool:
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

    def handle_mouse_position(self, /) -> None:
        mouse_pos: Tuple[float, float] = Mouse.get_pos()
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)

    def __handle_key_event(self, /, event: KeyEvent) -> Optional[bool]:
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

    def __handle_mouse_event(self, /, event: MouseButtonEvent) -> Optional[bool]:
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
