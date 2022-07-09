# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI system module"""

from __future__ import annotations

__all__ = [
    "BoundFocus",
    "FocusableContainer",
    "GUIScene",
    "NoFocusSupportError",
    "SupportsFocus",
]

import weakref
from abc import abstractmethod
from enum import auto, unique
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    ClassVar,
    Final,
    Iterator,
    Literal as L,
    Mapping,
    Protocol,
    Sequence,
    TypedDict,
    overload,
    runtime_checkable,
)

from ..graphics.theme import no_theme_decorator
from ..system.collections import OrderedWeakSet
from ..system.enum import AutoLowerNameEnum
from ..system.object import final
from ..system.utils.functools import setdefaultattr
from ..system.utils.weakref import weakref_unwrap
from .event import (
    Event,
    KeyDownEvent,
    KeyEvent,
    KeyUpEvent,
    MouseButtonDownEvent,
    MouseButtonUpEvent,
    MouseEvent,
    MouseMotionEvent,
    MouseWheelEvent,
)
from .keyboard import Keyboard
from .scene import Scene


class GUIScene(Scene):
    def __init__(self) -> None:
        super().__init__()
        self.__container: FocusableContainer = FocusableContainer(self)
        self.__focus_index: int = -1
        set_focus_mode_key: Callable[[KeyEvent], None] = lambda _: BoundFocus.set_mode(BoundFocus.Mode.KEY)
        set_focus_mode_mouse: Callable[[MouseEvent], None] = lambda _: BoundFocus.set_mode(BoundFocus.Mode.MOUSE)
        self.event.bind(KeyDownEvent, set_focus_mode_key)
        self.event.bind(KeyUpEvent, set_focus_mode_key)
        self.event.bind(MouseButtonDownEvent, set_focus_mode_mouse)
        self.event.bind(MouseButtonUpEvent, set_focus_mode_mouse)
        self.event.bind(MouseMotionEvent, set_focus_mode_mouse)
        self.event.bind(MouseWheelEvent, set_focus_mode_mouse)

    def update(self) -> None:
        super().update()
        self.__container.update()

    def handle_event(self, event: Event) -> bool:
        return (
            ((obj := self.focus_get()) is not None and obj._focus_handle_event(event))
            or super().handle_event(event)
            or (isinstance(event, KeyDownEvent) and self.__handle_key_event(event))  # Must be handled after event manager
        )

    @no_theme_decorator
    def focus_get(self) -> SupportsFocus | None:
        if not self.looping():
            return None
        focus_index: int = self.__focus_index
        try:
            focusable: SupportsFocus = self.__container[focus_index]
        except IndexError:
            self.__focus_index = -1
            return None
        if not focusable.focus.take():
            self.focus_next()
            return self.focus_get()
        return focusable

    @no_theme_decorator
    def get_next_focusable(self) -> SupportsFocus | None:
        return self.__internal_focus_next(offset=1)

    @no_theme_decorator
    def get_previous_focusable(self) -> SupportsFocus | None:
        return self.__internal_focus_next(offset=-1)

    @no_theme_decorator
    def __internal_focus_next(self, offset: L[1, -1]) -> SupportsFocus | None:
        if not self.looping():
            return None
        focusable_list: Sequence[SupportsFocus] = self.__container
        eligible_focusable_list = [obj for obj in focusable_list if obj.focus.take()]
        if eligible_focusable_list:
            if len(eligible_focusable_list) == 1:
                return eligible_focusable_list[0]
            focus_index: int = self.__focus_index
            if focus_index < 0:
                focus_index = -offset
            while (
                obj := focusable_list[(focus_index := (focus_index + offset) % len(focusable_list))]
            ) not in eligible_focusable_list:
                continue
            return obj
        self.__focus_index = -1
        return None

    @overload
    def focus_set(self, focusable: SupportsFocus) -> bool:
        ...

    @overload
    def focus_set(self, focusable: None) -> None:
        ...

    @no_theme_decorator
    def focus_set(self, focusable: SupportsFocus | None) -> bool | None:
        if not self.looping():
            return None if focusable is None else False
        focusable_list: Sequence[SupportsFocus] = self.__container
        focus_index: int = self.__focus_index
        if focusable is None:
            self.__focus_index = -1
            try:
                focusable = focusable_list[focus_index]
            except IndexError:
                pass
            else:
                self.__on_focus_leave(focusable)
            return None
        if focusable not in focusable_list or not focusable.focus.take():
            return False
        self.__focus_index = focusable_list.index(focusable)
        try:
            actual_focusable: SupportsFocus = focusable_list[focus_index]
        except IndexError:
            pass
        else:
            if actual_focusable is focusable:
                return True
            self.__on_focus_leave(actual_focusable)
        self.__on_focus_set(focusable)
        return True

    @final
    @no_theme_decorator
    def focus_next(self) -> None:
        self.focus_set(self.get_next_focusable())

    @final
    @no_theme_decorator
    def focus_prev(self) -> None:
        self.focus_set(self.get_previous_focusable())

    @no_theme_decorator
    def __on_focus_set(self, focusable: SupportsFocus) -> None:
        focusable._on_focus_set()
        callback: Callable[[], None]
        for callback in getattr(focusable, "_focus_set_callbacks_", ()):
            callback()

    @no_theme_decorator
    def __on_focus_leave(self, focusable: SupportsFocus) -> None:
        focusable._on_focus_leave()
        callback: Callable[[], None]
        for callback in getattr(focusable, "_focus_leave_callbacks_", ()):
            callback()

    @no_theme_decorator
    def get_side_with_key_event(self) -> Mapping[int, BoundFocus.Side]:
        return _SIDE_WITH_KEY_EVENT

    @no_theme_decorator
    def __handle_key_event(self, event: KeyDownEvent) -> bool:
        match event.key:
            case Keyboard.Key.TAB if event.mod & Keyboard.Modifiers.SHIFT:
                self.focus_prev()
            case Keyboard.Key.TAB:
                self.focus_next()
            case Keyboard.Key.ESCAPE:
                self.focus_set(None)
        side_with_key_event = self.get_side_with_key_event()
        if event.key in side_with_key_event:
            side: BoundFocus.Side = side_with_key_event[event.key]
            self.__focus_obj_on_side(side)
            return True
        return False

    @no_theme_decorator
    def __focus_obj_on_side(self, side: BoundFocus.Side) -> None:
        if not self.looping():
            return
        obj: SupportsFocus | None = self.focus_get()
        if obj is None:
            self.focus_next()
            return
        while ((obj := obj.focus.get_obj_on_side(side)) is not None) and not obj.focus.take():  # type: ignore[union-attr]
            continue
        if obj is not None:
            self.focus_set(obj)

    @property
    @final
    def _focus_container(self) -> FocusableContainer:
        return self.__container


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


class BoundFocus:
    @unique
    class Side(AutoLowerNameEnum):
        ON_TOP = auto()
        ON_BOTTOM = auto()
        ON_LEFT = auto()
        ON_RIGHT = auto()

    @unique
    class Mode(AutoLowerNameEnum):
        KEY = auto()
        MOUSE = auto()

    __mode: ClassVar[Mode] = Mode.MOUSE

    __slots__ = ("__f", "__scene")

    def __init__(self, focusable: SupportsFocus, scene: Scene | None) -> None:
        if not isinstance(focusable, _HasFocusMethods):
            raise NoFocusSupportError(repr(focusable))
        self.__f: weakref.ReferenceType[SupportsFocus] = weakref.ref(focusable)
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
        bound_object_dict: dict[BoundFocus.Side, SupportsFocus | None] = setdefaultattr(f, "_bound_focus_objects_", {})
        if __m is not None:
            kwargs = __m | kwargs
        del __m
        for side, obj in kwargs.items():
            side = BoundFocus.Side(side)
            if obj is not None and not isinstance(obj, SupportsFocus):
                raise TypeError(f"Expected None or SupportsFocus object, got {obj!r}")
            bound_object_dict[side] = obj

    def remove_obj_on_side(self, *sides: str) -> None:
        self.set_obj_on_side(dict.fromkeys(sides, None))

    def remove_all_links(self) -> None:
        self.remove_obj_on_side(*BoundFocus.Side)

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
        bound_object_dict: dict[BoundFocus.Side, SupportsFocus | None] = getattr(f, "_bound_focus_objects_", {})

        if side is None:
            return {
                "on_top": bound_object_dict.get(BoundFocus.Side.ON_TOP),
                "on_bottom": bound_object_dict.get(BoundFocus.Side.ON_BOTTOM),
                "on_left": bound_object_dict.get(BoundFocus.Side.ON_LEFT),
                "on_right": bound_object_dict.get(BoundFocus.Side.ON_RIGHT),
            }

        side = BoundFocus.Side(side)
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
    def get_mode(cls) -> Mode:
        return cls.__mode

    @classmethod
    def set_mode(cls, mode: Mode) -> None:
        cls.__mode = cls.Mode(mode)

    @property
    def __self__(self) -> SupportsFocus:
        return weakref_unwrap(self.__f)


_SIDE_WITH_KEY_EVENT: Final[MappingProxyType[int, BoundFocus.Side]] = MappingProxyType(
    {
        Keyboard.Key.LEFT: BoundFocus.Side.ON_LEFT,
        Keyboard.Key.RIGHT: BoundFocus.Side.ON_RIGHT,
        Keyboard.Key.UP: BoundFocus.Side.ON_TOP,
        Keyboard.Key.DOWN: BoundFocus.Side.ON_BOTTOM,
    }
)


class FocusableContainer(Sequence[SupportsFocus]):

    __slots__ = ("__master", "__list")

    def __init__(self, master: GUIScene) -> None:
        super().__init__()
        self.__master: weakref.ReferenceType[GUIScene] = weakref.ref(master)
        self.__list: OrderedWeakSet[SupportsFocus] = OrderedWeakSet()

    def __repr__(self) -> str:
        return self.__list.__repr__()

    def __len__(self) -> int:
        return self.__list.__len__()

    def __iter__(self) -> Iterator[SupportsFocus]:
        return self.__list.__iter__()

    def __reversed__(self) -> Iterator[SupportsFocus]:
        return self.__list.__reversed__()

    def __contains__(self, value: object) -> bool:
        return self.__list.__contains__(value)

    @overload
    def __getitem__(self, index: int, /) -> SupportsFocus:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[SupportsFocus]:
        ...

    def __getitem__(self, index: int | slice, /) -> SupportsFocus | Sequence[SupportsFocus]:
        if not isinstance(index, slice) and index < 0:
            raise IndexError("list index out of range")
        return self.__list[index]

    def add(self, focusable: SupportsFocus | BoundFocus) -> None:
        master: GUIScene = weakref_unwrap(self.__master)
        bound_focus: BoundFocus
        if isinstance(focusable, BoundFocus):
            bound_focus = focusable
            focusable = bound_focus.__self__
        else:
            if not isinstance(focusable, SupportsFocus):
                raise TypeError("'focusable' must be a SupportsFocus object")
            bound_focus = focusable.focus
        if not bound_focus.is_bound_to(master):
            raise ValueError("'focusable' is not bound to this scene")
        self.__list.add(focusable)

    def update(self) -> None:
        for f in self:
            f._focus_update()

    @overload
    def index(self, value: Any) -> int:
        ...

    @overload
    def index(self, value: Any, start: int = ..., stop: int = ...) -> int:
        ...

    def index(self, value: Any, *args: Any, **kwargs: Any) -> int:
        return self.__list.index(value, *args, **kwargs)

    def count(self, value: Any) -> int:
        return self.__list.count(value)
