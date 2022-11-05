# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Window events module"""

from __future__ import annotations

__all__ = [
    "BuiltinEvent",
    "BuiltinEventType",
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
    "NamespaceEventModel",
    "NoDataEventModel",
    "PygameConvertedEventBlocked",
    "PygameEventConversionError",
    "ScreenshotEvent",
    "TextEditingEvent",
    "TextInputEvent",
    "UnknownEventTypeError",
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

from ..system.collections import OrderedSet, WeakKeyDefaultDictionary
from ..system.namespace import ClassNamespaceMeta
from ..system.object import Object, ObjectMeta, final
from ..system.utils.abc import isabstractclass
from ..system.utils.weakref import weakref_unwrap

if TYPE_CHECKING:
    from ..audio.music import Music
    from ..graphics.surface import Surface

_P = ParamSpec("_P")
_T = TypeVar("_T")
_U = TypeVar("_U")
_V = TypeVar("_V")

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
        is_model = EventMeta.is_model
        try:
            Event
        except NameError:
            pass
        else:
            if not any(issubclass(b, Event) for b in bases):
                raise TypeError(f"{name!r} must inherit from Event")
            if concrete_events := [b for b in bases if issubclass(b, Event) and not is_model(b)]:
                concrete_events_qualnames = ", ".join(b.__qualname__ for b in concrete_events)
                raise TypeError(f"{name!r}: Events which are not model classes caught: {concrete_events_qualnames}")
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        setattr(cls, "_model_", model or isabstractclass(cls))
        if not is_model(cls) and not issubclass(cls, BuiltinEvent):
            cls = final(cls)
            event_type: int = int(_pg_event.custom_type())
            if event_type in EventFactory.pygame_type:  # Should not happen
                event_cls = EventFactory.pygame_type[event_type]
                raise AssertionError(
                    f"Event with type {_pg_event.event_name(event_type)!r} ({event_type}) already exists: {event_cls}"
                )
            event_cls = cast(type[Event], cls)
            EventMeta.__associations[event_cls] = event_type
            EventMeta.__type[event_type] = event_cls
            try:
                event_name_dispatch_table: dict[int, str] = getattr(_pg_event.event_name, "__event_name_dispatch_table__")
            except AttributeError:
                pass
            else:
                event_name = f"{event_cls.__module__}.{event_cls.__qualname__}"
                try:
                    original_pygame_event_name: Callable[[int], str] = getattr(_pg_event.event_name, "__wrapped__")
                except AttributeError:
                    pass
                else:
                    event_name = f"{event_name}({original_pygame_event_name(event_type)})"
                event_name_dispatch_table[event_type] = event_name
        return cls

    @final
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

    @final
    def is_model(cls) -> bool:
        return bool(isabstractclass(cls) or getattr(cls, "_model_"))

    @final
    def get_name(cls) -> str:
        if cls.is_model():
            raise TypeError("Event models do not have a name")
        pg_type = EventFactory.get_pygame_event_type(cls)  # type: ignore[arg-type]
        return _pg_event.event_name(pg_type)


_BUILTIN_PYGAME_EVENT_TYPE: dict[int, type[Event]] = {}
_BUILTIN_ASSOCIATIONS: dict[type[Event], int] = {}


@final
class _BuiltinEventMeta(EventMeta):
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
            return super().__new__(mcs, name, bases, namespace, model=event_type is None, **kwargs)

        try:
            dict_associations: Final[dict[type[Event], int]] = _BUILTIN_ASSOCIATIONS  # noqa: F821
            dict_type: Final[dict[int, type[Event]]] = _BUILTIN_PYGAME_EVENT_TYPE  # noqa: F821
        except NameError:
            raise TypeError("Trying to create custom event from BuiltinEvent class") from None

        assert len(bases) == 1 and issubclass(bases[0], BuiltinEvent)
        cls = super().__new__(mcs, name, bases, namespace, model=event_type is None, **kwargs)
        if cls.is_model():
            assert event_type is None, f"Got {event_type!r}"
            assert event_name is None, f"Got {event_name!r}"
            return cls
        assert isinstance(event_type, BuiltinEventType), f"Got {event_type!r}"
        assert event_type not in dict_type, f"{event_type!r} event already taken"
        event_cls = cast(type[BuiltinEvent], cls)
        dict_associations[event_cls] = int(event_type)
        dict_type[int(event_type)] = event_cls
        if event_name:
            try:
                event_name_dispatch_table: dict[int, str] = getattr(_pg_event.event_name, "__event_name_dispatch_table__")
            except AttributeError:
                pass
            else:
                event_name_dispatch_table[int(event_type)] = event_name
        return cls


class Event(Object, metaclass=EventMeta):
    __slots__ = ("__weakref__",)

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="Event")

    def __repr__(self) -> str:
        event_name: str
        event_type = self.__class__
        try:
            pygame_type = EventFactory.get_pygame_event_type(event_type)
        except KeyError:
            event_name = event_type.__name__
        else:
            event_name = _pg_event.event_name(pygame_type)
        event_dict = self.to_dict()
        return f"{event_name}({', '.join(f'{k}={v!r}' for k, v in event_dict.items())})"

    @classmethod
    @abstractmethod
    def from_dict(cls: type[__Self], event_dict: Mapping[str, Any]) -> __Self:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


class NoDataEventModel(Event, model=True):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="NoDataEventModel")

    @classmethod
    @final
    def from_dict(cls: type[__Self], event_dict: Mapping[str, Any]) -> __Self:
        if event_dict:
            raise TypeError(f"{cls.get_name()} does not take data")
        return cls()

    @final
    def to_dict(self) -> dict[str, Any]:
        return {}


class NamespaceEventModel(Event, model=True, no_slots=True):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="NamespaceEventModel")

    @classmethod
    @final
    def from_dict(cls: type[__Self], event_dict: Mapping[str, Any]) -> __Self:
        self = cls.__new__(cls)
        self.__dict__.update(event_dict)
        return self

    @final
    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@unique
class BuiltinEventType(IntEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        return getattr(_pg_constants, name)  # noqa: F821

    # pygame's built-in events
    KEYDOWN = auto()
    KEYUP = auto()
    MOUSEMOTION = auto()
    MOUSEBUTTONUP = auto()
    MOUSEBUTTONDOWN = auto()
    MOUSEWHEEL = auto()
    JOYAXISMOTION = auto()
    JOYBALLMOTION = auto()
    JOYHATMOTION = auto()
    JOYBUTTONUP = auto()
    JOYBUTTONDOWN = auto()
    JOYDEVICEADDED = auto()
    JOYDEVICEREMOVED = auto()
    AUDIODEVICEADDED = auto()
    AUDIODEVICEREMOVED = auto()
    FINGERMOTION = auto()
    FINGERUP = auto()
    FINGERDOWN = auto()
    MULTIGESTURE = auto()
    TEXTEDITING = auto()
    TEXTINPUT = auto()
    DROPBEGIN = auto()
    DROPCOMPLETE = auto()
    DROPFILE = auto()
    DROPTEXT = auto()
    WINDOWSHOWN = auto()
    WINDOWHIDDEN = auto()
    WINDOWEXPOSED = auto()
    WINDOWMOVED = auto()
    WINDOWRESIZED = auto()
    WINDOWSIZECHANGED = auto()
    WINDOWMINIMIZED = auto()
    WINDOWMAXIMIZED = auto()
    WINDOWRESTORED = auto()
    WINDOWENTER = auto()
    WINDOWLEAVE = auto()
    WINDOWFOCUSGAINED = auto()
    WINDOWFOCUSLOST = auto()
    WINDOWCLOSE = auto()
    WINDOWTAKEFOCUS = auto()
    WINDOWHITTEST = auto()

    # PyDiamond's events
    MUSICEND = _pg_event.custom_type()
    SCREENSHOT = _pg_event.custom_type()

    def __repr__(self) -> str:
        return f"<{self.name} ({self.pygame_name}): {self.value}>"

    @property
    def pygame_name(self) -> str:
        return _pg_event.event_name(self)


# TODO (3.11) dataclass_transform (PEP-681)
class BuiltinEvent(Event, metaclass=_BuiltinEventMeta):
    __slots__ = ()

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="BuiltinEvent")

    @classmethod
    def from_dict(cls: type[__Self], event_dict: Mapping[str, Any]) -> __Self:
        event_fields: Sequence[str] = tuple(f.name for f in fields(cls))
        kwargs: dict[str, Any] = {k: event_dict[k] for k in filter(event_fields.__contains__, event_dict)}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {field.name: getattr(self, field.name) for field in fields(self.__class__)}


@dataclass(kw_only=True)
class KeyEvent(BuiltinEvent):
    key: int
    mod: int
    unicode: str
    scancode: int


@final
@dataclass(kw_only=True)
class KeyDownEvent(KeyEvent, event_type=BuiltinEventType.KEYDOWN):
    pass


@final
@dataclass(kw_only=True)
class KeyUpEvent(KeyEvent, event_type=BuiltinEventType.KEYUP):
    pass


@dataclass(kw_only=True)
class MouseEvent(BuiltinEvent):
    touch: bool


@dataclass(kw_only=True)
class MouseButtonEvent(MouseEvent):
    pos: tuple[int, int]
    button: int


@final
@dataclass(kw_only=True)
class MouseButtonDownEvent(MouseButtonEvent, event_type=BuiltinEventType.MOUSEBUTTONDOWN):
    pass


@final
@dataclass(kw_only=True)
class MouseButtonUpEvent(MouseButtonEvent, event_type=BuiltinEventType.MOUSEBUTTONUP):
    pass


@final
@dataclass(kw_only=True)
class MouseMotionEvent(MouseEvent, event_type=BuiltinEventType.MOUSEMOTION):
    pos: tuple[int, int]
    rel: tuple[int, int]
    buttons: tuple[bool, bool, bool]

    def __post_init__(self) -> None:
        setattr(self, "buttons", tuple(map(bool, self.buttons)))


@final
@dataclass(kw_only=True)
class MouseWheelEvent(MouseEvent, event_type=BuiltinEventType.MOUSEWHEEL):
    flipped: bool
    x: int
    y: int

    def __post_init__(self) -> None:
        self.flipped = bool(self.flipped)

    def x_offset(self, factor: float = 1) -> float:
        offset = float(factor) * self.x
        if self.flipped:
            return -offset
        return offset

    def y_offset(self, factor: float = 1) -> float:
        offset = float(factor) * self.y
        if self.flipped:
            return offset
        return -offset


@dataclass(kw_only=True)
class JoyEvent(BuiltinEvent):
    instance_id: int


@final
@dataclass(kw_only=True)
class JoyAxisMotionEvent(JoyEvent, event_type=BuiltinEventType.JOYAXISMOTION):
    axis: int
    value: float


@final
@dataclass(kw_only=True)
class JoyBallMotionEvent(JoyEvent, event_type=BuiltinEventType.JOYBALLMOTION):
    ball: int
    rel: float


@final
@dataclass(kw_only=True)
class JoyHatMotionEvent(JoyEvent, event_type=BuiltinEventType.JOYHATMOTION):
    hat: int
    value: tuple[int, int]


@dataclass(kw_only=True)
class JoyButtonEvent(JoyEvent):
    button: int


@final
@dataclass(kw_only=True)
class JoyButtonDownEvent(JoyButtonEvent, event_type=BuiltinEventType.JOYBUTTONDOWN):
    pass


@final
@dataclass(kw_only=True)
class JoyButtonUpEvent(JoyButtonEvent, event_type=BuiltinEventType.JOYBUTTONUP):
    pass


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


@dataclass(kw_only=True)
class TouchEvent(BuiltinEvent):
    touch_id: int


@dataclass(kw_only=True)
class TouchFingerEvent(TouchEvent):
    finger_id: int
    x: float
    y: float
    dx: float
    dy: float


@final
@dataclass(kw_only=True)
class FingerMotionEvent(TouchFingerEvent, event_type=BuiltinEventType.FINGERMOTION):
    pass


@final
@dataclass(kw_only=True)
class FingerUpEvent(TouchFingerEvent, event_type=BuiltinEventType.FINGERUP):
    pass


@final
@dataclass(kw_only=True)
class FingerDownEvent(TouchFingerEvent, event_type=BuiltinEventType.FINGERDOWN):
    pass


@final
@dataclass(kw_only=True)
class MultiGestureEvent(TouchEvent, event_type=BuiltinEventType.MULTIGESTURE):
    x: float
    y: float
    pinched: bool
    rotated: bool
    num_fingers: int


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


@dataclass(kw_only=True)
class DropEvent(BuiltinEvent):
    pass


@final
@dataclass(kw_only=True)
class DropBeginEvent(DropEvent, event_type=BuiltinEventType.DROPBEGIN):
    pass


@final
@dataclass(kw_only=True)
class DropCompleteEvent(DropEvent, event_type=BuiltinEventType.DROPCOMPLETE):
    pass


@final
@dataclass(kw_only=True)
class DropFileEvent(DropEvent, event_type=BuiltinEventType.DROPFILE):
    file: str


@final
@dataclass(kw_only=True)
class DropTextEvent(DropEvent, event_type=BuiltinEventType.DROPTEXT):
    text: str


@dataclass(kw_only=True)
class WindowEvent(BuiltinEvent):
    pass


@final
@dataclass(kw_only=True)
class WindowShownEvent(WindowEvent, event_type=BuiltinEventType.WINDOWSHOWN):
    pass


@final
@dataclass(kw_only=True)
class WindowHiddenEvent(WindowEvent, event_type=BuiltinEventType.WINDOWHIDDEN):
    pass


@final
@dataclass(kw_only=True)
class WindowExposedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWEXPOSED):
    pass


@final
@dataclass(kw_only=True)
class WindowMovedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWMOVED):
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowResizedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWRESIZED):
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowSizeChangedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWSIZECHANGED):
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowMinimizedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWMINIMIZED):
    pass


@final
@dataclass(kw_only=True)
class WindowMaximizedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWMAXIMIZED):
    pass


@final
@dataclass(kw_only=True)
class WindowRestoredEvent(WindowEvent, event_type=BuiltinEventType.WINDOWRESTORED):
    pass


@final
@dataclass(kw_only=True)
class WindowEnterEvent(WindowEvent, event_type=BuiltinEventType.WINDOWENTER):
    pass


@final
@dataclass(kw_only=True)
class WindowLeaveEvent(WindowEvent, event_type=BuiltinEventType.WINDOWLEAVE):
    pass


@final
@dataclass(kw_only=True)
class WindowFocusGainedEvent(WindowEvent, event_type=BuiltinEventType.WINDOWFOCUSGAINED):
    pass


@final
@dataclass(kw_only=True)
class WindowFocusLostEvent(WindowEvent, event_type=BuiltinEventType.WINDOWFOCUSLOST):
    pass


@final
@dataclass(kw_only=True)
class WindowCloseEvent(WindowEvent, event_type=BuiltinEventType.WINDOWCLOSE):
    pass


@final
@dataclass(kw_only=True)
class WindowTakeFocusEvent(WindowEvent, event_type=BuiltinEventType.WINDOWTAKEFOCUS):
    pass


@final
@dataclass(kw_only=True)
class WindowHitTestEvent(WindowEvent, event_type=BuiltinEventType.WINDOWHITTEST):
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

    def get_image(self) -> Surface:
        from ..graphics.surface import load_image

        return load_image(self.filepath)


def __check_event_types_association() -> None:
    if unbound_types := set(filter(lambda e: e not in _BUILTIN_PYGAME_EVENT_TYPE, BuiltinEventType)):  # noqa: F821
        raise AssertionError(
            f"The following events do not have an associated BuiltinEvent class: {', '.join(e.name for e in unbound_types)}"
        )

    def __init_subclass__(cls: type[BuiltinEvent], **kwargs: Any) -> None:
        msg = f"Trying to create custom event from {BuiltinEvent.__qualname__} class"
        raise TypeError(msg)

    __init_subclass__.__qualname__ = f"{BuiltinEvent.__qualname__}.{__init_subclass__.__name__}"
    setattr(BuiltinEvent, "__init_subclass__", classmethod(__init_subclass__))


__check_event_types_association()

del __check_event_types_association


class EventFactoryError(Exception):
    pass


class UnknownEventTypeError(EventFactoryError):
    pass


class PygameEventConversionError(EventFactoryError):
    pass


class PygameConvertedEventBlocked(PygameEventConversionError):
    pass


if TYPE_CHECKING:
    _PygameEventType: TypeAlias = _pg_event.Event
else:
    from pygame.event import EventType as _PygameEventType


@final
class EventFactory(metaclass=ClassNamespaceMeta, frozen=True):
    associations: Final[Mapping[type[Event], int]] = MappingProxyType(ChainMap(_BUILTIN_ASSOCIATIONS, _ASSOCIATIONS))
    pygame_type: Final[Mapping[int, type[Event]]] = MappingProxyType(ChainMap(_BUILTIN_PYGAME_EVENT_TYPE, _PYGAME_EVENT_TYPE))

    NOEVENT: Final[int] = _pg_constants.NOEVENT
    USEREVENT: Final[int] = _pg_constants.USEREVENT
    NUMEVENTS: Final[int] = _pg_constants.NUMEVENTS
    NON_BLOCKABLE_EVENTS: Final[frozenset[int]] = frozenset(map(int, getattr(_pg_event.set_blocked, "__forbidden_events__", ())))

    if __debug__:

        @staticmethod
        def get_pygame_event_type(event: type[Event]) -> int:
            return EventFactory.associations[event]

    else:

        get_pygame_event_type = staticmethod(associations.__getitem__)

    @staticmethod
    def is_blockable(event: type[Event] | int) -> bool:
        if not isinstance(event, int):
            event = EventFactory.associations[event]
        return event not in EventFactory.NON_BLOCKABLE_EVENTS

    @staticmethod
    def from_pygame_event(pygame_event: _pg_event.Event, raise_if_blocked: bool = False) -> Event:
        actual_event_type: int = pygame_event.type
        pygame_event = EventFactory.convert_pygame_event(pygame_event)
        if raise_if_blocked and actual_event_type != pygame_event.type and _pg_event.get_blocked(pygame_event.type):
            raise PygameConvertedEventBlocked(pygame_event.type)
        try:
            event_cls: type[Event] = EventFactory.pygame_type[pygame_event.type]
        except KeyError as exc:
            raise UnknownEventTypeError(
                f"Unknown event with type {pygame_event.type} ({_pg_event.event_name(pygame_event.type)!r})"
            ) from exc
        return event_cls.from_dict(MappingProxyType(pygame_event.__dict__))

    @staticmethod
    def make_pygame_event(event: Event) -> _pg_event.Event:
        assert not event.__class__.is_model()  # Should not happen but who knows...?
        event_dict = event.to_dict()
        if "type" in event_dict:
            raise EventFactoryError("Invalid key 'type' caught in event.to_dict() output")
        event_type = EventFactory.associations[event.__class__]
        return _pg_event.Event(event_type, event_dict)

    @staticmethod
    def convert_pygame_event(event: _pg_event.Event) -> _pg_event.Event:
        import pygame.constants as _pg_constants

        match event:
            case _PygameEventType(type=EventFactory.USEREVENT, code=_pg_constants.USEREVENT_DROPFILE):
                # cf.: https://www.pygame.org/docs/ref/event.html#:~:text=%3Dpygame.-,USEREVENT_DROPFILE,-%2C%20filename
                try:
                    event = _pg_event.Event(int(BuiltinEventType.DROPFILE), file=event.filename)
                except AttributeError as exc:
                    raise PygameEventConversionError(f"Cannot convert {event}") from exc
            case _ if event.type == _pg_music.get_endevent():
                event = _pg_event.Event(int(BuiltinEventType.MUSICEND), event.__dict__)
        return event


_EventCallback: TypeAlias = Callable[[Event], bool]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback: TypeAlias = Callable[[tuple[float, float]], Any]

_WeakCallbackRegister: TypeAlias = weakref.WeakKeyDictionary[Callable[..., Any], Callable[..., Any]]


class EventManager:

    __slots__ = (
        "__event_handler_dict",
        "__other_event_handlers_list",
        "__key_pressed_handler_dict",
        "__key_released_handler_dict",
        "__mouse_button_pressed_handler_dict",
        "__mouse_button_released_handler_dict",
        "__mouse_pos_handler_list",
        "__priority_callback_dict",
        "__weak_event_callbacks",
        "__weak_key_press_callbacks",
        "__weak_key_release_callbacks",
        "__weak_mouse_button_press_callbacks",
        "__weak_mouse_button_release_callbacks",
        "__weak_mouse_position_callbacks",
        "__weakref__",
    )

    __weak_event_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[type[Event] | None, _WeakCallbackRegister]]
    __weak_key_press_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_key_release_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_mouse_button_press_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_mouse_button_release_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_mouse_position_callbacks: WeakKeyDefaultDictionary[Any, _WeakCallbackRegister]

    def __init__(self, *, priority_callbacks: bool = True) -> None:
        self.__event_handler_dict: dict[type[Event], OrderedSet[_EventCallback]] = dict()
        self.__other_event_handlers_list: OrderedSet[_EventCallback] = OrderedSet()
        self.__key_pressed_handler_dict: dict[int, Callable[[KeyDownEvent], Any]] = dict()
        self.__key_released_handler_dict: dict[int, Callable[[KeyUpEvent], Any]] = dict()
        self.__mouse_button_pressed_handler_dict: dict[int, Callable[[MouseButtonDownEvent], Any]] = dict()
        self.__mouse_button_released_handler_dict: dict[int, Callable[[MouseButtonUpEvent], Any]] = dict()
        self.__mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = OrderedSet()
        self.__priority_callback_dict: dict[type[Event], _EventCallback] | None = dict() if priority_callbacks else None

        self.__weak_event_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_key_press_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_key_release_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_mouse_button_press_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_mouse_button_release_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_mouse_position_callbacks = WeakKeyDefaultDictionary(weakref.WeakKeyDictionary)

    def __del__(self) -> None:
        type(self).clear(self)

    def clear(self) -> None:
        self.__event_handler_dict.clear()
        self.__other_event_handlers_list.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()
        if self.__priority_callback_dict is not None:
            self.__priority_callback_dict.clear()
        self.__weak_event_callbacks.clear()
        self.__weak_key_press_callbacks.clear()
        self.__weak_key_release_callbacks.clear()
        self.__weak_mouse_button_press_callbacks.clear()
        self.__weak_mouse_button_release_callbacks.clear()
        self.__weak_mouse_position_callbacks.clear()

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
    def __unbind_single(handler_dict: dict[_T, Callable[[_TE], Any]], key: _T) -> Callable[[_TE], Any]:
        return handler_dict.pop(key)

    @overload
    def bind(
        self,
        event_cls: type[_TE],
        callback: Callable[[_TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]],
    ) -> None:
        ...

    @overload
    def bind(
        self,
        event_cls: None,
        callback: Callable[[Event], bool] | weakref.WeakMethod[Callable[[Event], bool]],
    ) -> None:
        ...

    def bind(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        callback: weakref.WeakMethod[Callable[[Event], bool]] | Callable[[Event], bool],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):

            def unbind(self: EventManager, callback: Callable[[Event], bool]) -> None:
                self.unbind(event_cls, callback)

            obj = self.__get_weak_method_info(callback)[1]

            callback = self.__build_callback_from_method(
                callback,
                dead_ref_fallback_value=False,
                unbind_on_delete=unbind,
                callback_register=self.__weak_event_callbacks[obj][event_cls],
            )

        if event_cls is not None:
            if not issubclass(event_cls, Event):
                raise TypeError("Invalid argument")
            if event_cls.is_model():
                raise TypeError("Cannot assign events to event models")
        if event_cls is KeyDownEvent or event_cls is None:
            if callback in self.__key_pressed_handler_dict.values():
                raise TypeError("Conflict with predecent bind_key_press() call")
        if event_cls is KeyUpEvent or event_cls is None:
            if callback in self.__key_released_handler_dict.values():
                raise TypeError("Conflict with predecent bind_key_release() call")
        if event_cls is MouseButtonDownEvent or event_cls is None:
            if callback in self.__mouse_button_pressed_handler_dict.values():
                raise TypeError("Conflict with predecent bind_mouse_button_press() call")
        if event_cls is MouseButtonUpEvent or event_cls is None:
            if callback in self.__mouse_button_released_handler_dict.values():
                raise TypeError("Conflict with predecent bind_mouse_button_release() call")
        if event_cls is None:
            self.__other_event_handlers_list.add(cast(_EventCallback, callback))
        else:
            EventManager.__bind(self.__event_handler_dict, event_cls, callback)

    @overload
    def unbind(
        self,
        event_cls: type[_TE],
        callback_to_remove: Callable[[_TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]],
    ) -> None:
        ...

    @overload
    def unbind(
        self,
        event_cls: None,
        callback_to_remove: Callable[[Event], bool] | weakref.WeakMethod[Callable[[Event], bool]],
    ) -> None:
        ...

    def unbind(
        self,
        event_cls: type[_TE] | None,
        callback_to_remove: Callable[[_TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]],
    ) -> None:
        if isinstance(callback_to_remove, weakref.WeakMethod):
            method, obj = self.__get_weak_method_info(callback_to_remove)
            callback_to_remove = self.__weak_event_callbacks[obj][event_cls].pop(method)

        if event_cls is None:
            self.__other_event_handlers_list.remove(cast(_EventCallback, callback_to_remove))
        else:
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
                if priority_callback is callback_to_remove
            ):
                priority_callback_dict.pop(event_type)

    @overload
    def bind_all(
        self,
        event_cls: type[_TE],
        sequence: Iterable[Callable[[_TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]]],
    ) -> None:
        ...

    @overload
    def bind_all(
        self,
        event_cls: None,
        sequence: Iterable[Callable[[Event], bool] | weakref.WeakMethod[Callable[[Event], bool]]],
    ) -> None:
        ...

    def bind_all(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        sequence: Iterable[Callable[[Event], bool] | weakref.WeakMethod[Callable[[Event], bool]]],
    ) -> None:
        bind = self.bind
        for callback in sequence:
            bind(event_cls, callback)

    @overload
    def unbind_all(
        self,
        event_cls: type[_TE],
        sequence: Iterable[Callable[[_TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]]],
    ) -> None:
        ...

    @overload
    def unbind_all(
        self,
        event_cls: None,
        sequence: Iterable[Callable[[Event], bool] | weakref.WeakMethod[Callable[[Event], bool]]],
    ) -> None:
        ...

    def unbind_all(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        sequence: Iterable[Callable[[Event], bool] | weakref.WeakMethod[Callable[[Event], bool]]],
    ) -> None:
        unbind = self.unbind
        for callback in sequence:
            unbind(event_cls, callback)

    @overload
    def bind_key(self, key: int, callback: Callable[[KeyEvent], Any]) -> None:
        ...

    @overload
    def bind_key(self, key: int, callback: weakref.WeakMethod[Callable[[KeyEvent], Any]]) -> None:
        ...

    def bind_key(self, key: int, callback: Callable[..., Any]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(
        self,
        key: int,
        callback: Callable[[KeyDownEvent], Any] | weakref.WeakMethod[Callable[[KeyDownEvent], Any]],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):

            def unbind(self: EventManager, callback: Callable[[KeyDownEvent], Any]) -> None:
                if self.__key_pressed_handler_dict.get(key) == callback:
                    self.unbind_key_press(key)

            obj = self.__get_weak_method_info(callback)[1]

            callback = self.__build_callback_from_method(
                callback,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_key_press_callbacks[obj][key],
            )

        if callback in self.__event_handler_dict.get(KeyDownEvent, ()):
            raise TypeError("Conflict with predecent bind(KeyDownEvent) call")
        if callback in self.__other_event_handlers_list:
            raise TypeError("Conflict with predecent bind(None) call")

        EventManager.__bind_single(self.__key_pressed_handler_dict, int(key), callback)

    def bind_key_release(
        self,
        key: int,
        callback: Callable[[KeyUpEvent], Any] | weakref.WeakMethod[Callable[[KeyUpEvent], Any]],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):

            def unbind(self: EventManager, callback: Callable[[KeyUpEvent], Any]) -> None:
                if self.__key_released_handler_dict.get(key) == callback:
                    self.unbind_key_release(key)

            obj = self.__get_weak_method_info(callback)[1]

            callback = self.__build_callback_from_method(
                callback,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_key_release_callbacks[obj][key],
            )

        if callback in self.__event_handler_dict.get(KeyUpEvent, ()):
            raise TypeError("Conflict with predecent bind(KeyUpEvent) call")
        if callback in self.__other_event_handlers_list:
            raise TypeError("Conflict with predecent bind(None) call")

        EventManager.__bind_single(self.__key_released_handler_dict, int(key), callback)

    def unbind_key(self, key: int) -> None:
        self.unbind_key_press(key)
        self.unbind_key_release(key)

    def unbind_key_press(self, key: int) -> None:
        EventManager.__unbind_single(self.__key_pressed_handler_dict, int(key))
        self.__weak_key_press_callbacks.clear()

    def unbind_key_release(self, key: int) -> None:
        EventManager.__unbind_single(self.__key_released_handler_dict, int(key))
        self.__weak_key_release_callbacks.clear()

    @overload
    def bind_mouse_button(self, button: int, callback: Callable[[MouseButtonEvent], Any]) -> None:
        ...

    @overload
    def bind_mouse_button(self, button: int, callback: weakref.WeakMethod[Callable[[MouseButtonEvent], Any]]) -> None:
        ...

    def bind_mouse_button(self, button: int, callback: Callable[..., Any]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(
        self,
        button: int,
        callback: Callable[[MouseButtonDownEvent], Any] | weakref.WeakMethod[Callable[[MouseButtonDownEvent], Any]],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):

            def unbind(self: EventManager, callback: Callable[[MouseButtonDownEvent], Any]) -> None:
                if self.__mouse_button_pressed_handler_dict.get(button) == callback:
                    self.unbind_mouse_button(button)

            obj = self.__get_weak_method_info(callback)[1]

            callback = self.__build_callback_from_method(
                callback,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_button_press_callbacks[obj][button],
            )

        if callback in self.__event_handler_dict.get(MouseButtonDownEvent, ()):
            raise TypeError("Conflict with predecent bind(MouseButtonDownEvent) call")
        if callback in self.__other_event_handlers_list:
            raise TypeError("Conflict with predecent bind(None) call")

        EventManager.__bind_single(self.__mouse_button_pressed_handler_dict, int(button), callback)

    def bind_mouse_button_release(
        self,
        button: int,
        callback: Callable[[MouseButtonUpEvent], Any] | weakref.WeakMethod[Callable[[MouseButtonUpEvent], Any]],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):

            def unbind(self: EventManager, callback: Callable[[MouseButtonUpEvent], Any]) -> None:
                if self.__mouse_button_released_handler_dict.get(button) == callback:
                    self.unbind_mouse_button(button)

            obj = self.__get_weak_method_info(callback)[1]

            callback = self.__build_callback_from_method(
                callback,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_button_release_callbacks[obj][button],
            )

        if callback in self.__event_handler_dict.get(MouseButtonUpEvent, ()):
            raise TypeError("Conflict with predecent bind(MouseButtonUpEvent) call")
        if callback in self.__other_event_handlers_list:
            raise TypeError("Conflict with predecent bind(None) call")

        EventManager.__bind_single(self.__mouse_button_released_handler_dict, int(button), callback)

    def unbind_mouse_button(self, button: int) -> None:
        self.unbind_mouse_button_press(button)
        self.unbind_mouse_button_release(button)

    def unbind_mouse_button_press(self, button: int) -> None:
        EventManager.__unbind_single(self.__mouse_button_pressed_handler_dict, int(button))
        self.__weak_mouse_button_press_callbacks.clear()

    def unbind_mouse_button_release(self, button: int) -> None:
        EventManager.__unbind_single(self.__mouse_button_released_handler_dict, int(button))
        self.__weak_mouse_button_release_callbacks.clear()

    def bind_mouse_position(
        self,
        callback: Callable[[tuple[float, float]], Any] | weakref.WeakMethod[Callable[[tuple[float, float]], Any]],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):

            def unbind(self: EventManager, callback: _MousePositionCallback) -> None:
                self.unbind_mouse_position(callback)

            obj = self.__get_weak_method_info(callback)[1]

            callback = self.__build_callback_from_method(
                callback,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_position_callbacks[obj],
            )

        mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = self.__mouse_pos_handler_list
        mouse_pos_handler_list.add(callback)

    def unbind_mouse_position(
        self,
        callback_to_remove: Callable[[tuple[float, float]], Any] | weakref.WeakMethod[Callable[[tuple[float, float]], Any]],
    ) -> None:
        if isinstance(callback_to_remove, weakref.WeakMethod):
            method, obj = self.__get_weak_method_info(callback_to_remove)
            callback_to_remove = self.__weak_mouse_position_callbacks[obj].pop(method)

        mouse_pos_handler_list: OrderedSet[_MousePositionCallback] = self.__mouse_pos_handler_list
        mouse_pos_handler_list.remove(callback_to_remove)

    @overload
    def weak_bind(self, event_cls: type[_TE], callback: Callable[[_T, _TE], bool], obj: _T) -> None:
        ...

    @overload
    def weak_bind(self, event_cls: None, callback: Callable[[_T, Event], bool], obj: _T) -> None:
        ...

    def weak_bind(self, event_cls: type[Event] | None, callback: Callable[[_T, Event], bool], obj: _T) -> None:  # type: ignore[misc]
        def unbind(self: EventManager, callback: Callable[[Event], bool]) -> None:
            self.unbind(event_cls, callback)

        return self.bind(
            event_cls,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=False,
                unbind_on_delete=unbind,
                callback_register=self.__weak_event_callbacks[obj][event_cls],
            ),
        )

    @overload
    def weak_unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_T, _TE], bool], obj: _T) -> None:
        ...

    @overload
    def weak_unbind(self, event_cls: None, callback_to_remove: Callable[[_T, Event], bool], obj: _T) -> None:
        ...

    def weak_unbind(self, event_cls: type[Event] | None, callback_to_remove: Callable[[_T, Event], bool], obj: _T) -> None:  # type: ignore[misc]
        self.unbind(event_cls, self.__weak_event_callbacks[obj][event_cls].pop(callback_to_remove))

    @overload
    def weak_bind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_T, _TE], bool]], obj: _T) -> None:
        ...

    @overload
    def weak_bind_all(self, event_cls: None, sequence: Iterable[Callable[[_T, Event], bool]], obj: _T) -> None:
        ...

    def weak_bind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[_T, Event], bool]], obj: _T) -> None:  # type: ignore[misc]
        bind = self.weak_bind
        for callback in sequence:
            bind(event_cls, callback, obj)

    @overload
    def weak_unbind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_T, _TE], bool]], obj: _T) -> None:
        ...

    @overload
    def weak_unbind_all(self, event_cls: None, sequence: Iterable[Callable[[_T, Event], bool]], obj: _T) -> None:
        ...

    def weak_unbind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[_T, Event], bool]], obj: _T) -> None:  # type: ignore[misc]
        unbind = self.weak_unbind
        for callback in sequence:
            unbind(event_cls, callback, obj)

    def weak_bind_key(self, key: int, callback: Callable[[_T, KeyEvent], Any], obj: _T) -> None:
        self.weak_bind_key_press(key, callback, obj)
        self.weak_bind_key_release(key, callback, obj)

    def weak_bind_key_press(self, key: int, callback: Callable[[_T, KeyDownEvent], Any], obj: _T) -> None:
        def unbind(self: EventManager, callback: Callable[[KeyDownEvent], Any]) -> None:
            if self.__key_pressed_handler_dict.get(key) == callback:
                self.unbind_key_press(key)

        return self.bind_key_press(
            key,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_key_press_callbacks[obj][key],
            ),
        )

    def weak_bind_key_release(self, key: int, callback: Callable[[_T, KeyUpEvent], Any], obj: _T) -> None:
        def unbind(self: EventManager, callback: Callable[[KeyUpEvent], Any]) -> None:
            if self.__key_released_handler_dict.get(key) == callback:
                self.unbind_key_release(key)

        return self.bind_key_release(
            key,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_key_release_callbacks[obj][key],
            ),
        )

    def weak_bind_mouse_button(self, button: int, callback: Callable[[_T, MouseButtonEvent], Any], obj: _T) -> None:
        self.weak_bind_mouse_button_press(button, callback, obj)
        self.weak_bind_mouse_button_release(button, callback, obj)

    def weak_bind_mouse_button_press(self, button: int, callback: Callable[[_T, MouseButtonDownEvent], Any], obj: _T) -> None:
        def unbind(self: EventManager, callback: Callable[[MouseButtonDownEvent], Any]) -> None:
            if self.__mouse_button_pressed_handler_dict.get(button) == callback:
                self.unbind_mouse_button(button)

        return self.bind_mouse_button_press(
            button,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_button_press_callbacks[obj][button],
            ),
        )

    def weak_bind_mouse_button_release(self, button: int, callback: Callable[[_T, MouseButtonUpEvent], Any], obj: _T) -> None:
        def unbind(self: EventManager, callback: Callable[[MouseButtonUpEvent], Any]) -> None:
            if self.__mouse_button_released_handler_dict.get(button) == callback:
                self.unbind_mouse_button(button)

        return self.bind_mouse_button_release(
            button,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_button_release_callbacks[obj][button],
            ),
        )

    def weak_bind_mouse_position(self, callback: Callable[[_T, tuple[float, float]], Any], obj: _T) -> None:
        def unbind(self: EventManager, callback: _MousePositionCallback) -> None:
            self.unbind_mouse_position(callback)

        return self.bind_mouse_position(
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_position_callbacks[obj],
            )
        )

    def weak_unbind_mouse_position(self, callback_to_remove: Callable[[_T, tuple[float, float]], Any], obj: _T) -> None:
        return self.unbind_mouse_position(self.__weak_mouse_position_callbacks[obj].pop(callback_to_remove))

    def _process_event(self, event: Event) -> bool:
        event_type: type[Event] = type(event)

        priority_callback_dict = self.__priority_callback_dict
        priority_callback: _EventCallback | None = None
        if priority_callback_dict is not None:
            priority_callback = priority_callback_dict.get(event_type)
            if priority_callback is not None:
                if priority_callback(event):
                    return True
                del priority_callback_dict[event_type]

        if isinstance(event, KeyEvent):
            if self.__handle_key_event(event, priority_callback):
                return True
        elif isinstance(event, MouseButtonEvent):
            if self.__handle_mouse_event(event, priority_callback):
                return True

        for callback in chain(self.__event_handler_dict.get(event_type, ()), self.__other_event_handlers_list):
            if callback is not priority_callback and callback(event):
                if priority_callback_dict is not None:
                    priority_callback_dict[event_type] = callback
                return True
        return False

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)

    def __handle_key_event(self, event: KeyEvent, priority_callback: _EventCallback | None) -> bool:
        callback: Callable[[Any], Any]
        match event:
            case KeyDownEvent(key=key) if key in self.__key_pressed_handler_dict:
                callback = self.__key_pressed_handler_dict[key]
                callback(event)
                return True
            case KeyUpEvent(key=key) if key in self.__key_released_handler_dict:
                callback = self.__key_released_handler_dict[key]
                callback(event)
                return True
        return False

    def __handle_mouse_event(self, event: MouseButtonEvent, priority_callback: _EventCallback | None) -> bool:
        callback: Callable[[Any], Any]
        match event:
            case MouseButtonDownEvent(button=mouse_button) if mouse_button in self.__mouse_button_pressed_handler_dict:
                callback = self.__mouse_button_pressed_handler_dict[mouse_button]
                callback(event)
                return True
            case MouseButtonUpEvent(button=mouse_button) if mouse_button in self.__mouse_button_released_handler_dict:
                callback = self.__mouse_button_released_handler_dict[mouse_button]
                callback(event)
                return True
        return False

    def __build_callback_from_strong_reference(
        self,
        callback: Callable[Concatenate[_T, _P], _U],
        obj: _T,
        dead_ref_fallback_value: _U,
        unbind_on_delete: Callable[[EventManager, Callable[_P, _U]], None],
        callback_register: weakref.WeakKeyDictionary[Callable[Concatenate[_T, _P], _U], Callable[_P, _U]],
    ) -> Callable[_P, _U]:
        try:
            return callback_register[callback]
        except KeyError:
            pass

        selfref = weakref.ref(self)

        def unbind_callback(_: Any) -> None:
            self = selfref()
            callback_register.pop(callback, None)
            if self is not None:
                try:
                    unbind_on_delete(self, callback_wrapper)
                except KeyError:
                    pass

        objref = weakref.ref(obj, unbind_callback)

        def callback_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _U:
            obj = objref()
            if obj is None:
                return dead_ref_fallback_value
            return callback(obj, *args, **kwargs)

        callback_register[callback] = callback_wrapper

        return callback_wrapper

    def __build_callback_from_method(
        self,
        weak_method: weakref.WeakMethod[Callable[_P, _U]],
        dead_ref_fallback_value: _U,
        unbind_on_delete: Callable[[EventManager, Callable[_P, _U]], None] | None,
        callback_register: _WeakCallbackRegister | None,
    ) -> Callable[_P, _U]:
        if not isinstance(weak_method, weakref.WeakMethod):
            raise TypeError("Expected a WeakMethod instance")
        method = weakref_unwrap(weak_method)
        callback: Callable[Concatenate[Any, _P], _U] = getattr(method, "__func__")
        if callback_register is not None:
            try:
                return callback_register[callback]
            except KeyError:
                pass

        selfref = weakref.ref(self)
        callbackref = weakref.ref(callback)

        def unbind_callback(_: Any) -> None:
            self = selfref()
            callback = callbackref()
            if callback is not None and callback_register is not None:
                callback_register.pop(callback, None)
            if self is not None and unbind_on_delete is not None:
                try:
                    unbind_on_delete(self, callback_wrapper)
                except KeyError:
                    pass

        weak_method = weakref.WeakMethod(method, unbind_callback)

        def callback_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _U:
            method = weak_method()
            if method is None:
                return dead_ref_fallback_value
            return method(*args, **kwargs)

        if callback_register is not None:
            callback_register[callback] = callback_wrapper

        return callback_wrapper

    @staticmethod
    def __get_weak_method_info(
        weak_method: weakref.WeakMethod[Callable[_P, _U]]
    ) -> tuple[Callable[Concatenate[Any, _P], _U], Any]:
        method: Any = weakref_unwrap(weak_method)
        return method.__func__, method.__self__


class BoundEventManager(Generic[_T]):
    __slots__ = (
        "__ref",
        "__manager",
        "__weak_event_callbacks",
        "__weak_key_press_callbacks",
        "__weak_key_release_callbacks",
        "__weak_mouse_button_press_callbacks",
        "__weak_mouse_button_release_callbacks",
        "__weak_mouse_position_callbacks",
        "__weakref__",
    )

    __weak_event_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[type[Event] | None, _WeakCallbackRegister]]
    __weak_key_press_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_key_release_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_mouse_button_press_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_mouse_button_release_callbacks: WeakKeyDefaultDictionary[Any, defaultdict[int, _WeakCallbackRegister]]
    __weak_mouse_position_callbacks: WeakKeyDefaultDictionary[Any, _WeakCallbackRegister]

    def __init__(
        self,
        obj: _T,
        *,
        priority_callbacks: bool = True,
        weakref_callback: Callable[[], None] | None = None,
    ) -> None:
        selfref: weakref.ref[BoundEventManager[_T]] = weakref.ref(self)

        def unbind_all(_: Any, /) -> None:
            self = selfref()
            if self is not None:
                self.__manager.clear()
                self.__weak_event_callbacks.clear()
                self.__weak_key_press_callbacks.clear()
                self.__weak_key_release_callbacks.clear()
                self.__weak_mouse_button_press_callbacks.clear()
                self.__weak_mouse_button_release_callbacks.clear()
                self.__weak_mouse_position_callbacks.clear()
            if weakref_callback is not None:
                weakref_callback()

        self.__ref: weakref.ref[_T] = weakref.ref(obj, unbind_all)
        self.__manager: EventManager = EventManager(priority_callbacks=priority_callbacks)
        self.__weak_event_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_key_press_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_key_release_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_mouse_button_press_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_mouse_button_release_callbacks = WeakKeyDefaultDictionary(lambda: defaultdict(weakref.WeakKeyDictionary))
        self.__weak_mouse_position_callbacks = WeakKeyDefaultDictionary(weakref.WeakKeyDictionary)

    def __del__(self) -> None:
        self.__manager.clear()
        self.__weak_event_callbacks.clear()
        self.__weak_key_press_callbacks.clear()
        self.__weak_key_release_callbacks.clear()
        self.__weak_mouse_button_press_callbacks.clear()
        self.__weak_mouse_button_release_callbacks.clear()
        self.__weak_mouse_position_callbacks.clear()

    @overload
    def bind(
        self,
        event_cls: type[_TE],
        callback: Callable[[_T, _TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]],
    ) -> None:
        ...

    @overload
    def bind(
        self,
        event_cls: None,
        callback: Callable[[_T, Event], bool] | weakref.WeakMethod[Callable[[Event], bool]],
    ) -> None:
        ...

    def bind(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        callback: weakref.WeakMethod[Callable[[Event], bool]] | Callable[[_T, Event], bool],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback, weakref.WeakMethod):
            self.__verify_weak_method(callback)
            return self.__manager.bind(event_cls, callback)
        return self.__manager.weak_bind(event_cls, callback, obj)

    @overload
    def unbind(
        self,
        event_cls: type[_TE],
        callback_to_remove: Callable[[_T, _TE], bool] | weakref.WeakMethod[Callable[[_TE], bool]],
    ) -> None:
        ...

    @overload
    def unbind(
        self,
        event_cls: None,
        callback_to_remove: Callable[[_T, Event], bool] | weakref.WeakMethod[Callable[[Event], bool]],
    ) -> None:
        ...

    def unbind(  # type: ignore[misc]
        self,
        event_cls: type[Event] | None,
        callback_to_remove: weakref.WeakMethod[Callable[[Event], bool]] | Callable[[_T, Event], bool],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback_to_remove, weakref.WeakMethod):
            self.__verify_weak_method(callback_to_remove)
            return self.__manager.unbind(event_cls, callback_to_remove)
        return self.__manager.weak_unbind(event_cls, callback_to_remove, obj)

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
    def bind_key(self, key: int, callback: Callable[[_T, KeyEvent], Any]) -> None:
        ...

    @overload
    def bind_key(self, key: int, callback: weakref.WeakMethod[Callable[[KeyEvent], Any]]) -> None:
        ...

    def bind_key(self, key: int, callback: Callable[..., Any]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(
        self,
        key: int,
        callback: weakref.WeakMethod[Callable[[KeyDownEvent], Any]] | Callable[[_T, KeyDownEvent], Any],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback, weakref.WeakMethod):
            self.__verify_weak_method(callback)
            return self.__manager.bind_key_press(key, callback)
        return self.__manager.weak_bind_key_press(key, callback, obj)

    def bind_key_release(
        self,
        key: int,
        callback: weakref.WeakMethod[Callable[[KeyUpEvent], Any]] | Callable[[_T, KeyUpEvent], Any],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback, weakref.WeakMethod):
            self.__verify_weak_method(callback)
            return self.__manager.bind_key_release(key, callback)
        return self.__manager.weak_bind_key_release(key, callback, obj)

    def unbind_key(self, key: int) -> None:
        self.unbind_key_press(key)
        self.unbind_key_release(key)

    def unbind_key_press(self, key: int) -> None:
        self.__manager.unbind_key_press(key)
        self.__weak_key_press_callbacks.clear()

    def unbind_key_release(self, key: int) -> None:
        self.__manager.unbind_key_release(key)
        self.__weak_key_release_callbacks.clear()

    @overload
    def bind_mouse_button(self, button: int, callback: Callable[[_T, MouseButtonEvent], Any]) -> None:
        ...

    @overload
    def bind_mouse_button(self, button: int, callback: weakref.WeakMethod[Callable[[MouseButtonEvent], Any]]) -> None:
        ...

    def bind_mouse_button(self, button: int, callback: Callable[..., Any]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(
        self,
        button: int,
        callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], Any]] | Callable[[_T, MouseButtonDownEvent], Any],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback, weakref.WeakMethod):
            self.__verify_weak_method(callback)
            return self.__manager.bind_mouse_button_press(button, callback)
        return self.__manager.weak_bind_mouse_button_press(button, callback, obj)

    def bind_mouse_button_release(
        self,
        button: int,
        callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], Any]] | Callable[[_T, MouseButtonUpEvent], Any],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback, weakref.WeakMethod):
            self.__verify_weak_method(callback)
            return self.__manager.bind_mouse_button_release(button, callback)
        return self.__manager.weak_bind_mouse_button_release(button, callback, obj)

    def unbind_mouse_button(self, button: int) -> None:
        self.unbind_mouse_button_press(button)
        self.unbind_mouse_button_release(button)

    def unbind_mouse_button_press(self, button: int) -> None:
        self.__manager.unbind_mouse_button_press(button)
        self.__weak_mouse_button_press_callbacks.clear()

    def unbind_mouse_button_release(self, button: int) -> None:
        self.__manager.unbind_mouse_button_release(button)
        self.__weak_mouse_button_release_callbacks.clear()

    def bind_mouse_position(
        self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], Any]] | Callable[[_T, tuple[float, float]], Any]
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback, weakref.WeakMethod):
            self.__verify_weak_method(callback)
            return self.__manager.bind_mouse_position(callback)
        return self.__manager.weak_bind_mouse_position(callback, obj)

    def unbind_mouse_position(
        self,
        callback_to_remove: weakref.WeakMethod[Callable[[tuple[float, float]], Any]] | Callable[[_T, tuple[float, float]], Any],
    ) -> None:
        obj = weakref_unwrap(self.__ref)
        if isinstance(callback_to_remove, weakref.WeakMethod):
            self.__verify_weak_method(callback_to_remove)
            return self.__manager.unbind_mouse_position(callback_to_remove)
        return self.__manager.weak_unbind_mouse_position(callback_to_remove, obj)

    @overload
    def weak_bind(self, event_cls: type[_TE], callback: Callable[[_U, _T, _TE], bool], obj: _U) -> None:
        ...

    @overload
    def weak_bind(self, event_cls: None, callback: Callable[[_U, _T, Event], bool], obj: _U) -> None:
        ...

    def weak_bind(self, event_cls: type[Event] | None, callback: Callable[[_U, _T, Event], bool], obj: _U) -> None:  # type: ignore[misc]
        def unbind(self: EventManager, callback: Callable[[Event], bool]) -> None:
            self.unbind(event_cls, callback)

        return self.__manager.bind(
            event_cls,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=False,
                unbind_on_delete=unbind,
                callback_register=self.__weak_event_callbacks[obj][event_cls],
            ),
        )

    @overload
    def weak_unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_U, _T, _TE], bool], obj: _U) -> None:
        ...

    @overload
    def weak_unbind(self, event_cls: None, callback_to_remove: Callable[[_U, _T, Event], bool], obj: _U) -> None:
        ...

    def weak_unbind(self, event_cls: type[Event] | None, callback_to_remove: Callable[[_U, _T, Event], bool], obj: _U) -> None:  # type: ignore[misc]
        self.__manager.unbind(event_cls, self.__weak_event_callbacks[obj][event_cls].pop(callback_to_remove))

    @overload
    def weak_bind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_U, _T, _TE], bool]], obj: _U) -> None:
        ...

    @overload
    def weak_bind_all(self, event_cls: None, sequence: Iterable[Callable[[_U, _T, Event], bool]], obj: _U) -> None:
        ...

    def weak_bind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[_U, _T, Event], bool]], obj: _U) -> None:  # type: ignore[misc]
        bind = self.weak_bind
        for callback in sequence:
            bind(event_cls, callback, obj)

    @overload
    def weak_unbind_all(self, event_cls: type[_TE], sequence: Iterable[Callable[[_U, _T, _TE], bool]], obj: _U) -> None:
        ...

    @overload
    def weak_unbind_all(self, event_cls: None, sequence: Iterable[Callable[[_U, _T, Event], bool]], obj: _U) -> None:
        ...

    def weak_unbind_all(self, event_cls: type[Event] | None, sequence: Iterable[Callable[[_U, _T, Event], bool]], obj: _U) -> None:  # type: ignore[misc]
        unbind = self.weak_unbind
        for callback in sequence:
            unbind(event_cls, callback, obj)

    def weak_bind_key(self, key: int, callback: Callable[[_U, _T, KeyEvent], Any], obj: _U) -> None:
        self.weak_bind_key_press(key, callback, obj)
        self.weak_bind_key_release(key, callback, obj)

    def weak_bind_key_press(self, key: int, callback: Callable[[_U, _T, KeyDownEvent], Any], obj: _U) -> None:
        def unbind(self: EventManager, callback: Callable[[KeyDownEvent], Any]) -> None:
            if self.__key_pressed_handler_dict.get(key) == callback:
                self.unbind_key_press(key)

        return self.__manager.bind_key_press(
            key,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_key_press_callbacks[obj][key],
            ),
        )

    def weak_bind_key_release(self, key: int, callback: Callable[[_U, _T, KeyUpEvent], Any], obj: _U) -> None:
        def unbind(self: EventManager, callback: Callable[[KeyUpEvent], Any]) -> None:
            if self.__key_released_handler_dict.get(key) == callback:
                self.unbind_key_release(key)

        return self.__manager.bind_key_release(
            key,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_key_release_callbacks[obj][key],
            ),
        )

    def weak_bind_mouse_button(self, button: int, callback: Callable[[_U, _T, MouseButtonEvent], Any], obj: _U) -> None:
        self.weak_bind_mouse_button_press(button, callback, obj)
        self.weak_bind_mouse_button_release(button, callback, obj)

    def weak_bind_mouse_button_press(self, button: int, callback: Callable[[_U, _T, MouseButtonDownEvent], Any], obj: _U) -> None:
        def unbind(self: EventManager, callback: Callable[[MouseButtonDownEvent], Any]) -> None:
            if self.__mouse_button_pressed_handler_dict.get(button) == callback:
                self.unbind_mouse_button(button)

        return self.__manager.bind_mouse_button_press(
            button,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_button_press_callbacks[obj][button],
            ),
        )

    def weak_bind_mouse_button_release(self, button: int, callback: Callable[[_U, _T, MouseButtonUpEvent], Any], obj: _U) -> None:
        def unbind(self: EventManager, callback: Callable[[MouseButtonUpEvent], Any]) -> None:
            if self.__mouse_button_released_handler_dict.get(button) == callback:
                self.unbind_mouse_button(button)

        return self.__manager.bind_mouse_button_release(
            button,
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_button_release_callbacks[obj][button],
            ),
        )

    def weak_bind_mouse_position(self, callback: Callable[[_U, _T, tuple[float, float]], Any], obj: _U) -> None:
        def unbind(self: EventManager, callback: _MousePositionCallback) -> None:
            self.unbind_mouse_position(callback)

        return self.__manager.bind_mouse_position(
            self.__build_callback_from_strong_reference(
                callback,
                obj,
                dead_ref_fallback_value=None,
                unbind_on_delete=unbind,
                callback_register=self.__weak_mouse_position_callbacks[obj],
            )
        )

    def weak_unbind_mouse_position(self, callback_to_remove: Callable[[_U, _T, tuple[float, float]], Any], obj: _U) -> None:
        return self.__manager.unbind_mouse_position(self.__weak_mouse_position_callbacks[obj].pop(callback_to_remove))

    def _process_event(self, event: Event) -> bool:
        return self.__manager._process_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        return self.__manager._handle_mouse_position(mouse_pos)

    def __verify_weak_method(self, weak_method: weakref.WeakMethod[Callable[_P, _U]]) -> None:
        method: Any = weakref_unwrap(weak_method)
        if method.__self__ is not (obj := weakref_unwrap(self.__ref)):
            raise ValueError(f"bound object of weak method ({method.__self__!r}) is not {obj!r}")

    def __build_callback_from_strong_reference(
        self,
        callback: Callable[Concatenate[_U, _T, _P], _V],
        obj: _U,
        dead_ref_fallback_value: _V,
        unbind_on_delete: Callable[[EventManager, Callable[_P, _V]], None],
        callback_register: weakref.WeakKeyDictionary[Callable[Concatenate[_U, _T, _P], _V], Callable[_P, _V]],
    ) -> Callable[_P, _V]:
        try:
            return callback_register[callback]
        except KeyError:
            pass

        manager_ref = weakref.ref(self.__manager)

        def unbind_callback(_: Any) -> None:
            manager = manager_ref()
            callback_register.pop(callback, None)
            if manager is not None:
                try:
                    unbind_on_delete(manager, callback_wrapper)
                except KeyError:
                    pass

        selfref = self.__ref
        objref = weakref.ref(obj, unbind_callback)

        def callback_wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _V:
            self = selfref()
            obj = objref()
            if self is None or obj is None:
                return dead_ref_fallback_value
            return callback(obj, self, *args, **kwargs)

        callback_register[callback] = callback_wrapper

        return callback_wrapper

    @property
    def static(self) -> EventManager:
        return self.__manager

    @property
    def __self__(self) -> _T:
        return weakref_unwrap(self.__ref)


del _pg_constants, _BuiltinEventMeta
del _ASSOCIATIONS, _PYGAME_EVENT_TYPE, _BUILTIN_ASSOCIATIONS, _BUILTIN_PYGAME_EVENT_TYPE
