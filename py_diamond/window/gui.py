# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI system module"""

from __future__ import annotations

__all__ = [
    "BoundFocus",
    "BoundFocusProxy",
    "FocusableContainer",
    "GUIScene",
    "NoFocusSupportError",
    "SupportsFocus",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import weakref
from abc import abstractmethod
from enum import auto, unique
from operator import truth
from types import FunctionType, LambdaType
from typing import (
    Any,
    Callable,
    ClassVar,
    Final,
    Literal,
    Mapping,
    Protocol,
    Sequence,
    TypedDict,
    final,
    overload,
    runtime_checkable,
)

from ..graphics.drawable import Drawable, LayeredDrawableGroup
from ..graphics.renderer import AbstractRenderer
from ..graphics.theme import no_theme_decorator
from ..system._mangling import getattr_pv
from ..system.enum import AutoLowerNameEnum
from ..system.utils import setdefaultattr, wraps
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
from .scene import AbstractLayeredScene, Scene


class GUIScene(AbstractLayeredScene):
    def __init__(self) -> None:
        super().__init__()
        self.__container: FocusableContainer = FocusableContainer(self)
        self.__group: _GUILayeredGroup = _GUILayeredGroup(self)
        self.__focus_index: int = -1
        handle_key_event = self.__handle_key_event
        set_focus_mode_key: Callable[[KeyEvent], None] = lambda event: BoundFocus.set_mode(BoundFocus.Mode.KEY)
        set_focus_mode_mouse: Callable[[MouseEvent], None] = lambda event: BoundFocus.set_mode(BoundFocus.Mode.MOUSE)
        self.event.bind(KeyDownEvent, set_focus_mode_key)
        self.event.bind(KeyUpEvent, set_focus_mode_key)
        self.event.bind(MouseButtonDownEvent, set_focus_mode_mouse)
        self.event.bind(MouseButtonUpEvent, set_focus_mode_mouse)
        self.event.bind(MouseMotionEvent, set_focus_mode_mouse)
        self.event.bind(MouseWheelEvent, set_focus_mode_mouse)
        self.event.bind_key_press(Keyboard.Key.TAB, handle_key_event)
        self.event.bind_key_press(Keyboard.Key.ESCAPE, handle_key_event)

    def handle_event(self, event: Event) -> bool:
        return (
            ((obj := self.focus_get()) is not None and obj._focus_handle_event(event))
            or super().handle_event(event)
            or (isinstance(event, KeyDownEvent) and self.__handle_key_event(event))
        )

    @no_theme_decorator
    def focus_get(self) -> SupportsFocus | None:
        if not self.looping():
            return None
        focus_index: int = self.__focus_index
        if focus_index < 0:
            return None
        focusable = next((f for idx, f in enumerate(self.__container) if idx == focus_index), None)
        if focusable is None:
            self.__focus_index = -1
            return None
        if not focusable.focus.take():
            self.focus_set(self.focus_next())
            return self.focus_get()
        return focusable

    @no_theme_decorator
    def focus_next(self) -> SupportsFocus | None:
        return self.__internal_focus_next(offset=1)

    @no_theme_decorator
    def focus_prev(self) -> SupportsFocus | None:
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
            size = len(focusable_list)
            while (obj := focusable_list[(focus_index := (focus_index + offset) % size)]) not in eligible_focusable_list:
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
            if focus_index >= 0:
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
        if focus_index >= 0:
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
    def __handle_key_event(self, event: KeyDownEvent) -> bool:
        if event.key == Keyboard.Key.TAB:
            self.focus_set(self.focus_next() if not event.mod & Keyboard.Modifiers.SHIFT else self.focus_prev())
            return True
        if event.key == Keyboard.Key.ESCAPE:
            self.focus_set(None)
            return True
        if event.key in _SIDE_WITH_KEY_EVENT:
            side: BoundFocus.Side = _SIDE_WITH_KEY_EVENT[event.key]
            self.__focus_obj_on_side(side)
            return True
        return False

    @no_theme_decorator
    def __focus_obj_on_side(self, side: BoundFocus.Side) -> None:
        if not self.looping():
            return
        obj: SupportsFocus | None = self.focus_get()
        if obj is None:
            self.focus_set(self.focus_next())
            return
        while (obj := obj.focus.get_obj_on_side(side)) is not None and not obj.focus.take():  # type: ignore[union-attr]
            continue
        if obj is not None:
            self.focus_set(obj)

    @property
    @final
    def group(self) -> LayeredDrawableGroup:
        return self.__group

    @property
    def _focus_container(self) -> FocusableContainer:
        return self.__container


@runtime_checkable
class _HasFocusMethods(Protocol):
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
        self.__scene: GUIScene | None = scene if isinstance(scene, GUIScene) else None

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
        if scene is None:
            return False
        taken: bool = truth(getattr(f, "_take_focus_", False))
        if isinstance(f, Drawable):
            taken = taken and f.is_shown()
        return taken

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
        f: SupportsFocus | None = self.__f()
        if f is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        return f


class _BoundFocusProxyMeta(type):
    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _BoundFocusProxyMeta:
        if "BoundFocusProxy" in globals() and not any(issubclass(cls, BoundFocusProxy) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {BoundFocusProxy.__name__} class in order to use {_BoundFocusProxyMeta.__name__} metaclass"
            )

        if "BoundFocusProxy" not in globals() and name == "BoundFocusProxy":
            FOCUS_OBJ_ATTR = f"_{name}__focus"

            def get_underlying_object(self: BoundFocusProxy) -> BoundFocus:
                return self.__getattribute__(FOCUS_OBJ_ATTR)  # type: ignore[no-any-return]

            def proxy_method_wrapper(method_name: str, func: Callable[..., Any]) -> Callable[..., Any]:
                @wraps(func)
                def wrapper(self: BoundFocusProxy, /, *args: Any, **kwargs: Any) -> Any:
                    focus: BoundFocus = get_underlying_object(self)
                    method: Callable[..., Any] = getattr(focus, method_name)
                    return method(*args, **kwargs)

                return wrapper

            def proxy_property_wrapper(name: str, obj: property) -> property:
                if callable(obj.fget):

                    @wraps(obj.fget)
                    def getter(self: BoundFocusProxy, /) -> Any:
                        focus: BoundFocus = get_underlying_object(self)
                        return getattr(focus, name)

                    obj = obj.getter(getter)

                if callable(obj.fset):

                    @wraps(obj.fset)
                    def setter(self: BoundFocusProxy, value: Any, /) -> None:
                        focus: BoundFocus = get_underlying_object(self)
                        return setattr(focus, name, value)

                    obj = obj.setter(setter)

                if callable(obj.fdel):

                    @wraps(obj.fdel)
                    def deleter(self: BoundFocusProxy, /) -> None:
                        focus: BoundFocus = get_underlying_object(self)
                        return delattr(focus, name)

                    obj = obj.deleter(deleter)

                return obj

            for attr_name, attr_obj in vars(BoundFocus).items():
                if isinstance(attr_obj, property):
                    namespace[attr_name] = proxy_property_wrapper(attr_name, attr_obj)
                elif isinstance(attr_obj, (FunctionType, LambdaType)):
                    namespace[attr_name] = proxy_method_wrapper(attr_name, attr_obj)

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class BoundFocusProxy(BoundFocus, metaclass=_BoundFocusProxyMeta):

    __slots__ = ("__focus",)

    def __init__(self, focus: BoundFocus) -> None:
        super().__init__(focus.__self__, getattr_pv(focus, "scene", None, owner=BoundFocus))
        self.__focus: BoundFocus = focus

    def __getattr__(self, name: str, /) -> Any:
        return self.__focus.__getattribute__(name)

    def __setattr__(self, name: str, value: Any, /) -> None:
        return self.__focus.__setattr__(name, value)

    def __delattr__(self, name: str, /) -> None:
        return self.__focus.__delattr__(name)


_SIDE_WITH_KEY_EVENT: Final[dict[int, BoundFocus.Side]] = {
    Keyboard.Key.LEFT: BoundFocus.Side.ON_LEFT,
    Keyboard.Key.RIGHT: BoundFocus.Side.ON_RIGHT,
    Keyboard.Key.UP: BoundFocus.Side.ON_TOP,
    Keyboard.Key.DOWN: BoundFocus.Side.ON_BOTTOM,
}


class _GUILayeredGroup(LayeredDrawableGroup):

    __slots__ = ("__master",)

    def __init__(self, master: GUIScene) -> None:
        self.__master: GUIScene = master
        super().__init__()

    def draw_onto(self, target: AbstractRenderer) -> None:
        master: GUIScene = self.__master
        master._focus_container.update()
        super().draw_onto(target)

    def add(self, *objects: Drawable, layer: int | None = None) -> None:
        super().add(*objects, layer=layer)
        master: GUIScene = self.__master
        container: FocusableContainer = master._focus_container
        for obj in objects:
            if isinstance(obj, SupportsFocus) and obj.focus.is_bound_to(master):
                container.add(obj)

    def remove(self, *objects: Drawable) -> None:
        super().remove(*objects)
        container: FocusableContainer = self.__master._focus_container
        for obj in objects:
            if isinstance(obj, SupportsFocus) and obj in container:
                container.remove(obj)

    def pop(self, index: int = -1) -> Drawable:
        obj: Drawable = super().pop(index=index)
        container: FocusableContainer = self.__master._focus_container
        if isinstance(obj, SupportsFocus) and obj in container:
            container.remove(obj)
        return obj


class FocusableContainer(Sequence[SupportsFocus]):

    __slots__ = ("__master", "__list")

    def __init__(self, master: GUIScene) -> None:
        super().__init__()
        self.__master: GUIScene = master
        self.__list: list[SupportsFocus] = []

    def __repr__(self) -> str:
        return self.__list.__repr__()

    def __len__(self) -> int:
        return self.__list.__len__()

    @overload
    def __getitem__(self, index: int, /) -> SupportsFocus:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[SupportsFocus]:
        ...

    def __getitem__(self, index: int | slice, /) -> SupportsFocus | Sequence[SupportsFocus]:
        focusable_list: list[SupportsFocus] = self.__list
        return focusable_list[index]

    def add(self, focusable: SupportsFocus) -> None:
        if focusable in self:
            return
        if not isinstance(focusable, SupportsFocus):
            raise TypeError("'focusable' must be a SupportsFocus object")
        master: GUIScene = self.__master
        if not focusable.focus.is_bound_to(master):
            raise ValueError("'focusable' is not bound to this scene")
        self.__list.append(focusable)

    def remove(self, focusable: SupportsFocus) -> None:
        focusable_list: list[SupportsFocus] = self.__list
        focusable_list.remove(focusable)

    def update(self) -> None:
        for f in self:
            f._focus_update()


del _BoundFocusProxyMeta
