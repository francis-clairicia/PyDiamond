# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Controller module

** EXPERIMENTAL API **
Since pygame does not have a stable API for SDL controllers for now, this implementation might be changed in further releases.
"""

from __future__ import annotations

__all__ = ["Controller"]

from collections.abc import Iterable, Iterator, MutableMapping
from enum import IntEnum, auto, unique
from threading import RLock
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final, Literal, NoReturn, assert_never, final, overload

import pygame._sdl2.controller as _pg_controller
import pygame.constants as _pg_constants
import pygame.joystick as _pg_joystick
from pygame import error as _pg_error

from ..system.object import Object

if TYPE_CHECKING:
    from _typeshed import SupportsKeysAndGetItem


@unique
class ControllerButton(IntEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        constant_name = f"CONTROLLER_BUTTON_{name.removeprefix('BUTTON_')}"
        return getattr(_pg_constants, constant_name)

    BUTTON_A = auto()
    BUTTON_B = auto()
    BUTTON_X = auto()
    BUTTON_Y = auto()
    BUTTON_BACK = auto()
    BUTTON_GUIDE = auto()
    BUTTON_START = auto()
    BUTTON_LEFTSTICK = auto()
    BUTTON_RIGHTSTICK = auto()
    BUTTON_LEFTSHOULDER = auto()
    BUTTON_RIGHTSHOULDER = auto()
    DPAD_UP = auto()
    DPAD_DOWN = auto()
    DPAD_LEFT = auto()
    DPAD_RIGHT = auto()


@unique
class ControllerAxis(IntEnum):
    @staticmethod
    def _generate_next_value_(name: str, start: int, count: int, last_values: list[int]) -> int:
        constant_name = f"CONTROLLER_AXIS_{name.replace('_', '')}"
        return getattr(_pg_constants, constant_name)

    LEFT_X = auto()
    LEFT_Y = auto()
    RIGHT_X = auto()
    RIGHT_Y = auto()
    TRIGGERLEFT = auto()
    TRIGGERRIGHT = auto()


def get_count() -> int:
    return _pg_controller.get_count()


def get_all_controllers() -> list[Controller]:
    return [Controller(idx) for idx in range(_pg_controller.get_count()) if _pg_controller.is_controller(idx)]


def is_controller(index: int) -> bool:
    return _pg_controller.is_controller(index)


def name_forindex(index: int) -> str | None:
    return _pg_controller.name_forindex(index)


@final
class ControllerMapping(MutableMapping[str, str]):
    def __init__(self, controller: _pg_controller.Controller) -> None:
        super().__init__()
        assert isinstance(controller, _pg_controller.Controller)
        self.__controller: _pg_controller.Controller = controller

    def __repr__(self) -> str:
        return repr(self.__controller.get_mapping())

    def __str__(self) -> str:
        controller = self.__controller
        name: str = controller.name
        guid: str = controller.as_joystick().get_guid()
        mapping = controller.get_mapping()
        return f"{name},{guid},{','.join(f'{k}:{v}' for k, v in mapping.items())}"

    def __iter__(self) -> Iterator[str]:
        mapping = self.__controller.get_mapping()
        return iter(mapping)

    def __len__(self) -> int:
        mapping = self.__controller.get_mapping()
        return len(mapping)

    def __getitem__(self, key: str, /) -> str:
        mapping = self.__controller.get_mapping()
        return mapping[key]

    def __setitem__(self, key: str, value: str, /) -> None:
        mapping = self.__controller.get_mapping()
        mapping[key] = value
        self.__controller.set_mapping(mapping)

    def __delitem__(self, __key: str, /) -> NoReturn:
        raise KeyError("Cannot be deleted")

    def clear(self) -> NoReturn:
        raise TypeError("ControllerMapping cannot be cleared")

    def pop(self, key: str, /, default: Any = ...) -> NoReturn:
        raise KeyError("Cannot be deleted")

    def popitem(self) -> NoReturn:
        raise KeyError("Cannot be deleted")

    @overload
    def update(self, __m: SupportsKeysAndGetItem[str, str], /, **kwargs: str) -> None: ...

    @overload
    def update(self, __m: Iterable[tuple[str, str]], /, **kwargs: str) -> None: ...

    @overload
    def update(self, /, **kwargs: str) -> None: ...

    def update(self, other: Any = (), /, **kwargs: Any) -> None:
        mapping = self.__controller.get_mapping()
        mapping.update(other, **kwargs)
        self.__controller.set_mapping(mapping)

    def update_from_string(self, string: str) -> None:
        parts = string.split(",")
        if len(parts) <= 2:
            raise ValueError("Invalid mapping string")
        controller = self.__controller
        joystick = controller.as_joystick()
        actual_mapping = controller.get_mapping()
        guid, _, *parts = parts
        if guid != joystick.get_guid():
            raise ValueError("GUIDs do not match")
        new_mapping = dict(part.split(":") for part in parts)

        # Special case: 'platform' is an optional field
        _PLATFORM_KEY = "platform"
        if _PLATFORM_KEY not in new_mapping and _PLATFORM_KEY in actual_mapping:
            new_mapping[_PLATFORM_KEY] = actual_mapping[_PLATFORM_KEY]
        elif _PLATFORM_KEY in new_mapping and _PLATFORM_KEY not in actual_mapping:
            actual_mapping[_PLATFORM_KEY] = new_mapping[_PLATFORM_KEY]

        if sorted(new_mapping) != sorted(actual_mapping):
            raise ValueError("Invalid mapping string")
        controller.set_mapping(new_mapping)


@final
class Controller(Object):
    __slots__ = ("__c", "__id", "__h", "__weakref__")

    __instances: Final[dict[int, Controller]] = {}
    __instances_lock: RLock = RLock()

    _ALL_CONTROLLERS: MappingProxyType[int, Controller] = MappingProxyType(__instances)

    def __new__(cls, device_index: int) -> Controller:
        joystick = _pg_joystick.Joystick(device_index)
        instance_id = joystick.get_instance_id()
        with cls.__instances_lock:
            try:
                self = cls.__instances[instance_id]
            except KeyError:
                self = super().__new__(cls)
                cls.__instances[instance_id] = self
                try:
                    self.__internal_init(joystick)
                except _pg_error:
                    cls.__instances.pop(instance_id, None)
                    raise
            else:
                self.__internal_init(joystick)
            return self

    @classmethod
    def from_instance_id(cls, instance_id: int) -> Controller:
        with cls.__instances_lock:
            try:
                self = cls.__instances[instance_id]
            except KeyError:
                joystick: _pg_joystick.JoystickType | None = (
                    next(
                        (
                            joy
                            for joy in map(_pg_joystick.Joystick, range(_pg_joystick.get_count()))
                            if joy.get_instance_id() == instance_id
                        ),
                        None,
                    )
                    if instance_id >= 0
                    else None
                )
                if joystick is None:
                    raise _pg_error("Invalid joystick instance id")
                self = super().__new__(cls)
                self.__internal_init(joystick)
                cls.__instances[instance_id] = self
            else:
                try:
                    self.__check_valid_controller()
                except _pg_error:
                    raise _pg_error("Invalid joystick instance id") from None
            return self

    def __internal_init(self, joystick: _pg_joystick.JoystickType) -> None:
        controller = _pg_controller.Controller.from_joystick(joystick)
        self.__c: _pg_controller.Controller | None = controller
        self.__id: int = joystick.get_instance_id()
        self.__h: int = hash((type(self), self.__c))

    def __repr__(self) -> str:
        with self.__instances_lock:
            if not self.attached():
                return f"<{type(self).__name__} closed>"

            name: str = self.name
            instance_id: int = self.instance_id
            guid: str = self.guid

            return f"<{type(self).__name__} name={name!r} instance_id={instance_id} guid={guid!r}>"

    def quit(self) -> None:
        with self.__instances_lock:
            self.__instances.pop(self.__id, None)
            controller: _pg_controller.Controller | None = self.__c
            self.__c = None
            if controller is not None:
                try:
                    controller.quit()
                except _pg_error:
                    pass

    def attached(self) -> bool:
        try:
            controller: _pg_controller.Controller = self.__check_valid_controller()
        except _pg_error:
            return False
        return controller.attached()

    def get_button(self, button: int) -> bool:
        button = ControllerButton(button)
        controller: _pg_controller.Controller = self.__check_valid_controller()
        return controller.get_button(button)

    def get_axis(self, axis: int, how: Literal["value", "percent"] = "value") -> float:
        axis = ControllerAxis(axis)
        controller: _pg_controller.Controller = self.__check_valid_controller()
        match how:
            case "value":
                return controller.get_axis(axis)
            case "percent":
                value: int = controller.get_axis(axis)
                return value / (32768 - (value >= 0))
            case _:
                assert_never(how)

    def rumble(self, low_frequency: float, high_frequency: float, duration: int) -> bool:
        controller: _pg_controller.Controller = self.__check_valid_controller()
        return controller.rumble(low_frequency, high_frequency, duration)

    def stop_rumble(self) -> None:
        controller: _pg_controller.Controller = self.__check_valid_controller()
        controller.stop_rumble()

    def __eq__(self, other: object, /) -> bool:
        if not isinstance(other, Controller):
            return NotImplemented
        if self.__c is None or other.__c is None:
            return False
        return other.__c == self.__c

    def __ne__(self, other: object, /) -> bool:
        return not (self == other)

    def __hash__(self) -> int:
        return self.__h

    def __check_valid_controller(self) -> _pg_controller.Controller:
        instance_id: int = self.__id
        controller: _pg_controller.Controller | None = self.__c
        if controller is None or not controller.get_init():
            raise _pg_error("Controller closed")
        with self.__instances_lock:
            if instance_id != controller.as_joystick().get_instance_id():  # Object reused for another joystick
                self.__c = None
                self.__instances.pop(instance_id, None)
                raise _pg_error("Controller closed")
        return controller

    @property
    def name(self) -> str:
        try:
            controller: _pg_controller.Controller = self.__check_valid_controller()
        except _pg_error:
            return ""
        return controller.name

    @property
    def guid(self) -> str:
        try:
            controller: _pg_controller.Controller = self.__check_valid_controller()
        except _pg_error:
            return ""
        return controller.as_joystick().get_guid()

    @property
    def device_index(self) -> int:
        try:
            controller: _pg_controller.Controller = self.__check_valid_controller()
        except _pg_error:
            return -1
        return controller.id

    @property
    def instance_id(self) -> int:
        return self.__id

    @property
    def mapping(self) -> ControllerMapping:
        controller: _pg_controller.Controller = self.__check_valid_controller()
        return ControllerMapping(controller)
