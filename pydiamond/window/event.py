# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "BuiltinEvent",
    "BuiltinEventType",
    "BuiltinUserEventCode",
    "DropBeginEvent",
    "DropCompleteEvent",
    "DropFileEvent",
    "DropTextEvent",
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventMeta",
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
    "ScreenshotEvent",
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

import weakref
from abc import abstractmethod
from collections import ChainMap, defaultdict
from dataclasses import dataclass, fields
from enum import IntEnum, auto, unique
from itertools import chain
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Concatenate,
    Final,
    Generic,
    Iterable,
    Mapping,
    ParamSpec,
    Sequence,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

import pygame.constants as _pg_constants
import pygame.event as _pg_event
from pygame.mixer import music as _pg_music

from ..system.collections import OrderedSet
from ..system.namespace import ClassNamespaceMeta
from ..system.object import Object, ObjectMeta, final
from ..system.utils.abc import isabstractclass
from ..system.utils.weakref import weakref_unwrap

if TYPE_CHECKING:
    from _typeshed import Self

    from ..audio.music import Music
    from ..graphics.surface import Surface

_T = TypeVar("_T")

_PYGAME_EVENT_TYPE: dict[int, type[Event]] = {}
_ASSOCIATIONS: dict[type[Event], int] = {}


class EventMeta(ObjectMeta):
    __associations: Final[dict[type[Event], int]] = _ASSOCIATIONS
    __type: Final[dict[int, type[Event]]] = _PYGAME_EVENT_TYPE

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="EventMeta")

    def __new__(
        mcs: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        model: bool = False,
        **kwargs: Any,
    ) -> __Self:
        model = bool(model)
        try:
            Event
        except NameError:
            pass
        else:
            if not any(issubclass(b, Event) for b in bases):
                raise TypeError(f"{name!r} must inherit from Event")
            if concrete_events := [b for b in bases if issubclass(b, Event) and not b.is_model()]:
                concrete_events_qualnames = ", ".join(b.__qualname__ for b in concrete_events)
                raise TypeError(f"{name!r}: Events which are not model classes caught: {concrete_events_qualnames}")
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        setattr(cls, "_model_", model or isabstractclass(cls))
        if not cls.is_model() and not issubclass(cls, BuiltinEvent):
            cls = final(cls)
            event_type: int = int(_pg_event.custom_type())
            if event_type in EventFactory.pygame_type:  # Should not happen
                event_cls = EventFactory.pygame_type[event_type]
                raise AssertionError(
                    f"Event with type {_pg_event.event_name(event_type)!r} ({event_type}) already exists: {event_cls}"
                )
            event_cls = cast(type[Event], cls)
            mcs.__associations[event_cls] = event_type
            mcs.__type[event_type] = event_cls
            try:
                event_name_dispatch_table: dict[int, str] = getattr(_pg_event.event_name, "__event_name_dispatch_table__")
            except AttributeError:
                pass
            else:
                event_name_dispatch_table[event_type] = f"{event_cls.__qualname__}({_pg_event.event_name(event_type)})"
        return cls

    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if cls.is_model():
            raise TypeError("Event models are not instanciable")
        return super().__call__(*args, **kwds)

    def __setattr__(cls, __name: str, __value: Any) -> None:
        if __name in {"_model_"} and __name in vars(cls):
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(cls, __name: str) -> None:
        if __name in {"_model_"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)

    def is_model(cls) -> bool:
        return bool(isabstractclass(cls) or getattr(cls, "_model_"))


_BUILTIN_PYGAME_EVENT_TYPE: dict[int, type[Event]] = {}
_BUILTIN_ASSOCIATIONS: dict[type[Event], int] = {}


@final
class _BuiltinEventMeta(EventMeta):
    __associations: Final[dict[type[Event], int]] = _BUILTIN_ASSOCIATIONS  # type: ignore[misc]
    __type: Final[dict[int, type[Event]]] = _BUILTIN_PYGAME_EVENT_TYPE  # type: ignore[misc]

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        event_type: BuiltinEventType | None = None,
        event_name: str | None = None,
        **kwargs: Any,
    ) -> _BuiltinEventMeta:  # noqa: F821
        try:
            BuiltinEvent
        except NameError:
            return super().__new__(mcs, name, bases, namespace, **kwargs)

        if all(event_type in mcs.__type for event_type in BuiltinEventType):
            raise TypeError("Trying to create custom event from BuiltinEvent class")
        assert len(bases) == 1 and issubclass(bases[0], BuiltinEvent)
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        assert not cls.is_model()
        assert isinstance(event_type, BuiltinEventType), f"Got {event_type!r}"
        assert event_type not in mcs.__type, f"{event_type!r} event already taken"
        event_cls = cast(type[BuiltinEvent], cls)
        mcs.__associations[event_cls] = int(event_type)
        mcs.__type[int(event_type)] = event_cls
        if event_name:
            try:
                event_name_dispatch_table: dict[int, str] = getattr(_pg_event.event_name, "__event_name_dispatch_table__")
            except AttributeError:
                pass
            else:
                event_name_dispatch_table[int(event_type)] = event_name
        return cls


class Event(Object, metaclass=EventMeta):
    __slots__ = ()

    @classmethod
    @abstractmethod
    def from_dict(cls: type[Self], event_dict: Mapping[str, Any]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


@unique
class BuiltinEventType(IntEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[Any]) -> Any:
        return _pg_event.custom_type()

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
    AUDIODEVICEADDED = _pg_constants.AUDIODEVICEADDED
    AUDIODEVICEREMOVED = _pg_constants.AUDIODEVICEREMOVED
    TEXTEDITING = _pg_constants.TEXTEDITING
    TEXTINPUT = _pg_constants.TEXTINPUT
    DROPBEGIN = _pg_constants.DROPBEGIN
    DROPCOMPLETE = _pg_constants.DROPCOMPLETE
    DROPFILE = _pg_constants.DROPFILE
    DROPTEXT = _pg_constants.DROPTEXT
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
    MUSICEND = _pg_music.get_endevent()
    SCREENSHOT = auto()

    def __repr__(self) -> str:
        return f"<{self.name} ({self.pygame_name}): {self.value}>"

    @property
    def pygame_name(self) -> str:
        return _pg_event.event_name(self)


class BuiltinUserEventCode(IntEnum):
    DROPFILE = _pg_constants.USEREVENT_DROPFILE

    def __repr__(self) -> str:
        return f"<{self.name}: {self.value}>"


# TODO (3.11) dataclass_transform (PEP-681)
class BuiltinEvent(Event, metaclass=_BuiltinEventMeta, model=True):
    @classmethod
    def from_dict(cls: type[Self], event_dict: Mapping[str, Any]) -> Self:
        event_fields: Sequence[str] = tuple(f.name for f in fields(cls))
        kwargs: dict[str, Any] = {k: event_dict[k] for k in filter(event_fields.__contains__, event_dict)}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self.__class__)}


@final
@dataclass(kw_only=True)
class KeyDownEvent(BuiltinEvent, event_type=BuiltinEventType.KEYDOWN):
    key: int
    mod: int
    unicode: str
    scancode: int


@final
@dataclass(kw_only=True)
class KeyUpEvent(BuiltinEvent, event_type=BuiltinEventType.KEYUP):
    key: int
    mod: int


KeyEvent: TypeAlias = KeyDownEvent | KeyUpEvent


@final
@dataclass(kw_only=True)
class MouseButtonDownEvent(BuiltinEvent, event_type=BuiltinEventType.MOUSEBUTTONDOWN):
    pos: tuple[int, int]
    button: int


@final
@dataclass(kw_only=True)
class MouseButtonUpEvent(BuiltinEvent, event_type=BuiltinEventType.MOUSEBUTTONUP):
    pos: tuple[int, int]
    button: int


MouseButtonEvent: TypeAlias = MouseButtonDownEvent | MouseButtonUpEvent


@final
@dataclass(kw_only=True)
class MouseMotionEvent(BuiltinEvent, event_type=BuiltinEventType.MOUSEMOTION):
    pos: tuple[int, int]
    rel: tuple[int, int]
    buttons: tuple[bool, bool, bool]

    def __post_init__(self) -> None:
        setattr(self, "buttons", tuple(map(bool, self.buttons)))


@final
@dataclass(kw_only=True)
class MouseWheelEvent(BuiltinEvent, event_type=BuiltinEventType.MOUSEWHEEL):
    flipped: bool
    x: int
    y: int

    def __post_init__(self) -> None:
        self.flipped = bool(self.flipped)


MouseEvent: TypeAlias = MouseButtonEvent | MouseWheelEvent | MouseMotionEvent


@final
@dataclass(kw_only=True)
class JoyAxisMotionEvent(BuiltinEvent, event_type=BuiltinEventType.JOYAXISMOTION):
    instance_id: int
    axis: int
    value: float


@final
@dataclass(kw_only=True)
class JoyBallMotionEvent(BuiltinEvent, event_type=BuiltinEventType.JOYBALLMOTION):
    instance_id: int
    ball: int
    rel: float


@final
@dataclass(kw_only=True)
class JoyHatMotionEvent(BuiltinEvent, event_type=BuiltinEventType.JOYHATMOTION):
    instance_id: int
    hat: int
    value: tuple[int, int]


@final
@dataclass(kw_only=True)
class JoyButtonDownEvent(BuiltinEvent, event_type=BuiltinEventType.JOYBUTTONDOWN):
    instance_id: int
    button: int


@final
@dataclass(kw_only=True)
class JoyButtonUpEvent(BuiltinEvent, event_type=BuiltinEventType.JOYBUTTONUP):
    instance_id: int
    button: int


JoyButtonEvent: TypeAlias = JoyButtonDownEvent | JoyButtonUpEvent


@final
@dataclass(kw_only=True)
class JoyDeviceAddedEvent(BuiltinEvent, event_type=BuiltinEventType.JOYDEVICEADDED):
    device_index: int


@final
@dataclass(kw_only=True)
class JoyDeviceRemovedEvent(BuiltinEvent, event_type=BuiltinEventType.JOYDEVICEREMOVED):
    instance_id: int


@final
@dataclass(kw_only=True)
class AudioDeviceAddedEvent(BuiltinEvent, event_type=BuiltinEventType.AUDIODEVICEADDED):
    which: int
    iscapture: bool

    def __post_init__(self) -> None:
        self.iscapture = bool(self.iscapture)


@final
@dataclass(kw_only=True)
class AudioDeviceRemovedEvent(BuiltinEvent, event_type=BuiltinEventType.AUDIODEVICEREMOVED):
    which: int
    iscapture: bool

    def __post_init__(self) -> None:
        self.iscapture = bool(self.iscapture)


@final
@dataclass(kw_only=True)
class TextEditingEvent(BuiltinEvent, event_type=BuiltinEventType.TEXTEDITING):
    text: str
    start: int
    length: int


@final
@dataclass(kw_only=True)
class TextInputEvent(BuiltinEvent, event_type=BuiltinEventType.TEXTINPUT):
    text: str


TextEvent: TypeAlias = TextEditingEvent | TextInputEvent


@final
@dataclass(init=False)
class UserEvent(BuiltinEvent, event_type=BuiltinEventType.USEREVENT):
    code: int = 0

    def __init__(self, *, code: int = 0, **kwargs: Any) -> None:
        self.code = code
        self.__dict__.update(kwargs)

    if TYPE_CHECKING:

        def __getattr__(self, name: str, /) -> Any:  # Indicate dynamic attribute
            ...

    @classmethod
    def from_dict(cls, event_dict: Mapping[str, Any]) -> UserEvent:
        return cls(**event_dict)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__ | super().to_dict()


@final
@dataclass(kw_only=True)
class DropBeginEvent(BuiltinEvent, event_type=BuiltinEventType.DROPBEGIN):
    pass


@final
@dataclass(kw_only=True)
class DropCompleteEvent(BuiltinEvent, event_type=BuiltinEventType.DROPCOMPLETE):
    pass


@final
@dataclass(kw_only=True)
class DropFileEvent(BuiltinEvent, event_type=BuiltinEventType.DROPFILE):
    file: str


@final
@dataclass(kw_only=True)
class DropTextEvent(BuiltinEvent, event_type=BuiltinEventType.DROPTEXT):
    text: str


@final
@dataclass(kw_only=True)
class WindowShownEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWSHOWN):
    pass


@final
@dataclass(kw_only=True)
class WindowHiddenEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWHIDDEN):
    pass


@final
@dataclass(kw_only=True)
class WindowExposedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWEXPOSED):
    pass


@final
@dataclass(kw_only=True)
class WindowMovedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWMOVED):
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowResizedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWRESIZED):
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowSizeChangedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWSIZECHANGED):
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowMinimizedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWMINIMIZED):
    pass


@final
@dataclass(kw_only=True)
class WindowMaximizedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWMAXIMIZED):
    pass


@final
@dataclass(kw_only=True)
class WindowRestoredEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWRESTORED):
    pass


@final
@dataclass(kw_only=True)
class WindowEnterEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWENTER):
    pass


@final
@dataclass(kw_only=True)
class WindowLeaveEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWLEAVE):
    pass


@final
@dataclass(kw_only=True)
class WindowFocusGainedEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWFOCUSGAINED):
    pass


@final
@dataclass(kw_only=True)
class WindowFocusLostEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWFOCUSLOST):
    pass


@final
@dataclass(kw_only=True)
class WindowTakeFocusEvent(BuiltinEvent, event_type=BuiltinEventType.WINDOWTAKEFOCUS):
    pass


@final
@dataclass(kw_only=True)
class MusicEndEvent(BuiltinEvent, event_type=BuiltinEventType.MUSICEND, event_name="MusicEnd"):
    finished: Music
    next: Music | None = None


@final
@dataclass(kw_only=True)
class ScreenshotEvent(BuiltinEvent, event_type=BuiltinEventType.SCREENSHOT, event_name="Screenshot"):
    filepath: str
    screen: Surface


def __check_event_types_association() -> None:
    if unbound_types := set(filter(lambda e: e not in _BUILTIN_PYGAME_EVENT_TYPE, BuiltinEventType)):  # noqa: F821
        raise AssertionError(
            f"The following events do not have an associated BuiltinEvent class: {', '.join(e.name for e in unbound_types)}"
        )


__check_event_types_association()

del __check_event_types_association


class EventFactoryError(Exception):
    pass


class UnknownEventTypeError(EventFactoryError):
    pass


@final
class EventFactory(metaclass=ClassNamespaceMeta, frozen=True):
    associations: Final[Mapping[type[Event], int]] = MappingProxyType(ChainMap(_BUILTIN_ASSOCIATIONS, _ASSOCIATIONS))
    pygame_type: Final[Mapping[int, type[Event]]] = MappingProxyType(ChainMap(_BUILTIN_PYGAME_EVENT_TYPE, _PYGAME_EVENT_TYPE))

    NUMEVENTS: Final[int] = _pg_constants.NUMEVENTS
    NON_BLOCKABLE_EVENTS: Final[frozenset[int]] = frozenset(map(int, getattr(_pg_event.set_blocked, "__forbidden_events__", ())))

    @staticmethod
    def get_pygame_event_type(event: Event | type[Event]) -> int:
        if not isinstance(event, type):
            event = event.__class__
        return EventFactory.associations[event]

    @staticmethod
    def is_blockable(event: type[Event] | int) -> bool:
        if not isinstance(event, int):
            event = EventFactory.associations[event]
        return event not in EventFactory.NON_BLOCKABLE_EVENTS

    @staticmethod
    def from_pygame_event(pygame_event: _pg_event.Event, *, handle_user_events: bool = True) -> Event:
        try:
            event_cls: type[Event] = EventFactory.pygame_type[pygame_event.type]
        except KeyError as exc:
            if not handle_user_events or not (BuiltinEventType.USEREVENT < pygame_event.type < EventFactory.NUMEVENTS):
                raise UnknownEventTypeError(
                    f"Unknown event with type {pygame_event.type} ({_pg_event.event_name(pygame_event.type)!r})"
                ) from exc
            return UserEvent.from_dict(pygame_event.__dict__ | {"code": pygame_event.type})
        match event_cls.from_dict(pygame_event.__dict__):
            case UserEvent(code=BuiltinUserEventCode.DROPFILE, filename=filename) as event:
                # c.f.: https://www.pygame.org/docs/ref/event.html#:~:text=%3Dpygame.-,USEREVENT_DROPFILE,-%2C%20filename
                return DropFileEvent(file=filename)
            case event:
                return event

    @staticmethod
    def make_pygame_event(event: Event) -> _pg_event.Event:
        assert not event.__class__.is_model()  # Should not happen but who knows...?
        event_dict = event.to_dict()
        event_dict.pop("type", None)
        event_type = EventFactory.associations[event.__class__]
        return _pg_event.Event(event_type, event_dict)


_EventCallback: TypeAlias = Callable[[Event], bool]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback: TypeAlias = Callable[[tuple[float, float]], Any]


class EventManager:

    __slots__ = (
        "__event_handler_dict",
        "__event_handler_list",
        "__key_pressed_handler_dict",
        "__key_released_handler_dict",
        "__mouse_button_pressed_handler_dict",
        "__mouse_button_released_handler_dict",
        "__mouse_pos_handler_list",
        "__priority_callback_dict",
        "__weakref__",
    )

    def __init__(self, *, priority_callbacks: bool = True) -> None:
        self.__event_handler_dict: dict[type[Event], OrderedSet[_EventCallback]] = dict()
        self.__event_handler_list: OrderedSet[_EventCallback] = OrderedSet()
        self.__key_pressed_handler_dict: dict[int, Callable[[KeyDownEvent], Any]] = dict()
        self.__key_released_handler_dict: dict[int, Callable[[KeyUpEvent], Any]] = dict()
        self.__mouse_button_pressed_handler_dict: dict[int, Callable[[MouseButtonDownEvent], Any]] = dict()
        self.__mouse_button_released_handler_dict: dict[int, Callable[[MouseButtonUpEvent], Any]] = dict()
        self.__mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = OrderedSet()
        self.__priority_callback_dict: dict[type[Event], _EventCallback] | None = dict() if priority_callbacks else None

    def __del__(self) -> None:
        type(self).clear(self)

    def clear(self) -> None:
        self.__event_handler_dict.clear()
        self.__event_handler_list.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()
        if self.__priority_callback_dict is not None:
            self.__priority_callback_dict.clear()

    @overload
    @staticmethod
    def __bind(
        handler_dict: dict[type[Event], OrderedSet[_EventCallback]],
        key: type[Event],
        callback: Callable[[_TE], bool],
    ) -> None:
        ...

    @overload
    @staticmethod
    def __bind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool]) -> None:
        ...

    @staticmethod
    def __bind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool]) -> None:
        try:
            handler_list: OrderedSet[_EventCallback] = handler_dict[key]
        except KeyError:
            handler_dict[key] = handler_list = OrderedSet()
        handler_list.add(cast(_EventCallback, callback))

    @overload
    @staticmethod
    def __unbind(
        handler_dict: dict[type[Event], OrderedSet[_EventCallback]],
        key: type[Event],
        callback: Callable[[_TE], bool],
    ) -> None:
        ...

    @overload
    @staticmethod
    def __unbind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool]) -> None:
        ...

    @staticmethod
    def __unbind(handler_dict: dict[_T, OrderedSet[_EventCallback]], key: _T, callback: Callable[[_TE], bool]) -> None:
        handler_dict[key].remove(cast(_EventCallback, callback))

    @staticmethod
    def __bind_single(handler_dict: dict[_T, Callable[[_TE], Any]], key: _T, callback: Callable[[_TE], Any]) -> None:
        if key in handler_dict:
            if handler_dict[key] is not callback:
                raise ValueError(f"Conflict when setting {key!r}: a callback is already registered")
            return
        handler_dict[key] = callback

    @staticmethod
    def __unbind_single(handler_dict: dict[_T, Callable[[_TE], Any]], key: _T) -> None:
        del handler_dict[key]

    @overload
    def bind(self, event_cls: type[_TE], callback: Callable[[_TE], bool]) -> None:
        ...

    @overload
    def bind(self, event_cls: None, callback: Callable[[Event], bool]) -> None:
        ...

    def bind(self, event_cls: type[_TE] | None, callback: Callable[[_TE], bool]) -> None:
        if event_cls is None:
            return self.__event_handler_list.add(cast(_EventCallback, callback))
        if not issubclass(event_cls, Event):
            raise TypeError("Invalid argument")
        if event_cls.is_model():
            raise TypeError("Cannot assign events to event models")
        EventManager.__bind(self.__event_handler_dict, event_cls, callback)

    @overload
    def unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_TE], bool]) -> None:
        ...

    @overload
    def unbind(self, event_cls: None, callback_to_remove: Callable[[Event], bool]) -> None:
        ...

    def unbind(self, event_cls: type[_TE] | None, callback_to_remove: Callable[[_TE], bool]) -> None:
        if event_cls is None:
            return self.__event_handler_list.remove(cast(_EventCallback, callback_to_remove))
        if not issubclass(event_cls, Event):
            raise TypeError("Invalid argument")
        if event_cls.is_model():
            raise TypeError("Cannot assign events to event models")
        EventManager.__unbind(self.__event_handler_dict, event_cls, callback_to_remove)
        priority_callback_dict = self.__priority_callback_dict
        if priority_callback_dict is not None:
            for event_type in tuple(
                event_type
                for event_type, priority_callback in priority_callback_dict.items()
                if priority_callback == callback_to_remove
            ):
                priority_callback_dict.pop(event_type)

    @overload
    def bind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_TE], bool]]) -> None:
        ...

    @overload
    def bind_all(self, event_cls: None, sequence: Iterable[Callable[[Event], bool]]) -> None:
        ...

    def bind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[Event], bool]]) -> None:  # type: ignore[misc]
        bind = self.bind
        for callback in sequence:
            bind(event_cls, callback)

    @overload
    def unbind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_TE], bool]]) -> None:
        ...

    @overload
    def unbind_all(self, event_cls: None, sequence: Iterable[Callable[[Event], bool]]) -> None:
        ...

    def unbind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[Event], bool]]) -> None:  # type: ignore[misc]
        unbind = self.unbind
        for callback in sequence:
            unbind(event_cls, callback)

    def bind_key(self, key: int, callback: Callable[[KeyEvent], Any]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, key: int, callback: Callable[[KeyDownEvent], Any]) -> None:
        EventManager.__bind_single(self.__key_pressed_handler_dict, int(key), callback)

    def bind_key_release(self, key: int, callback: Callable[[KeyUpEvent], Any]) -> None:
        EventManager.__bind_single(self.__key_released_handler_dict, int(key), callback)

    def unbind_key(self, key: int) -> None:
        self.unbind_key_press(key)
        self.unbind_key_release(key)

    def unbind_key_press(self, key: int) -> None:
        EventManager.__unbind_single(self.__key_pressed_handler_dict, int(key))

    def unbind_key_release(self, key: int) -> None:
        EventManager.__unbind_single(self.__key_released_handler_dict, int(key))

    def bind_mouse_button(self, button: int, callback: Callable[[MouseButtonEvent], Any]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(self, button: int, callback: Callable[[MouseButtonDownEvent], Any]) -> None:
        EventManager.__bind_single(self.__mouse_button_pressed_handler_dict, int(button), callback)

    def bind_mouse_button_release(self, button: int, callback: Callable[[MouseButtonUpEvent], Any]) -> None:
        EventManager.__bind_single(self.__mouse_button_released_handler_dict, int(button), callback)

    def unbind_mouse_button(self, button: int) -> None:
        self.unbind_mouse_button_press(button)
        self.unbind_mouse_button_release(button)

    def unbind_mouse_button_press(self, button: int) -> None:
        EventManager.__unbind_single(self.__mouse_button_pressed_handler_dict, int(button))

    def unbind_mouse_button_release(self, button: int) -> None:
        EventManager.__unbind_single(self.__mouse_button_released_handler_dict, int(button))

    def bind_mouse_position(self, callback: _MousePositionCallback) -> None:
        mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = self.__mouse_pos_handler_list
        mouse_pos_handler_list.add(callback)

    def unbind_mouse_position(self, callback_to_remove: _MousePositionCallback) -> None:
        mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = self.__mouse_pos_handler_list
        mouse_pos_handler_list.remove(callback_to_remove)

    def _process_event(self, event: Event) -> bool:
        event_type: type[Event] = type(event)

        # mypy does not handle isinstance() with TypeAlias of UnionTypes yet
        if isinstance(event, KeyEvent):  # type: ignore[arg-type,misc]
            if self.__handle_key_event(event):  # type: ignore[arg-type]
                return True
        elif isinstance(event, MouseButtonEvent):  # type: ignore[arg-type,misc]
            if self.__handle_mouse_event(event):  # type: ignore[arg-type]
                return True

        event_handler_iterator = chain(self.__event_handler_dict.get(event_type, ()), self.__event_handler_list)

        priority_callback_dict = self.__priority_callback_dict
        if priority_callback_dict is None:
            return any(callback(event) for callback in event_handler_iterator)

        priority_callback: _EventCallback | None = priority_callback_dict.get(event_type)
        if priority_callback is not None:
            if priority_callback(event):
                return True
            priority_callback_dict[event_type]

        for callback in event_handler_iterator:
            if callback is not priority_callback and callback(event):
                priority_callback_dict[event_type] = callback
                return True
        return False

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)

    def __handle_key_event(self, event: KeyEvent) -> bool:
        match event:
            case KeyDownEvent(key=key) if key in self.__key_pressed_handler_dict:
                self.__key_pressed_handler_dict[key](event)
                return True
            case KeyUpEvent(key=key) if key in self.__key_released_handler_dict:
                self.__key_released_handler_dict[key](event)
                return True
        return False

    def __handle_mouse_event(self, event: MouseButtonEvent) -> bool:
        match event:
            case MouseButtonDownEvent(button=mouse_button) if mouse_button in self.__mouse_button_pressed_handler_dict:
                self.__mouse_button_pressed_handler_dict[mouse_button](event)
                return True
            case MouseButtonUpEvent(button=mouse_button) if mouse_button in self.__mouse_button_released_handler_dict:
                self.__mouse_button_released_handler_dict[mouse_button](event)
                return True
        return False


_P = ParamSpec("_P")
_U = TypeVar("_U")
_V = TypeVar("_V")

_CallbackRegistry: TypeAlias = weakref.WeakKeyDictionary[Callable[..., Any], Callable[..., Any]]


class BoundEventManager(Generic[_T]):
    __slots__ = (
        "__ref",
        "__manager",
        "__event_callbacks",
        "__key_press_callbacks",
        "__key_release_callbacks",
        "__mouse_press_callbacks",
        "__mouse_release_callbacks",
        "__mouse_position_callbacks",
        "__weakref__",
    )

    def __init__(
        self,
        obj: _T,
        *,
        priority_callbacks: bool = True,
        weakref_callback: Callable[[weakref.ref[_T]], None] | None = None,
    ) -> None:
        selfref: weakref.ref[BoundEventManager[_T]] = weakref.ref(self)

        def unbind_all(ref: weakref.ref[_T], /) -> None:
            self = selfref()
            if self is not None:
                self.__manager.clear()
                self.__event_callbacks.clear()
                self.__key_press_callbacks.clear()
                self.__key_release_callbacks.clear()
                self.__mouse_press_callbacks.clear()
                self.__mouse_release_callbacks.clear()
                self.__mouse_position_callbacks.clear()
            if weakref_callback is not None:
                weakref_callback(ref)

        self.__ref: weakref.ref[_T] = weakref.ref(obj, unbind_all)
        self.__manager: EventManager = EventManager(priority_callbacks=priority_callbacks)
        self.__event_callbacks: defaultdict[Any, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__key_press_callbacks: defaultdict[int, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__key_release_callbacks: defaultdict[int, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__mouse_press_callbacks: defaultdict[int, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__mouse_release_callbacks: defaultdict[int, _CallbackRegistry] = defaultdict(weakref.WeakKeyDictionary)
        self.__mouse_position_callbacks: _CallbackRegistry = weakref.WeakKeyDictionary()

    def __del__(self) -> None:
        self.__manager.clear()
        self.__event_callbacks.clear()
        self.__key_press_callbacks.clear()
        self.__key_release_callbacks.clear()
        self.__mouse_press_callbacks.clear()
        self.__mouse_release_callbacks.clear()
        self.__mouse_position_callbacks.clear()

    def __bind(
        self,
        manager_bind: Callable[[_U, Callable[[Event], _V]], None],
        key: _U,
        callback: weakref.WeakMethod[Callable[[_TE], _V]] | Callable[[_T, _TE], _V],
        callback_register: defaultdict[_U, _CallbackRegistry],
        dead_ref_fallback: _V,
    ) -> None:
        callback, event_callback = self.__build_callback(callback, dead_ref_fallback)
        callback = cast(Callable[[_T, Event], _V], callback)
        event_callback = cast(Callable[[Event], _V], event_callback)

        if callback in callback_register[key]:
            event_callback = callback_register[key][callback]
            return manager_bind(key, event_callback)

        manager_bind(key, event_callback)
        callback_register[key][callback] = event_callback

    @overload
    def bind(self, event_cls: type[_TE], callback: Callable[[_T, _TE], bool]) -> None:
        ...

    @overload
    def bind(self, event_cls: type[_TE], callback: weakref.WeakMethod[Callable[[_TE], bool]]) -> None:
        ...

    @overload
    def bind(self, event_cls: None, callback: Callable[[_T, Event], bool]) -> None:
        ...

    @overload
    def bind(self, event_cls: None, callback: weakref.WeakMethod[Callable[[Event], bool]]) -> None:
        ...

    def bind(
        self,
        event_cls: type[_TE] | None,
        callback: weakref.WeakMethod[Callable[[_TE], bool]] | Callable[[_T, _TE], bool],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind,
            key=event_cls,
            callback=callback,
            callback_register=self.__event_callbacks,
            dead_ref_fallback=False,
        )

    @overload
    def unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_T, _TE], bool]) -> None:
        ...

    @overload
    def unbind(self, event_cls: type[_TE], callback_to_remove: weakref.WeakMethod[Callable[[_TE], bool]]) -> None:
        ...

    @overload
    def unbind(self, event_cls: None, callback_to_remove: Callable[[_T, Event], bool]) -> None:
        ...

    @overload
    def unbind(self, event_cls: None, callback_to_remove: weakref.WeakMethod[Callable[[Event], bool]]) -> None:
        ...

    def unbind(
        self,
        event_cls: type[_TE] | None,
        callback_to_remove: weakref.WeakMethod[Callable[[_TE], bool]] | Callable[[_T, _TE], bool],
    ) -> None:
        if isinstance(callback_to_remove, weakref.WeakMethod):
            callback_to_remove = self.__get_method_func_from_weak_method(callback_to_remove)
        event_callback = self.__event_callbacks[event_cls].pop(callback_to_remove)
        return self.__manager.unbind(event_cls, event_callback)

    @overload
    def bind_all(
        self,
        event_cls: type[_TE],
        sequence: Iterable[weakref.WeakMethod[Callable[[_TE], bool]] | Callable[[_T, _TE], bool]],
    ) -> None:
        ...

    @overload
    def bind_all(
        self,
        event_cls: None,
        sequence: Iterable[weakref.WeakMethod[Callable[[Event], bool]] | Callable[[_T, Event], bool]],
    ) -> None:
        ...

    def bind_all(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        sequence: Iterable[weakref.WeakMethod[Callable[[Event], bool]] | Callable[[_T, Event], bool]],
    ) -> None:
        bind = self.bind
        for callback in sequence:
            bind(event_cls, callback)

    @overload
    def unbind_all(
        self,
        event_cls: type[_TE],
        sequence: Iterable[weakref.WeakMethod[Callable[[_TE], bool]] | Callable[[_T, _TE], bool]],
    ) -> None:
        ...

    @overload
    def unbind_all(
        self,
        event_cls: None,
        sequence: Iterable[weakref.WeakMethod[Callable[[Event], bool]] | Callable[[_T, Event], bool]],
    ) -> None:
        ...

    def unbind_all(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        sequence: Iterable[weakref.WeakMethod[Callable[[Event], bool]] | Callable[[_T, Event], bool]],
    ) -> None:
        unbind = self.unbind
        for callback in sequence:
            unbind(event_cls, callback)

    @overload
    def static_bind(self, event_cls: type[_TE], callback: Callable[[_TE], bool]) -> None:
        ...

    @overload
    def static_bind(self, event_cls: None, callback: Callable[[Event], bool]) -> None:
        ...

    def static_bind(self, event_cls: type[Event] | None, callback: Callable[[Event], bool]) -> None:  # type: ignore[misc]
        return self.__manager.bind(event_cls, callback)

    @overload
    def static_unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_TE], bool]) -> None:
        ...

    @overload
    def static_unbind(self, event_cls: None, callback_to_remove: Callable[[Event], bool]) -> None:
        ...

    def static_unbind(self, event_cls: type[Event] | None, callback_to_remove: Callable[[Event], bool]) -> None:  # type: ignore[misc]
        return self.__manager.unbind(event_cls, callback_to_remove)

    @overload
    def static_bind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_TE], bool]]) -> None:
        ...

    @overload
    def static_bind_all(self, event_cls: None, sequence: Iterable[Callable[[Event], bool]]) -> None:
        ...

    def static_bind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[Event], bool]]) -> None:  # type: ignore[misc]
        return self.__manager.bind_all(event_cls, sequence)

    @overload
    def static_unbind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_TE], bool]]) -> None:
        ...

    @overload
    def static_unbind_all(self, event_cls: None, sequence: Iterable[Callable[[Event], bool]]) -> None:
        ...

    def static_unbind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[Event], bool]]) -> None:  # type: ignore[misc]
        return self.__manager.unbind_all(event_cls, sequence)

    @overload
    def bind_key(self, key: int, callback: Callable[[_T, KeyEvent], Any]) -> None:
        ...

    @overload
    def bind_key(self, key: int, callback: weakref.WeakMethod[Callable[[KeyEvent], Any]]) -> None:
        ...

    def bind_key(self, key: int, callback: Callable[..., Any]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    @overload
    def bind_key_press(self, key: int, callback: Callable[[_T, KeyDownEvent], Any]) -> None:
        ...

    @overload
    def bind_key_press(self, key: int, callback: weakref.WeakMethod[Callable[[KeyDownEvent], Any]]) -> None:
        ...

    def bind_key_press(
        self,
        key: int,
        callback: weakref.WeakMethod[Callable[[KeyDownEvent], Any]] | Callable[[_T, KeyDownEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_key_press,
            key=key,
            callback=callback,
            callback_register=self.__key_press_callbacks,
            dead_ref_fallback=None,
        )

    @overload
    def bind_key_release(self, key: int, callback: Callable[[_T, KeyUpEvent], Any]) -> None:
        ...

    @overload
    def bind_key_release(self, key: int, callback: weakref.WeakMethod[Callable[[KeyUpEvent], Any]]) -> None:
        ...

    def bind_key_release(
        self,
        key: int,
        callback: weakref.WeakMethod[Callable[[KeyUpEvent], Any]] | Callable[[_T, KeyUpEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_key_release,
            key=key,
            callback=callback,
            callback_register=self.__key_release_callbacks,
            dead_ref_fallback=None,
        )

    def static_bind_key(self, key: int, callback: Callable[[KeyEvent], Any]) -> None:
        return self.__manager.bind_key(key, callback)

    def static_bind_key_press(self, key: int, callback: Callable[[KeyDownEvent], Any]) -> None:
        return self.__manager.bind_key_press(key, callback)

    def static_bind_key_release(self, key: int, callback: Callable[[KeyUpEvent], Any]) -> None:
        return self.__manager.bind_key_release(key, callback)

    def unbind_key(self, key: int) -> None:
        self.unbind_key_press(key)
        self.unbind_key_release(key)

    def unbind_key_press(self, key: int) -> None:
        self.__manager.unbind_key_press(key)
        self.__key_press_callbacks[key].clear()

    def unbind_key_release(self, key: int) -> None:
        self.__manager.unbind_key_release(key)
        self.__key_release_callbacks[key].clear()

    @overload
    def bind_mouse_button(self, button: int, callback: Callable[[_T, MouseButtonEvent], Any]) -> None:
        ...

    @overload
    def bind_mouse_button(self, button: int, callback: weakref.WeakMethod[Callable[[MouseButtonEvent], Any]]) -> None:
        ...

    def bind_mouse_button(self, button: int, callback: Callable[..., Any]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    @overload
    def bind_mouse_button_press(self, button: int, callback: Callable[[_T, MouseButtonDownEvent], Any]) -> None:
        ...

    @overload
    def bind_mouse_button_press(self, button: int, callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], Any]]) -> None:
        ...

    def bind_mouse_button_press(
        self,
        button: int,
        callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], Any]] | Callable[[_T, MouseButtonDownEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_mouse_button_press,
            key=button,
            callback=callback,
            callback_register=self.__mouse_press_callbacks,
            dead_ref_fallback=None,
        )

    @overload
    def bind_mouse_button_release(self, button: int, callback: Callable[[_T, MouseButtonUpEvent], Any]) -> None:
        ...

    @overload
    def bind_mouse_button_release(self, button: int, callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], Any]]) -> None:
        ...

    def bind_mouse_button_release(
        self,
        button: int,
        callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], Any]] | Callable[[_T, MouseButtonUpEvent], Any],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_mouse_button_release,
            key=button,
            callback=callback,
            callback_register=self.__mouse_release_callbacks,
            dead_ref_fallback=None,
        )

    def static_bind_mouse_button(self, button: int, callback: Callable[[MouseButtonEvent], Any]) -> None:
        return self.__manager.bind_mouse_button(button, callback)

    def static_bind_mouse_button_press(self, button: int, callback: Callable[[MouseButtonDownEvent], Any]) -> None:
        return self.__manager.bind_mouse_button_press(button, callback)

    def static_bind_mouse_button_release(self, button: int, callback: Callable[[MouseButtonUpEvent], Any]) -> None:
        return self.__manager.bind_mouse_button_release(button, callback)

    def unbind_mouse_button(self, button: int) -> None:
        self.unbind_mouse_button_press(button)
        self.unbind_mouse_button_release(button)

    def unbind_mouse_button_press(self, button: int) -> None:
        self.__manager.unbind_mouse_button_press(button)
        self.__mouse_press_callbacks[button].clear()

    def unbind_mouse_button_release(self, button: int) -> None:
        self.__manager.unbind_mouse_button_release(button)
        self.__mouse_release_callbacks[button].clear()

    @overload
    def bind_mouse_position(self, callback: Callable[[_T, tuple[float, float]], Any]) -> None:
        ...

    @overload
    def bind_mouse_position(self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], Any]]) -> None:
        ...

    def bind_mouse_position(
        self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], Any]] | Callable[[_T, tuple[float, float]], Any]
    ) -> None:
        callback, mouse_position_callback = self.__build_callback(callback, None)

        if callback in self.__mouse_position_callbacks:
            mouse_position_callback = self.__mouse_position_callbacks[callback]
            return self.__manager.bind_mouse_position(mouse_position_callback)

        self.__manager.bind_mouse_position(mouse_position_callback)
        self.__mouse_position_callbacks[callback] = mouse_position_callback

    @overload
    def unbind_mouse_position(self, callback_to_remove: Callable[[_T, tuple[float, float]], Any]) -> None:
        ...

    @overload
    def unbind_mouse_position(self, callback_to_remove: weakref.WeakMethod[Callable[[tuple[float, float]], Any]]) -> None:
        ...

    def unbind_mouse_position(
        self,
        callback_to_remove: weakref.WeakMethod[Callable[[tuple[float, float]], Any]] | Callable[[_T, tuple[float, float]], Any],
    ) -> None:
        if isinstance(callback_to_remove, weakref.WeakMethod):
            callback_to_remove = self.__get_method_func_from_weak_method(callback_to_remove)
        mouse_position_callback = self.__mouse_position_callbacks.pop(callback_to_remove)
        return self.__manager.unbind_mouse_position(mouse_position_callback)

    def static_bind_mouse_position(self, callback: _MousePositionCallback) -> None:
        return self.__manager.bind_mouse_position(callback)

    def static_unbind_mouse_position(self, callback_to_remove: _MousePositionCallback) -> None:
        return self.__manager.unbind_mouse_position(callback_to_remove)

    def _process_event(self, event: Event) -> bool:
        return self.__manager._process_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        return self.__manager._handle_mouse_position(mouse_pos)

    def __get_method_func_from_weak_method(
        self, weak_method: weakref.WeakMethod[Callable[_P, _U]]
    ) -> Callable[Concatenate[_T, _P], _U]:
        method: Any | None = weak_method()
        if method is None:
            raise ReferenceError("Dead reference")
        if not hasattr(method, "__self__") or not hasattr(method, "__func__"):
            raise TypeError("Not a method-like object")
        if method.__self__ is not (obj := self.__self__):
            raise ValueError(f"{method.__self__!r} is not {obj!r}")
        callback: Callable[..., Any] = method.__func__
        del obj, method
        return callback

    def __build_callback(
        self,
        callback: weakref.WeakMethod[Callable[_P, _U]] | Callable[Concatenate[_T, _P], _U],
        default_fallback: _U,
    ) -> tuple[Callable[Concatenate[_T, _P], _U], Callable[_P, _U]]:
        method: Callable[Concatenate[_T, _P], _U]
        if isinstance(callback, weakref.WeakMethod):
            method = self.__get_method_func_from_weak_method(callback)
            weak_method = callback

            def callback_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _U:
                method = weak_method()
                if method is None:
                    return default_fallback
                return method(*args, **kwargs)

        else:
            method = callback
            selfref = self.__ref

            def callback_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _U:
                self = selfref()
                if self is None:
                    return default_fallback
                return method(self, *args, **kwargs)

        return method, callback_wrapper

    @property
    def __self__(self) -> _T:
        return weakref_unwrap(self.__ref)


del _pg_constants, _pg_music, _BuiltinEventMeta
del _ASSOCIATIONS, _PYGAME_EVENT_TYPE, _BUILTIN_ASSOCIATIONS, _BUILTIN_PYGAME_EVENT_TYPE
