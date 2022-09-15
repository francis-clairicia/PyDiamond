# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI scene module"""

from __future__ import annotations

__all__ = [
    "FocusableContainer",
    "GUIScene",
]

import weakref
from types import MappingProxyType
from typing import Any, Callable, Final, Iterator, Literal, Mapping, Sequence, overload

from ..system.collections import OrderedWeakSet
from ..system.object import final
from ..system.theme import no_theme_decorator
from ..system.utils.weakref import weakref_unwrap
from ..window.event import (
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
from ..window.keyboard import Key, KeyModifiers
from ..window.scene import Scene


class GUIScene(Scene):
    def __init__(self) -> None:
        super().__init__()
        self.__container: FocusableContainer = FocusableContainer(self)
        self.__focus_index: int = -1
        set_focus_mode_key: Callable[[KeyEvent], None] = lambda _: BoundFocus.set_mode(BoundFocusMode.KEY)
        set_focus_mode_mouse: Callable[[MouseEvent], None] = lambda _: BoundFocus.set_mode(BoundFocusMode.MOUSE)
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
    def __internal_focus_next(self, offset: Literal[1, -1]) -> SupportsFocus | None:
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
    def get_side_with_key_event(self) -> Mapping[int, BoundFocusSide]:
        return _SIDE_WITH_KEY_EVENT

    @no_theme_decorator
    def __handle_key_event(self, event: KeyDownEvent) -> bool:
        match event.key:
            case Key.K_TAB if event.mod & KeyModifiers.KMOD_SHIFT:
                self.focus_prev()
                return True
            case Key.K_TAB:
                self.focus_next()
                return True
            case Key.K_ESCAPE:
                self.focus_set(None)
                return True
        side_with_key_event = self.get_side_with_key_event()
        if event.key in side_with_key_event:
            side: BoundFocusSide = side_with_key_event[event.key]
            self.__focus_obj_on_side(side)
            return True
        return False

    @no_theme_decorator
    def __focus_obj_on_side(self, side: BoundFocusSide) -> None:
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


from .focus import BoundFocus, BoundFocusMode, BoundFocusSide, SupportsFocus  # Import here because of circular import

_SIDE_WITH_KEY_EVENT: Final[MappingProxyType[int, BoundFocusSide]] = MappingProxyType(
    {
        Key.K_LEFT: BoundFocusSide.ON_LEFT,
        Key.K_RIGHT: BoundFocusSide.ON_RIGHT,
        Key.K_UP: BoundFocusSide.ON_TOP,
        Key.K_DOWN: BoundFocusSide.ON_BOTTOM,
    }
)


class FocusableContainer(Sequence[SupportsFocus]):

    __slots__ = ("__master", "__list")

    def __init__(self, master: GUIScene) -> None:
        super().__init__()
        self.__master: weakref.ref[GUIScene] = weakref.ref(master)
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
