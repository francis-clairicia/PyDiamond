# -*- coding: Utf-8 -*-
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
from collections import ChainMap
from contextlib import suppress
from dataclasses import Field, asdict as dataclass_asdict, dataclass, field, fields
from enum import IntEnum, unique
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Final,
    Generic,
    Literal as L,
    Sequence,
    SupportsInt,
    TypeAlias,
    TypeVar,
    cast,
    overload,
)

import pygame.constants as _pg_constants
from pygame.event import Event as _PygameEvent, custom_type as _pg_event_custom_type, event_name as _pg_event_name

from ..system.namespace import ClassNamespaceMeta
from ..system.object import Object, ObjectMeta, final
from ..system.utils.abc import isabstract
from ..system.utils.weakref import weakref_unwrap
from .keyboard import Keyboard
from .mouse import Mouse

if TYPE_CHECKING:
    from _typeshed import Self

    from ..audio.music import Music
    from ..graphics.surface import Surface

_T = TypeVar("_T")

_ASSOCIATIONS: dict[SupportsInt, type[Event]] = {}
_PYGAME_EVENT_TYPE: dict[type[Event], SupportsInt] = {}


class EventMeta(ObjectMeta):
    __associations: Final[dict[SupportsInt, type[Event]]] = _ASSOCIATIONS
    __type: Final[dict[type[Event], SupportsInt]] = _PYGAME_EVENT_TYPE

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
        try:
            Event
        except NameError:
            pass
        else:
            if len(bases) != 1 or not issubclass(bases[0], Event):
                raise TypeError(f"{name!r} must only inherits from Event without multiple inheritance")
            if not bases[0].is_model():
                raise TypeError(f"{name!r}: {bases[0].__qualname__} is a not a Event model class")
        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        setattr(cls, "_model_", bool(model))
        if not cls.is_model() and not issubclass(cls, BuiltinEvent):
            cls = final(cls)
            event_type: SupportsInt = _pg_event_custom_type()
            if event_type in EventFactory.associations:  # Should not happen
                event_cls = EventFactory.associations[event_type]
                raise SystemError(f"Event with type {event_type!r} already exists: {event_cls}")
            event_cls = cast(type[Event], cls)
            mcs.__associations[event_type] = event_cls
            mcs.__type[event_cls] = event_type
        return cls

    def __call__(cls, *args: Any, **kwds: Any) -> Any:
        if cls.is_model():
            raise TypeError("Event models are not instanciable")
        return super().__call__(*args, **kwds)

    def __setattr__(cls, __name: str, __value: Any) -> None:
        # if __name in {} and hasattr(cls, __name):
        #     raise AttributeError("Read-only attribute")
        if __name in {"_model_"} and __name in vars(cls):
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(cls, __name: str) -> None:
        if __name in {"_model_"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)

    def is_model(cls) -> bool:
        return bool(isabstract(cls) or getattr(cls, "_model_"))


_BUILTIN_ASSOCIATIONS: dict[SupportsInt, type[Event]] = {}
_BUILTIN_PYGAME_EVENT_TYPE: dict[type[Event], SupportsInt] = {}


@final
class _BuiltinEventMeta(EventMeta):
    __associations: Final[dict[SupportsInt, type[Event]]] = _BUILTIN_ASSOCIATIONS  # type: ignore[misc]
    __type: Final[dict[type[Event], SupportsInt]] = _BUILTIN_PYGAME_EVENT_TYPE  # type: ignore[misc]

    def __new__(mcs, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _BuiltinEventMeta:
        try:
            BuiltinEvent
        except NameError:
            pass
        else:
            if all(event_type in mcs.__associations for event_type in BuiltinEvent.Type):
                raise TypeError("Trying to create custom event from BuiltinEvent class")
            assert len(bases) == 1 and issubclass(bases[0], BuiltinEvent)
            cls = super().__new__(mcs, name, bases, namespace, **kwargs)
            assert not cls.is_model()
            event_type: Any = getattr(cls, "type")
            if isinstance(event_type, Field):
                event_type = event_type.default
            assert isinstance(event_type, BuiltinEvent.Type), f"Got {event_type!r}"
            assert event_type not in mcs.__associations, f"{event_type!r} event already taken"
            event_cls = cast(type[BuiltinEvent], cls)
            mcs.__associations[event_type] = event_cls
            mcs.__type[event_cls] = event_type
            return cls
        return super().__new__(mcs, name, bases, namespace, **kwargs)

    def __setattr__(cls, __name: str, __value: Any) -> None:
        if __name in {"Type"}:
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(cls, __name: str) -> None:
        if __name in {"Type"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)


class Event(Object, metaclass=EventMeta):
    __slots__ = ()

    @classmethod
    @abstractmethod
    def from_dict(cls: type[Self], event_dict: dict[str, Any]) -> Self:
        raise NotImplementedError

    @abstractmethod
    def to_dict(self) -> dict[str, Any]:
        raise NotImplementedError


# TODO (3.11) dataclass_transform (PEP-681)
@dataclass(kw_only=True)
class BuiltinEvent(Event, metaclass=_BuiltinEventMeta, model=True):
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
        MUSICEND = _pg_event_custom_type()
        SCREENSHOT = _pg_event_custom_type()

        def __repr__(self) -> str:
            return f"<{self.name} ({self.real_name}): {self.value}>"

        @property
        def real_name(self) -> str:
            return _pg_event_name(self)

    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name in {"type"}:
            raise AttributeError("Read-only attribute")
        return super().__setattr__(__name, __value)

    def __delattr__(self, __name: str) -> None:
        if __name in {"type"}:
            raise AttributeError("Read-only attribute")
        return super().__delattr__(__name)

    @classmethod
    def from_dict(cls: type[Self], event_dict: dict[str, Any]) -> Self:
        event_fields: Sequence[str] = tuple(f.name for f in fields(cls))
        kwargs: dict[str, Any] = {k: event_dict[k] for k in filter(event_fields.__contains__, event_dict)}
        return cls(**kwargs)

    def to_dict(self) -> dict[str, Any]:
        return dataclass_asdict(self)

    type: ClassVar[BuiltinEvent.Type] = field(init=False)


@final
@dataclass(kw_only=True)
class KeyDownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.KEYDOWN]] = field(default=BuiltinEvent.Type.KEYDOWN, init=False)
    key: int
    mod: int
    unicode: str
    scancode: int


@final
@dataclass(kw_only=True)
class KeyUpEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.KEYUP]] = field(default=BuiltinEvent.Type.KEYUP, init=False)
    key: int
    mod: int


KeyEvent: TypeAlias = KeyDownEvent | KeyUpEvent


@final
@dataclass(kw_only=True)
class MouseButtonDownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEBUTTONDOWN]] = field(default=BuiltinEvent.Type.MOUSEBUTTONDOWN, init=False)
    pos: tuple[int, int]
    button: int


@final
@dataclass(kw_only=True)
class MouseButtonUpEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEBUTTONUP]] = field(default=BuiltinEvent.Type.MOUSEBUTTONUP, init=False)
    pos: tuple[int, int]
    button: int


MouseButtonEvent: TypeAlias = MouseButtonDownEvent | MouseButtonUpEvent


@final
@dataclass(kw_only=True)
class MouseMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEMOTION]] = field(default=BuiltinEvent.Type.MOUSEMOTION, init=False)
    pos: tuple[int, int]
    rel: tuple[int, int]
    buttons: tuple[bool, bool, bool]


@final
@dataclass(kw_only=True)
class MouseWheelEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MOUSEWHEEL]] = field(default=BuiltinEvent.Type.MOUSEWHEEL, init=False)
    flipped: bool
    x: int
    y: int


MouseEvent: TypeAlias = MouseButtonEvent | MouseWheelEvent | MouseMotionEvent


@final
@dataclass(kw_only=True)
class JoyAxisMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYAXISMOTION]] = field(default=BuiltinEvent.Type.JOYAXISMOTION, init=False)
    instance_id: int
    axis: int
    value: float


@final
@dataclass(kw_only=True)
class JoyBallMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYBALLMOTION]] = field(default=BuiltinEvent.Type.JOYBALLMOTION, init=False)
    instance_id: int
    ball: int
    rel: float


@final
@dataclass(kw_only=True)
class JoyHatMotionEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYHATMOTION]] = field(default=BuiltinEvent.Type.JOYHATMOTION, init=False)
    instance_id: int
    hat: int
    value: tuple[int, int]


@final
@dataclass(kw_only=True)
class JoyButtonDownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYBUTTONDOWN]] = field(default=BuiltinEvent.Type.JOYBUTTONDOWN, init=False)
    instance_id: int
    button: int


@final
@dataclass(kw_only=True)
class JoyButtonUpEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYBUTTONUP]] = field(default=BuiltinEvent.Type.JOYBUTTONUP, init=False)
    instance_id: int
    button: int


JoyButtonEvent: TypeAlias = JoyButtonDownEvent | JoyButtonUpEvent


@final
@dataclass(kw_only=True)
class JoyDeviceAddedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYDEVICEADDED]] = field(default=BuiltinEvent.Type.JOYDEVICEADDED, init=False)
    device_index: int


@final
@dataclass(kw_only=True)
class JoyDeviceRemovedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.JOYDEVICEREMOVED]] = field(default=BuiltinEvent.Type.JOYDEVICEREMOVED, init=False)
    instance_id: int


@final
@dataclass(kw_only=True)
class TextEditingEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.TEXTEDITING]] = field(default=BuiltinEvent.Type.TEXTEDITING, init=False)
    text: str
    start: int
    length: int


@final
@dataclass(kw_only=True)
class TextInputEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.TEXTINPUT]] = field(default=BuiltinEvent.Type.TEXTINPUT, init=False)
    text: str


TextEvent: TypeAlias = TextEditingEvent | TextInputEvent


@final
@dataclass(init=False)
class UserEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.USEREVENT]] = field(default=BuiltinEvent.Type.USEREVENT, init=False)
    code: int = 0

    def __init__(self, *, code: int = 0, **kwargs: Any) -> None:
        self.code = code
        self.__dict__.update(kwargs)

    if TYPE_CHECKING:

        def __getattr__(self, name: str, /) -> Any:  # Indicate dynamic attribute
            ...

    @classmethod
    def from_dict(cls, event_dict: dict[str, Any]) -> UserEvent:
        return cls(**event_dict)

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


@final
@dataclass(kw_only=True)
class WindowShownEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWSHOWN]] = field(default=BuiltinEvent.Type.WINDOWSHOWN, init=False)


@final
@dataclass(kw_only=True)
class WindowHiddenEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWHIDDEN]] = field(default=BuiltinEvent.Type.WINDOWHIDDEN, init=False)


@final
@dataclass(kw_only=True)
class WindowExposedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWEXPOSED]] = field(default=BuiltinEvent.Type.WINDOWEXPOSED, init=False)


@final
@dataclass(kw_only=True)
class WindowMovedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWMOVED]] = field(default=BuiltinEvent.Type.WINDOWMOVED, init=False)
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowResizedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWRESIZED]] = field(default=BuiltinEvent.Type.WINDOWRESIZED, init=False)
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowSizeChangedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWSIZECHANGED]] = field(default=BuiltinEvent.Type.WINDOWSIZECHANGED, init=False)
    x: int
    y: int


@final
@dataclass(kw_only=True)
class WindowMinimizedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWMINIMIZED]] = field(default=BuiltinEvent.Type.WINDOWMINIMIZED, init=False)


@final
@dataclass(kw_only=True)
class WindowMaximizedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWMAXIMIZED]] = field(default=BuiltinEvent.Type.WINDOWMAXIMIZED, init=False)


@final
@dataclass(kw_only=True)
class WindowRestoredEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWRESTORED]] = field(default=BuiltinEvent.Type.WINDOWRESTORED, init=False)


@final
@dataclass(kw_only=True)
class WindowEnterEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWENTER]] = field(default=BuiltinEvent.Type.WINDOWENTER, init=False)


@final
@dataclass(kw_only=True)
class WindowLeaveEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWLEAVE]] = field(default=BuiltinEvent.Type.WINDOWLEAVE, init=False)


@final
@dataclass(kw_only=True)
class WindowFocusGainedEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWFOCUSGAINED]] = field(default=BuiltinEvent.Type.WINDOWFOCUSGAINED, init=False)


@final
@dataclass(kw_only=True)
class WindowFocusLostEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWFOCUSLOST]] = field(default=BuiltinEvent.Type.WINDOWFOCUSLOST, init=False)


@final
@dataclass(kw_only=True)
class WindowTakeFocusEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.WINDOWTAKEFOCUS]] = field(default=BuiltinEvent.Type.WINDOWTAKEFOCUS, init=False)


@final
@dataclass(kw_only=True)
class MusicEndEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.MUSICEND]] = field(default=BuiltinEvent.Type.MUSICEND, init=False)
    finished: Music
    next: Music | None


@final
@dataclass(kw_only=True)
class ScreenshotEvent(BuiltinEvent):
    type: ClassVar[L[BuiltinEvent.Type.SCREENSHOT]] = field(default=BuiltinEvent.Type.SCREENSHOT, init=False)
    filepath: str
    screen: Surface


def _check_event_types_association() -> None:
    if unbound_types := set(filter(lambda e: e not in _BUILTIN_ASSOCIATIONS, BuiltinEvent.Type)):
        raise SystemError(
            f"The following events do not have an associated BuiltinEvent class: {', '.join(e.name for e in unbound_types)}"
        )


_check_event_types_association()

del _check_event_types_association

_EventCallback: TypeAlias = Callable[[Event], bool | None]
_TE = TypeVar("_TE", bound=Event)

_MousePositionCallback: TypeAlias = Callable[[tuple[float, float]], None]


class EventFactoryError(Exception):
    pass


class UnknownEventTypeError(EventFactoryError):
    pass


class EventFactory(metaclass=ClassNamespaceMeta, frozen=True):
    associations: Final[MappingProxyType[SupportsInt, type[Event]]] = MappingProxyType(
        ChainMap(_BUILTIN_ASSOCIATIONS, _ASSOCIATIONS)
    )
    pygame_type: Final[MappingProxyType[type[Event], SupportsInt]] = MappingProxyType(
        ChainMap(_BUILTIN_PYGAME_EVENT_TYPE, _PYGAME_EVENT_TYPE)
    )

    NUMEVENTS: Final[int] = _pg_constants.NUMEVENTS

    @staticmethod
    def from_pygame_event(event: _PygameEvent, *, handle_user_events: bool = True) -> Event:
        try:
            event_cls: type[Event] = EventFactory.associations[event.type]
        except KeyError as exc:
            if handle_user_events and BuiltinEvent.Type.USEREVENT < event.type < EventFactory.NUMEVENTS:
                return UserEvent.from_dict(event.__dict__ | {"code": event.type})
            raise UnknownEventTypeError(f"Unknown event with type {_pg_event_name(event.type)!r}") from exc
        return event_cls.from_dict(event.__dict__)

    @staticmethod
    def make_pygame_event(event: Event) -> _PygameEvent:
        assert not event.__class__.is_model()  # Should not happen but who knows...?
        event_dict = event.to_dict()
        event_dict.pop("type", None)
        event_type = EventFactory.pygame_type[event.__class__]
        return _PygameEvent(int(event_type), event_dict)


class EventManager:

    __slots__ = (
        "__event_handler_dict",
        "__key_pressed_handler_dict",
        "__key_released_handler_dict",
        "__mouse_button_pressed_handler_dict",
        "__mouse_button_released_handler_dict",
        "__mouse_pos_handler_list",
        "__other_manager_list",
        "__priority_callback",
        "__priority_manager",
    )

    def __init__(self) -> None:
        self.__event_handler_dict: dict[type[Event], list[_EventCallback]] = dict()
        self.__key_pressed_handler_dict: dict[Keyboard.Key, list[_EventCallback]] = dict()
        self.__key_released_handler_dict: dict[Keyboard.Key, list[_EventCallback]] = dict()
        self.__mouse_button_pressed_handler_dict: dict[Mouse.Button, list[_EventCallback]] = dict()
        self.__mouse_button_released_handler_dict: dict[Mouse.Button, list[_EventCallback]] = dict()
        self.__mouse_pos_handler_list: list[_MousePositionCallback] = list()
        self.__other_manager_list: list[EventManager] = list()
        self.__priority_callback: dict[type[Event], _EventCallback] = dict()
        self.__priority_manager: dict[type[Event], EventManager] = dict()

    @overload
    @staticmethod
    def __bind(
        handler_dict: dict[type[Event], list[_EventCallback]],
        key: type[Event],
        callback: Callable[[_TE], bool | None],
    ) -> None:
        ...

    @overload
    @staticmethod
    def __bind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        ...

    @staticmethod
    def __bind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        try:
            handler_list: list[_EventCallback] = handler_dict[key]
        except KeyError:
            handler_dict[key] = handler_list = []
        if callback not in handler_list:
            handler_list.append(cast(_EventCallback, callback))

    @overload
    @staticmethod
    def __unbind(
        handler_dict: dict[type[Event], list[_EventCallback]],
        key: type[Event],
        callback: Callable[[_TE], bool | None],
    ) -> None:
        ...

    @overload
    @staticmethod
    def __unbind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        ...

    @staticmethod
    def __unbind(handler_dict: dict[_T, list[_EventCallback]], key: _T, callback: Callable[[_TE], bool | None]) -> None:
        with suppress(KeyError, ValueError):
            handler_dict[key].remove(cast(_EventCallback, callback))

    def bind(self, event_cls: type[_TE], callback: Callable[[_TE], bool | None]) -> None:
        if not issubclass(event_cls, Event):
            raise TypeError("Invalid argument")
        EventManager.__bind(self.__event_handler_dict, event_cls, callback)

    def unbind(self, event_cls: type[_TE], callback_to_remove: Callable[[_TE], bool | None]) -> None:
        if not issubclass(event_cls, Event):
            raise TypeError("Invalid argument")
        EventManager.__unbind(self.__event_handler_dict, event_cls, callback_to_remove)
        for event_type in tuple(
            event_type
            for event_type, priority_callback in self.__priority_callback.items()
            if priority_callback is callback_to_remove
        ):
            self.__priority_callback.pop(event_type)

    def unbind_all(self) -> None:
        self.__event_handler_dict.clear()
        self.__key_pressed_handler_dict.clear()
        self.__key_released_handler_dict.clear()
        self.__mouse_button_pressed_handler_dict.clear()
        self.__mouse_button_released_handler_dict.clear()
        self.__mouse_pos_handler_list.clear()
        self.__priority_callback.clear()
        self.__priority_manager.clear()

    def bind_key(self, key: Keyboard.Key, callback: Callable[[KeyEvent], None]) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    def bind_key_press(self, key: Keyboard.Key, callback: Callable[[KeyDownEvent], None]) -> None:
        EventManager.__bind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback)

    def bind_key_release(self, key: Keyboard.Key, callback: Callable[[KeyUpEvent], None]) -> None:
        EventManager.__bind(self.__key_released_handler_dict, Keyboard.Key(key), callback)

    def unbind_key(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyEvent], None]) -> None:
        self.unbind_key_press(key, callback_to_remove)
        self.unbind_key_release(key, callback_to_remove)

    def unbind_key_press(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyDownEvent], None]) -> None:
        EventManager.__unbind(self.__key_pressed_handler_dict, Keyboard.Key(key), callback_to_remove)

    def unbind_key_release(self, key: Keyboard.Key, callback_to_remove: Callable[[KeyUpEvent], None]) -> None:
        EventManager.__unbind(self.__key_released_handler_dict, Keyboard.Key(key), callback_to_remove)

    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[[MouseButtonEvent], None]) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    def bind_mouse_button_press(self, button: Mouse.Button, callback: Callable[[MouseButtonDownEvent], None]) -> None:
        EventManager.__bind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback)

    def bind_mouse_button_release(self, button: Mouse.Button, callback: Callable[[MouseButtonUpEvent], None]) -> None:
        EventManager.__bind(self.__mouse_button_released_handler_dict, Mouse.Button(button), callback)

    def unbind_mouse_button(self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonEvent], None]) -> None:
        self.unbind_mouse_button_press(button, callback_to_remove)
        self.unbind_mouse_button_release(button, callback_to_remove)

    def unbind_mouse_button_press(self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonDownEvent], None]) -> None:
        EventManager.__unbind(self.__mouse_button_pressed_handler_dict, Mouse.Button(button), callback_to_remove)

    def unbind_mouse_button_release(self, button: Mouse.Button, callback_to_remove: Callable[[MouseButtonUpEvent], None]) -> None:
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
        for event_type in tuple(
            event_type for event_type, priority_manager in self.__priority_manager.items() if priority_manager is manager
        ):
            self.__priority_manager.pop(event_type)

    def process_event(self, event: Event) -> bool:
        if isinstance(event, (KeyUpEvent, KeyDownEvent)):
            self.__handle_key_event(event)
        elif isinstance(event, (MouseButtonUpEvent, MouseButtonDownEvent)):
            self.__handle_mouse_event(event)

        priority_callback: _EventCallback | None = self.__priority_callback.get(type(event))
        if priority_callback is not None:
            if priority_callback(event):
                return True
            del self.__priority_callback[type(event)]

        priority_manager: EventManager | None = self.__priority_manager.get(type(event))
        if priority_manager is not None:
            if priority_manager.process_event(event):
                return True
            del self.__priority_manager[type(event)]

        event_dict: dict[type[Event], list[_EventCallback]] = self.__event_handler_dict
        for callback in event_dict.get(type(event), ()):
            if callback is not priority_callback and callback(event):
                self.__priority_callback[type(event)] = callback
                return True
        for manager in self.__other_manager_list:
            if manager is not priority_manager and manager.process_event(event):
                self.__priority_manager[type(event)] = manager
                return True
        return False

    def handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        for callback in self.__mouse_pos_handler_list:
            callback(mouse_pos)
        for manager in self.__other_manager_list:
            manager.handle_mouse_position(mouse_pos)

    def __handle_key_event(self, event: KeyEvent) -> None:
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
                callback(event)

    def __handle_mouse_event(self, event: MouseButtonEvent) -> None:
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
                callback(event)


_U = TypeVar("_U")
_V = TypeVar("_V")


class BoundEventManager(Generic[_T]):
    __slots__ = (
        "__ref",
        "__manager",
        "__weakref__",
    )

    def __init__(self, obj: _T) -> None:
        def unbind_all(selfref: weakref.ReferenceType[BoundEventManager[_T]] = weakref.ref(self)) -> None:
            self = selfref()
            if self is not None:
                self.__manager.unbind_all()

        self.__ref: weakref.ReferenceType[_T] = weakref.ref(obj, lambda _: unbind_all())
        self.__manager: EventManager = EventManager()

    def register_to_existing_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        return manager.bind_event_manager(self.__manager)

    def unregister_from_existing_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        return manager.unbind_event_manager(self.__manager)

    def __bind(
        self,
        manager_bind: Callable[[_U, Callable[[Event], _V]], None],
        key: _U,
        callback: weakref.WeakMethod[Callable[[_TE], _V]] | Callable[[_T, _TE], _V],
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):
            callback = self._get_method_func_from_weak_method(callback)

        method_callback = cast(Callable[[_T, Event], _V], callback)

        def event_callback(event: Event, /, selfref: weakref.ReferenceType[_T] = self.__ref) -> _V:
            self = selfref()
            if self is None:
                return None  # type: ignore[return-value]
            return method_callback(self, event)

        manager_bind(key, event_callback)

    @overload
    def bind(self, event_cls: type[_TE], callback: weakref.WeakMethod[Callable[[_TE], bool | None]]) -> None:
        ...

    @overload
    def bind(self, event_cls: type[_TE], callback: Callable[[_T, _TE], bool | None]) -> None:
        ...

    def bind(
        self,
        event_cls: type[_TE],
        callback: weakref.WeakMethod[Callable[[_TE], bool | None]] | Callable[[_T, _TE], bool | None],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind,
            key=event_cls,
            callback=callback,
        )

    @overload
    def bind_key(self, key: Keyboard.Key, callback: weakref.WeakMethod[Callable[[KeyEvent], None]]) -> None:
        ...

    @overload
    def bind_key(self, key: Keyboard.Key, callback: Callable[[_T, KeyEvent], None]) -> None:
        ...

    def bind_key(self, key: Keyboard.Key, callback: Any) -> None:
        self.bind_key_press(key, callback)
        self.bind_key_release(key, callback)

    @overload
    def bind_key_press(self, key: Keyboard.Key, callback: weakref.WeakMethod[Callable[[KeyDownEvent], None]]) -> None:
        ...

    @overload
    def bind_key_press(self, key: Keyboard.Key, callback: Callable[[_T, KeyDownEvent], None]) -> None:
        ...

    def bind_key_press(
        self,
        key: Keyboard.Key,
        callback: weakref.WeakMethod[Callable[[KeyDownEvent], None]] | Callable[[_T, KeyDownEvent], None],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_key_press,
            key=key,
            callback=callback,
        )

    @overload
    def bind_key_release(self, key: Keyboard.Key, callback: weakref.WeakMethod[Callable[[KeyUpEvent], None]]) -> None:
        ...

    @overload
    def bind_key_release(self, key: Keyboard.Key, callback: Callable[[_T, KeyUpEvent], None]) -> None:
        ...

    def bind_key_release(
        self,
        key: Keyboard.Key,
        callback: weakref.WeakMethod[Callable[[KeyUpEvent], None]] | Callable[[_T, KeyUpEvent], None],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_key_release,
            key=key,
            callback=callback,
        )

    @overload
    def bind_mouse_button(self, button: Mouse.Button, callback: weakref.WeakMethod[Callable[[MouseButtonEvent], None]]) -> None:
        ...

    @overload
    def bind_mouse_button(self, button: Mouse.Button, callback: Callable[[_T, MouseButtonEvent], None]) -> None:
        ...

    def bind_mouse_button(self, button: Mouse.Button, callback: Any) -> None:
        self.bind_mouse_button_press(button, callback)
        self.bind_mouse_button_release(button, callback)

    @overload
    def bind_mouse_button_press(
        self, button: Mouse.Button, callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], None]]
    ) -> None:
        ...

    @overload
    def bind_mouse_button_press(self, button: Mouse.Button, callback: Callable[[_T, MouseButtonDownEvent], None]) -> None:
        ...

    def bind_mouse_button_press(
        self,
        button: Mouse.Button,
        callback: weakref.WeakMethod[Callable[[MouseButtonDownEvent], None]] | Callable[[_T, MouseButtonDownEvent], None],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_mouse_button_press,
            key=button,
            callback=callback,
        )

    @overload
    def bind_mouse_button_release(
        self, button: Mouse.Button, callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], None]]
    ) -> None:
        ...

    @overload
    def bind_mouse_button_release(self, button: Mouse.Button, callback: Callable[[_T, MouseButtonUpEvent], None]) -> None:
        ...

    def bind_mouse_button_release(
        self,
        button: Mouse.Button,
        callback: weakref.WeakMethod[Callable[[MouseButtonUpEvent], None]] | Callable[[_T, MouseButtonUpEvent], None],
    ) -> None:
        return self.__bind(
            manager_bind=self.__manager.bind_mouse_button_release,
            key=button,
            callback=callback,
        )

    @overload
    def bind_mouse_position(self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], None]]) -> None:
        ...

    @overload
    def bind_mouse_position(self, callback: Callable[[_T, tuple[float, float]], None]) -> None:
        ...

    def bind_mouse_position(
        self, callback: weakref.WeakMethod[Callable[[tuple[float, float]], None]] | Callable[[_T, tuple[float, float]], None]
    ) -> None:
        if isinstance(callback, weakref.WeakMethod):
            callback = self._get_method_func_from_weak_method(callback)

        method_callback = cast(Callable[[_T, tuple[float, float]], None], callback)

        def mouse_position_callback(mouse_pos: tuple[float, float], /, selfref: weakref.ReferenceType[_T] = self.__ref) -> None:
            self = selfref()
            if self is None:
                return None
            return method_callback(self, mouse_pos)

        return self.__manager.bind_mouse_position(mouse_position_callback)

    def bind_event_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        if isinstance(manager, BoundEventManager):
            manager = manager.__manager
        return self.__manager.bind_event_manager(manager)

    def unbind_event_manager(self, manager: EventManager | BoundEventManager[Any]) -> None:
        if isinstance(manager, BoundEventManager):
            manager = manager.__manager
        return self.__manager.unbind_event_manager(manager)

    def process_event(self, event: Event) -> bool:
        return self.__manager.process_event(event)

    def handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        return self.__manager.handle_mouse_position(mouse_pos)

    def _get_method_func_from_weak_method(self, weak_method: weakref.WeakMethod[Any]) -> Callable[..., Any]:
        method = weak_method()
        if method is None:
            raise ReferenceError("Dead reference")
        if not hasattr(method, "__self__") or not hasattr(method, "__func__"):
            raise TypeError("Not a method-like object")
        if method.__self__ is not (obj := self.__self__):
            raise ValueError(f"{method.__self__!r} is not {obj!r}")
        callback: Callable[..., Any] = method.__func__
        del obj, method
        return callback

    @property
    def __self__(self) -> _T:
        return weakref_unwrap(self.__ref)


del _pg_constants, _BuiltinEventMeta
del _ASSOCIATIONS, _PYGAME_EVENT_TYPE, _BUILTIN_ASSOCIATIONS, _BUILTIN_PYGAME_EVENT_TYPE
