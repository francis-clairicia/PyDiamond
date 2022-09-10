# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI system module"""

from __future__ import annotations

__all__ = [
    "BoundFocus",
    "BoundFocusMode",
    "BoundFocusSide",
    "NoFocusSupportError",
    "SupportsFocus",
]

import weakref
from abc import abstractmethod
from enum import auto, unique
from typing import Callable, ClassVar, Mapping, Protocol, TypedDict, overload, runtime_checkable

from ..system.enum import AutoLowerNameEnum
from ..system.utils.functools import setdefaultattr
from ..system.utils.weakref import weakref_unwrap
from ..window.event import Event
from ..window.scene import Scene


@runtime_checkable
class _HasFocusMethods(Protocol):
    @abstractmethod
    def is_shown(self) -> bool:
        raise NotImplementedError

    def _on_focus_set(self) -> None:
        pass

    def _on_focus_leave(self) -> None:
        pass

    def _focus_update(self) -> None:
        pass

    def _focus_handle_event(self, event: Event) -> bool | None:
        pass


@runtime_checkable
class SupportsFocus(_HasFocusMethods, Protocol):
    @property
    @abstractmethod
    def focus(self) -> BoundFocus:
        raise NoFocusSupportError


class NoFocusSupportError(AttributeError):
    pass


@unique
class BoundFocusSide(AutoLowerNameEnum):
    ON_TOP = auto()
    ON_BOTTOM = auto()
    ON_LEFT = auto()
    ON_RIGHT = auto()


@unique
class BoundFocusMode(AutoLowerNameEnum):
    KEY = auto()
    MOUSE = auto()


class BoundFocus:
    __mode: ClassVar[BoundFocusMode] = BoundFocusMode.MOUSE

    __slots__ = ("__f", "__scene")

    def __init__(self, focusable: SupportsFocus, scene: Scene | None) -> None:
        if not isinstance(focusable, _HasFocusMethods):
            raise NoFocusSupportError(repr(focusable))
        self.__f: weakref.ref[SupportsFocus] = weakref.ref(focusable)
        if scene is not None and not isinstance(scene, Scene):
            raise TypeError(f"Must be a Scene or None, got {scene.__class__.__name__!r}")
        scene = scene if isinstance(scene, GUIScene) else None
        self.__scene: GUIScene | None = scene
        if scene is not None:
            scene._focus_container.add(self)

    def is_bound_to(self, scene: GUIScene) -> bool:
        return (bound_scene := self.__scene) is not None and bound_scene is scene

    def get(self) -> SupportsFocus | None:
        return scene.focus_get() if (scene := self.__scene) else None

    def has(self) -> bool:
        return self.get() is self.__self__

    @overload
    def take(self, status: bool) -> None:
        ...

    @overload
    def take(self) -> bool:
        ...

    def take(self, status: bool | None = None) -> bool | None:
        f: SupportsFocus = self.__self__
        scene: GUIScene | None = self.__scene
        if status is not None:
            status = bool(status)
            setattr(f, "_take_focus_", status)
            if scene is not None:
                scene.focus_get()  # Force update
            return None
        if scene is None or not f.is_shown():
            return False
        return bool(getattr(f, "_take_focus_", False))

    def set(self) -> bool:
        return scene.focus_set(self.__self__) if (scene := self.__scene) else False

    def leave(self) -> None:
        if (scene := self.__scene) is not None and self.has():
            scene.focus_set(None)

    @overload
    def set_obj_on_side(
        self,
        /,
        *,
        on_top: SupportsFocus | None = ...,
        on_bottom: SupportsFocus | None = ...,
        on_left: SupportsFocus | None = ...,
        on_right: SupportsFocus | None = ...,
    ) -> None:
        ...

    @overload
    def set_obj_on_side(self, __m: Mapping[str, SupportsFocus | None], /) -> None:
        ...

    def set_obj_on_side(
        self,
        __m: Mapping[str, SupportsFocus | None] | None = None,
        /,
        **kwargs: SupportsFocus | None,
    ) -> None:
        if __m is None and not kwargs:
            raise TypeError("Invalid arguments")

        f: SupportsFocus = self.__self__
        bound_object_dict: dict[BoundFocusSide, SupportsFocus | None] = setdefaultattr(f, "_bound_focus_objects_", {})
        if __m is not None:
            kwargs = __m | kwargs
        del __m
        for side, obj in kwargs.items():
            side = BoundFocusSide(side)
            if obj is not None and not isinstance(obj, SupportsFocus):
                raise TypeError(f"Expected None or SupportsFocus object, got {obj!r}")
            bound_object_dict[side] = obj

    def remove_obj_on_side(self, *sides: str) -> None:
        self.set_obj_on_side(dict.fromkeys(sides, None))

    def remove_all_links(self) -> None:
        self.remove_obj_on_side(*BoundFocusSide)

    class BoundObjectsDict(TypedDict):
        on_top: SupportsFocus | None
        on_bottom: SupportsFocus | None
        on_left: SupportsFocus | None
        on_right: SupportsFocus | None

    @overload
    def get_obj_on_side(self) -> BoundObjectsDict:
        ...

    @overload
    def get_obj_on_side(self, side: str) -> SupportsFocus | None:
        ...

    def get_obj_on_side(self, side: str | None = None) -> BoundObjectsDict | SupportsFocus | None:
        f: SupportsFocus = self.__self__
        bound_object_dict: dict[BoundFocusSide, SupportsFocus | None] = getattr(f, "_bound_focus_objects_", {})

        if side is None:
            return {
                "on_top": bound_object_dict.get(BoundFocusSide.ON_TOP),
                "on_bottom": bound_object_dict.get(BoundFocusSide.ON_BOTTOM),
                "on_left": bound_object_dict.get(BoundFocusSide.ON_LEFT),
                "on_right": bound_object_dict.get(BoundFocusSide.ON_RIGHT),
            }

        side = BoundFocusSide(side)
        return bound_object_dict.get(side)

    def left_to(self, right: SupportsFocus, *, bind_other: bool = True) -> None:
        if bind_other:
            right.focus.set_obj_on_side(on_left=self.__self__)
        self.set_obj_on_side(on_right=right)

    def right_to(self, left: SupportsFocus, *, bind_other: bool = True) -> None:
        if bind_other:
            left.focus.set_obj_on_side(on_right=self.__self__)
        self.set_obj_on_side(on_left=left)

    def above(self, bottom: SupportsFocus, *, bind_other: bool = True) -> None:
        if bind_other:
            bottom.focus.set_obj_on_side(on_top=self.__self__)
        self.set_obj_on_side(on_bottom=bottom)

    def below(self, top: SupportsFocus, *, bind_other: bool = True) -> None:
        if bind_other:
            top.focus.set_obj_on_side(on_bottom=self.__self__)
        self.set_obj_on_side(on_top=top)

    def register_focus_set_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: list[Callable[[], None]] = setdefaultattr(f, "_focus_set_callbacks_", [])
        if callback not in list_callback:
            list_callback.append(callback)

    def unregister_focus_set_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: list[Callable[[], None]] = setdefaultattr(f, "_focus_set_callbacks_", [])
        list_callback.remove(callback)

    def register_focus_leave_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: list[Callable[[], None]] = setdefaultattr(f, "_focus_leave_callbacks_", [])
        if callback not in list_callback:
            list_callback.append(callback)

    def unregister_focus_leave_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: list[Callable[[], None]] = setdefaultattr(f, "_focus_leave_callbacks_", [])
        list_callback.remove(callback)

    @classmethod
    def get_mode(cls) -> BoundFocusMode:
        return cls.__mode

    @classmethod
    def set_mode(cls, mode: BoundFocusMode) -> None:
        cls.__mode = BoundFocusMode(mode)

    @property
    def __self__(self) -> SupportsFocus:
        return weakref_unwrap(self.__f)


from .scene import GUIScene  # Import at last because of circular import
