# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI system module"""

from __future__ import annotations

__all__ = [
    "BoundFocus",
    "BoundFocusSide",
    "NoFocusSupportError",
    "SupportsFocus",
    "supports_focus",
]

from abc import abstractmethod
from enum import auto, unique
from typing import Any, Callable, Final, Iterator, Literal, Mapping, Protocol, TypedDict, TypeGuard, overload, runtime_checkable
from weakref import WeakSet, WeakValueDictionary, ref as weakref

from ..scene.abc import Scene
from ..system.collections import WeakKeyDefaultDictionary
from ..system.utils.enum import AutoLowerNameEnum
from ..system.utils.weakref import weakref_unwrap
from ..window.event import Event


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

    def _focus_handle_event(self, event: Event) -> bool:
        pass


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


class BoundObjectsDict(TypedDict):
    on_top: SupportsFocus | None
    on_bottom: SupportsFocus | None
    on_left: SupportsFocus | None
    on_right: SupportsFocus | None


# TODO: Generic[_T]
class BoundFocus:
    __slots__ = ("__f", "__scene", "__weakref__")

    __enabled: Final[WeakSet[SupportsFocus]] = WeakSet()
    __never_take_focus: Final[WeakSet[SupportsFocus]] = WeakSet()
    __register: Final[WeakSet[BoundFocus]] = WeakSet()

    # fmt: off
    __side: Final[WeakKeyDefaultDictionary[SupportsFocus, WeakValueDictionary[BoundFocusSide, SupportsFocus]]] = WeakKeyDefaultDictionary(WeakValueDictionary)
    __focus_set_callback: Final[WeakKeyDefaultDictionary[SupportsFocus, set[Callable[[], None]]]] = WeakKeyDefaultDictionary(set)
    __focus_leave_callback: Final[WeakKeyDefaultDictionary[SupportsFocus, set[Callable[[], None]]]] = WeakKeyDefaultDictionary(set)
    # fmt: on

    def __init__(self, focusable: SupportsFocus, scene: Scene | None | Literal[False]) -> None:
        if not isinstance(focusable, _HasFocusMethods):
            raise NoFocusSupportError(focusable)
        self.__f: weakref[SupportsFocus]
        self.__scene: Callable[[], GUIScene | None]
        if any(bound_focus.__f() is focusable for bound_focus in self.__register):
            raise ValueError("There is already a BoundFocus instance for this object")
        self.__f = focusable_ref = weakref(focusable)
        if scene is not None and scene is not False and not isinstance(scene, Scene):
            raise TypeError(f"Must be a Scene or None, got {scene.__class__.__name__!r}")
        if isinstance(scene, GUIScene):

            def disable(_: Any) -> None:
                focusable: SupportsFocus | None = focusable_ref()
                if focusable is not None:
                    BoundFocus.__enabled.discard(focusable)

            self.__scene = weakref(scene, disable)
            scene._focus_container.add(self)
            self.__enabled.add(focusable)
        else:
            if scene is False:
                self.__never_take_focus.add(focusable)
            self.__scene = lambda: None
        self.__register.add(self)

    def is_bound_to(self, scene: GUIScene) -> bool:
        return (bound_scene := self.__scene()) is not None and bound_scene is scene

    def has(self) -> bool:
        return (scene.focus_get() if (scene := self.__scene()) else None) is self.__self__

    @overload
    def take(self, status: bool) -> None:
        ...

    @overload
    def take(self) -> bool:
        ...

    def take(self, status: bool | None = None) -> bool | None:
        f: SupportsFocus = self.__self__
        scene: GUIScene | None = self.__scene()
        if status is not None:
            if f in self.__never_take_focus:
                raise TypeError("Cannot take focus: Not bound to a GUIScene")
            if status:
                self.__enabled.add(f)
            else:
                self.__enabled.discard(f)
            if scene is not None:
                scene.focus_get()  # Force update
            return None
        if scene is None or not f.is_shown() or f in self.__never_take_focus:
            return False
        return f in self.__enabled

    def set(self) -> bool:
        return scene.focus_set(self.__self__) if (scene := self.__scene()) else False

    def leave(self) -> None:
        if (scene := self.__scene()) is not None and self.has():
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
        if (__m is None and not kwargs) or (__m is not None and kwargs):
            raise TypeError("Invalid arguments")

        f: SupportsFocus = self.__self__
        bound_object_dict: WeakValueDictionary[BoundFocusSide, SupportsFocus] = self.__side[f]
        if __m is not None:
            kwargs = __m | kwargs
        del __m
        for side, obj in kwargs.items():
            side = BoundFocusSide(side)
            if obj is None:
                bound_object_dict.pop(side, None)
                continue
            if not supports_focus(obj):
                raise TypeError(f"Expected None or SupportsFocus object, got {obj!r}")
            bound_object_dict[side] = obj

    def remove_obj_on_side(self, *sides: str) -> None:
        sides_set = set(map(BoundFocusSide, sides))
        del sides
        f: SupportsFocus = self.__self__
        bound_object_dict: WeakValueDictionary[BoundFocusSide, SupportsFocus]
        try:
            bound_object_dict = self.__side[f]
        except KeyError:
            return
        for side in sides_set:
            bound_object_dict.pop(side, None)

    def remove_all_links(self) -> None:
        f: SupportsFocus = self.__self__
        self.__side.pop(f, None)

    @overload
    def get_obj_on_side(self) -> BoundObjectsDict:
        ...

    @overload
    def get_obj_on_side(self, side: str) -> SupportsFocus | None:
        ...

    def get_obj_on_side(self, side: str | None = None) -> BoundObjectsDict | SupportsFocus | None:
        f: SupportsFocus = self.__self__
        bound_object_dict: Mapping[BoundFocusSide, SupportsFocus] = self.__side.get(f, {})

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
        list_callback: set[Callable[[], None]] = self.__focus_set_callback[f]
        list_callback.add(callback)

    def unregister_focus_set_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: set[Callable[[], None]] = self.__focus_set_callback[f]
        list_callback.remove(callback)

    def iter_focus_set_callbacks(self) -> Iterator[Callable[[], None]]:
        return iter(self.__focus_set_callback.get(self.__self__, ()))

    def register_focus_leave_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: set[Callable[[], None]] = self.__focus_leave_callback[f]
        list_callback.add(callback)

    def unregister_focus_leave_callback(self, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__self__
        list_callback: set[Callable[[], None]] = self.__focus_leave_callback[f]
        list_callback.remove(callback)

    def iter_focus_leave_callbacks(self) -> Iterator[Callable[[], None]]:
        return iter(self.__focus_leave_callback.get(self.__self__, ()))

    def get_mode(self) -> FocusMode:
        return scene.focus_mode() if (scene := self.__scene()) else FocusMode.NONE

    @property
    def __self__(self) -> SupportsFocus:
        return weakref_unwrap(self.__f)


def supports_focus(obj: Any) -> TypeGuard[SupportsFocus]:
    if not isinstance(obj, _HasFocusMethods):
        return False
    try:
        focus: Any = getattr(obj, "focus")
    except AttributeError:
        return False
    if not isinstance(focus, BoundFocus):
        return False
    try:
        return focus.__self__ is obj
    except ReferenceError:
        return False


from .scene import FocusMode, GUIScene  # Import at last because of circular import
