# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "BuiltinEvent",
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventType",
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

from abc import abstractmethod
from contextlib import suppress
from dataclasses import Field, asdict as dataclass_asdict, dataclass, field, fields
from enum import IntEnum, unique
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Literal, Sequence, SupportsInt, TypeAlias, TypeVar, cast

import pygame.constants as _pg_constants
from pygame.event import Event as _PygameEvent, custom_type as _pg_event_custom_type, event_name as _pg_event_name

from ..audio.music import Music, MusicStream
from ..system.namespace import ClassNamespaceMeta
from ..system.object import Object, ObjectMeta, final
from ..system.utils import isconcreteclass
from .keyboard import Keyboard
from .mouse import Mouse

if TYPE_CHECKING:
    from _typeshed import Self

_T = TypeVar("_T")


EventType: TypeAlias = SupportsInt


class _EventMeta(ObjectMeta):
    __associations: Final[dict[EventType, type[Event]]] = {}
    associations: Final[MappingProxyType[EventType, type[Event]]] = MappingProxyType(__associations)

    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _EventMeta:
        try:
            Event
        except NameError:
            pass
        else:
            if len(bases) != 1 or not issubclass(bases[0], Event):
                raise TypeError(f"{name!r} must only inherits from Event without multiple inheritance")
            try:
                BuiltinEvent
            except NameError:
                pass
            else:
                if not issubclass(bases[0], BuiltinEvent) and "type" in namespace:
                    raise TypeError("'type' attribute must not be set explicitly")
        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if isconcreteclass(cls) and cls._should_be_registered():
            event_type: EventType
            if not hasattr(cls, "type"):
                event_type = _pg_event_custom_type()
                setattr(cls, "type", event_type)
            else:
                event_type = getattr(cls, "type")
                if isinstance(event_type, Field):  # Dataclass fields will be handled after the class creation
                    if event_type.init:
                        raise ValueError("'type' field must not be given at initialization")
                    if not isinstance(event_type.default, EventType):
                        raise ValueError("'type' field default value should be an integer")
                    event_type = event_type.default
                elif not isinstance(event_type, EventType):
                    raise TypeError("Events must have an integer 'type' class attribute")
            if event_type in metacls.__associations:
                event_cls = metacls.__associations[event_type]
                raise TypeError(f"Event with type {int(event_type)} already exists: {event_cls}")
            metacls.__associations[event_type] = cast(type[Event], cls)
        return cls

    def _should_be_registered(cls) -> bool:
        return True


class Event(Object, metaclass=_EventMeta):
    @classmethod
    @abstractmethod
    def from_dict(cls: type[Self], event_dict: dict[str, Any]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError

    type: ClassVar[EventType]


class _BuiltinEventMeta(_EventMeta):
    __associations: Final[dict[BuiltinEvent.Type, type[BuiltinEvent]]] = {}  # type: ignore[misc]

    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _EventMeta:
        try:
            BuiltinEvent
        except NameError:
            pass
        else:
            if len(bases) != 1 or not issubclass(bases[0], BuiltinEvent):
                raise TypeError(f"{name!r} must only inherits from BuiltinEvent without multiple inheritance")
            cls = super().__new__(metacls, name, bases, namespace, **kwargs)
            event_type: Any = getattr(cls, "type", None)
            if isinstance(event_type, Field):
                event_type = event_type.default
            if not isinstance(event_type, BuiltinEvent.Type):
                raise TypeError(f"BuiltinEvents must have a BuiltinEvent.Type 'type' class attribute, got {event_type!r}")
            if event_type in metacls.__associations:
                raise TypeError("Trying to create custom event from BuiltinEvent class")
            metacls.__associations[event_type] = cast(type[BuiltinEvent], cls)
            return cls
        return super().__new__(metacls, name, bases, namespace, **kwargs)

    @classmethod
    def _check_event_types_association(metacls) -> None:
        for event_type in BuiltinEvent.Type:
            if event_type not in metacls.__associations:
                raise TypeError(f"{event_type.name} event does not have an associated BuiltinEvent class")

    def _should_be_registered(cls) -> bool:
        if cls.__name__ == "BuiltinEvent" and cls.__name__ not in globals():
            return False
        return super()._should_be_registered()


@dataclass(frozen=True, kw_only=True)  # TODO (3.11) dataclass_transform (PEP-681)
class BuiltinEvent(Event, metaclass=_BuiltinEventMeta):
    @unique
    class Type(IntEnum):
        # pygame's built-in events
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

        # PyDiamond's events
        MUSICEND = MusicStream.MUSICEND

        def __repr__(self) -> str:
            return f"<{self.name} ({self.real_name}): {self.value}>"

        @property
        def real_name(self) -> str:
            return _pg_event_name(self)

    if not TYPE_CHECKING:

        def __new__(cls: type[Self], *args: Any, **kwargs: Any) -> Self:
            if cls is BuiltinEvent:
                raise TypeError("Cannot instantiate base class BuiltinEvent")
            return super().__new__(cls)

    @final
    @classmethod
    def from_dict(cls: type[Self], event_dict: dict[str, Any]) -> Self:
        event_fields: Sequence[str] = tuple(f.name for f in fields(cls))
        kwargs: dict[str, Any] = {k: event_dict[k] for k in filter(event_fields.__contains__, event_dict)}
        return cls(**kwargs)

    @final
    def to_dict(self) -> dict[str, Any]:
        return dataclass_asdict(self)

    type: ClassVar[BuiltinEvent.Type] = field(init=False)


@final
@dataclass(frozen=True, kw_only=True)
class KeyDownEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.KEYDOWN]] = field(default=BuiltinEvent.Type.KEYDOWN, init=False)
    key: int
    mod: int
    unicode: str
    scancode: int


@final
@dataclass(frozen=True, kw_only=True)
class KeyUpEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.KEYUP]] = field(default=BuiltinEvent.Type.KEYUP, init=False)
    key: int
    mod: int


KeyEvent: TypeAlias = KeyDownEvent | KeyUpEvent


@final
@dataclass(frozen=True, kw_only=True)
class MouseButtonDownEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.MOUSEBUTTONDOWN]] = field(default=BuiltinEvent.Type.MOUSEBUTTONDOWN, init=False)
    pos: tuple[int, int]
    button: int


@final
@dataclass(frozen=True, kw_only=True)
class MouseButtonUpEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.MOUSEBUTTONUP]] = field(default=BuiltinEvent.Type.MOUSEBUTTONUP, init=False)
    pos: tuple[int, int]
    button: int


MouseButtonEvent: TypeAlias = MouseButtonDownEvent | MouseButtonUpEvent


@final
@dataclass(frozen=True, kw_only=True)
class MouseMotionEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.MOUSEMOTION]] = field(default=BuiltinEvent.Type.MOUSEMOTION, init=False)
    pos: tuple[int, int]
    rel: tuple[int, int]
    buttons: tuple[bool, bool, bool]


@final
@dataclass(frozen=True, kw_only=True)
class MouseWheelEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.MOUSEWHEEL]] = field(default=BuiltinEvent.Type.MOUSEWHEEL, init=False)
    flipped: bool
    x: int
    y: int


MouseEvent: TypeAlias = MouseButtonEvent | MouseWheelEvent | MouseMotionEvent


@final
@dataclass(frozen=True, kw_only=True)
class JoyAxisMotionEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYAXISMOTION]] = field(default=BuiltinEvent.Type.JOYAXISMOTION, init=False)
    instance_id: int
    axis: int
    value: float


@final
@dataclass(frozen=True, kw_only=True)
class JoyBallMotionEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYBALLMOTION]] = field(default=BuiltinEvent.Type.JOYBALLMOTION, init=False)
    instance_id: int
    ball: int
    rel: float


@final
@dataclass(frozen=True, kw_only=True)
class JoyHatMotionEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYHATMOTION]] = field(default=BuiltinEvent.Type.JOYHATMOTION, init=False)
    instance_id: int
    hat: int
    value: tuple[int, int]


@final
@dataclass(frozen=True, kw_only=True)
class JoyButtonDownEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYBUTTONDOWN]] = field(default=BuiltinEvent.Type.JOYBUTTONDOWN, init=False)
    instance_id: int
    button: int


@final
@dataclass(frozen=True, kw_only=True)
class JoyButtonUpEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYBUTTONUP]] = field(default=BuiltinEvent.Type.JOYBUTTONUP, init=False)
    instance_id: int
    button: int


JoyButtonEvent: TypeAlias = JoyButtonDownEvent | JoyButtonUpEvent


@final
@dataclass(frozen=True, kw_only=True)
class JoyDeviceAddedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYDEVICEADDED]] = field(default=BuiltinEvent.Type.JOYDEVICEADDED, init=False)
    device_index: int


@final
@dataclass(frozen=True, kw_only=True)
class JoyDeviceRemovedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.JOYDEVICEREMOVED]] = field(default=BuiltinEvent.Type.JOYDEVICEREMOVED, init=False)
    instance_id: int


@final
@dataclass(frozen=True, kw_only=True)
class TextEditingEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.TEXTEDITING]] = field(default=BuiltinEvent.Type.TEXTEDITING, init=False)
    text: str
    start: int
    length: int


@final
@dataclass(frozen=True, kw_only=True)
class TextInputEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.TEXTINPUT]] = field(default=BuiltinEvent.Type.TEXTINPUT, init=False)
    text: str


TextEvent: TypeAlias = TextEditingEvent | TextInputEvent


@final
@dataclass(frozen=True, kw_only=True)
class UserEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.USEREVENT]] = field(default=BuiltinEvent.Type.USEREVENT, init=False)
    code: int


@final
@dataclass(frozen=True, kw_only=True)
class WindowShownEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWSHOWN]] = field(default=BuiltinEvent.Type.WINDOWSHOWN, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowHiddenEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWHIDDEN]] = field(default=BuiltinEvent.Type.WINDOWHIDDEN, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowExposedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWEXPOSED]] = field(default=BuiltinEvent.Type.WINDOWEXPOSED, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowMovedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWMOVED]] = field(default=BuiltinEvent.Type.WINDOWMOVED, init=False)
    x: int
    y: int


@final
@dataclass(frozen=True, kw_only=True)
class WindowResizedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWRESIZED]] = field(default=BuiltinEvent.Type.WINDOWRESIZED, init=False)
    x: int
    y: int


@final
@dataclass(frozen=True, kw_only=True)
class WindowSizeChangedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWSIZECHANGED]] = field(default=BuiltinEvent.Type.WINDOWSIZECHANGED, init=False)
    x: int
    y: int


@final
@dataclass(frozen=True, kw_only=True)
class WindowMinimizedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWMINIMIZED]] = field(default=BuiltinEvent.Type.WINDOWMINIMIZED, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowMaximizedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWMAXIMIZED]] = field(default=BuiltinEvent.Type.WINDOWMAXIMIZED, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowRestoredEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWRESTORED]] = field(default=BuiltinEvent.Type.WINDOWRESTORED, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowEnterEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWENTER]] = field(default=BuiltinEvent.Type.WINDOWENTER, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowLeaveEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWLEAVE]] = field(default=BuiltinEvent.Type.WINDOWLEAVE, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowFocusGainedEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWFOCUSGAINED]] = field(default=BuiltinEvent.Type.WINDOWFOCUSGAINED, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowFocusLostEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWFOCUSLOST]] = field(default=BuiltinEvent.Type.WINDOWFOCUSLOST, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class WindowTakeFocusEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.WINDOWTAKEFOCUS]] = field(default=BuiltinEvent.Type.WINDOWTAKEFOCUS, init=False)


@final
@dataclass(frozen=True, kw_only=True)
class MusicEndEvent(BuiltinEvent):
    type: ClassVar[Literal[BuiltinEvent.Type.MUSICEND]] = field(default=BuiltinEvent.Type.MUSICEND, init=False)
    finished: Music
    next: Music | None


_BuiltinEventMeta._check_event_types_association()

_EventCallback: TypeAlias = Callable[[Event], bool | None]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback: TypeAlias = Callable[[tuple[float, float]], None]


class EventFactoryError(Exception):
    pass


class UnknownEventTypeError(EventFactoryError):
    pass


class EventFactory(metaclass=ClassNamespaceMeta, frozen=True):
    associations: Final[MappingProxyType[EventType, type[Event]]] = _EventMeta.associations

    @staticmethod
    def get_all_event_types() -> tuple[EventType, ...]:
        return tuple(EventFactory.associations.keys())

    @staticmethod
    def is_valid_type(event_type: EventType) -> bool:
        return event_type in EventFactory.associations

    @staticmethod
    def from_pygame_event(event: _PygameEvent) -> Event:
        try:
            event_cls: type[Event] = EventFactory.associations[event.type]
        except KeyError as exc:
            raise UnknownEventTypeError(f"Unknown event with type {event.type!r}") from exc
        event_dict = dict(event.__dict__)
        event_dict.pop("type", None)
        return event_cls.from_dict(event_dict)


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
        self.__event_handler_dict: dict[EventType, list[_EventCallback]] = dict()
        self.__key_pressed_handler_dict: dict[Keyboard.Key, list[_EventCallback]] = dict()
        self.__key_released_handler_dict: dict[Keyboard.Key, list[_EventCallback]] = dict()
        self.__mouse_button_pressed_handler_dict: dict[Mouse.Button, list[_EventCallback]] = dict()
        self.__mouse_button_released_handler_dict: dict[Mouse.Button, list[_EventCallback]] = dict()
        self.__mouse_pos_handler_list: list[_MousePositionCallback] = list()
        self.__other_manager_list: list[EventManager] = list()

    @staticmethod
    def __bind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        try:
            handler_list: list[_EventCallback] = handler_dict[key]
        except KeyError:
            handler_dict[key] = handler_list = []
        if callback not in handler_list:
            handler_list.append(cast(_EventCallback, callback))

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
        if manager is self:
            raise ValueError("Trying to add yourself")
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
        event_dict: dict[EventType, list[_EventCallback]] = self.__event_handler_dict
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
        if event.type == BuiltinEvent.Type.KEYDOWN:
            key_handler_dict = self.__key_pressed_handler_dict
        elif event.type == BuiltinEvent.Type.KEYUP:
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
        if event.type == BuiltinEvent.Type.MOUSEBUTTONDOWN:
            mouse_handler_dict = self.__mouse_button_pressed_handler_dict
        elif event.type == BuiltinEvent.Type.MOUSEBUTTONUP:
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


del _pg_constants, _EventMeta, _BuiltinEventMeta, MusicStream
