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
    "GUIMainScene",
    "GUIMainSceneMeta",
    "GUIScene",
    "GUISceneMeta",
    "NoFocusSupportError",
    "SupportsFocus",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import auto, unique
from operator import truth
from types import FunctionType, LambdaType
from typing import Any, Callable, ClassVar, Final, Mapping, Protocol, Sequence, TypedDict, final, overload, runtime_checkable

from ..graphics.drawable import Drawable, LayeredGroup
from ..graphics.renderer import Renderer
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
from .scene import AbstractLayeredScene, LayeredMainSceneMeta, LayeredSceneMeta, MainScene, Scene


class GUISceneMeta(LayeredSceneMeta):
    pass


class GUIScene(AbstractLayeredScene, metaclass=GUISceneMeta):

    __slots__ = ("__group", "__focus_index", "__container")

    def __init__(self) -> None:
        super().__init__()
        self.__container: FocusableContainer = FocusableContainer(self)
        self.__group: _GUILayeredGroup = _GUILayeredGroup(self)
        self.__focus_index: int = -1
        handle_key_event = self.__handle_key_event
        set_focus_mode_key: Callable[[KeyEvent], None] = lambda event: BoundFocus.set_mode(BoundFocus.Mode.KEY)
        set_focus_mode_mouse: Callable[[MouseEvent], None] = lambda event: BoundFocus.set_mode(BoundFocus.Mode.MOUSE)
        self.event.bind_event(KeyDownEvent, set_focus_mode_key)
        self.event.bind_event(KeyUpEvent, set_focus_mode_key)
        self.event.bind_event(MouseButtonDownEvent, set_focus_mode_mouse)
        self.event.bind_event(MouseButtonUpEvent, set_focus_mode_mouse)
        self.event.bind_event(MouseMotionEvent, set_focus_mode_mouse)
        self.event.bind_event(MouseWheelEvent, set_focus_mode_mouse)
        self.event.bind_key_press(Keyboard.Key.TAB, handle_key_event)
        self.event.bind_key_press(Keyboard.Key.ESCAPE, handle_key_event)

    def handle_event(self, event: Event) -> bool:
        if super().handle_event(event):
            return True
        if isinstance(event, KeyDownEvent) and self.__handle_key_event(event):
            return True
        return False

    def focus_get(self) -> SupportsFocus | None:
        if not self.looping():
            return None
        focus_index: int = self.__focus_index
        if focus_index < 0:
            return None
        for index, focusable in enumerate(self.__container):
            if index == focus_index:
                focus: BoundFocus = focusable.focus
                if not focus.take():
                    self.focus_set(self.focus_next())
                    return self.focus_get()
                return focusable
        self.__focus_index = -1
        return None

    def focus_next(self) -> SupportsFocus | None:
        if not self.looping():
            return None
        focusable_list: Sequence[SupportsFocus] = self.__container
        if not focusable_list:
            self.__focus_index = -1
            return None
        focus_index: int = max(self.__focus_index, -1)
        if any(obj.focus.take() for obj in focusable_list):
            size = len(focusable_list)
            while True:
                focus_index = (focus_index + 1) % size
                obj = focusable_list[focus_index]
                if obj.focus.take():
                    return obj
        self.__focus_index = -1
        return None

    def focus_prev(self) -> SupportsFocus | None:
        if not self.looping():
            return None
        focusable_list: Sequence[SupportsFocus] = self.__container
        if not focusable_list:
            self.__focus_index = -1
            return None
        focus_index: int = self.__focus_index
        if focus_index < 0:
            focus_index = 1
        if any(obj.focus.take() for obj in focusable_list):
            size = len(focusable_list)
            while True:
                focus_index = (focus_index - 1) % size
                obj = focusable_list[focus_index]
                if obj.focus.take():
                    return obj
        self.__focus_index = -1
        return None

    @overload
    def focus_set(self, focusable: SupportsFocus) -> bool:
        ...

    @overload
    def focus_set(self, focusable: None) -> None:
        ...

    def focus_set(self, focusable: SupportsFocus | None) -> bool | None:
        if not self.looping():
            return None if focusable is None else False
        if focusable is None:
            focusable = self.focus_get()
            if focusable is not None:
                self.__focus_index = -1
                self.__on_focus_leave(focusable)
            return None
        focusable_list: Sequence[SupportsFocus] = self.__container
        if focusable not in focusable_list or not focusable.focus.take():
            return False
        focus_index: int = self.__focus_index
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

    def __on_focus_set(self, focusable: SupportsFocus) -> None:
        focusable._on_focus_set()
        callback: Callable[[], None]
        for callback in getattr(focusable, "_focus_set_callbacks_", ()):
            callback()

    def __on_focus_leave(self, focusable: SupportsFocus) -> None:
        focusable._on_focus_leave()
        callback: Callable[[], None]
        for callback in getattr(focusable, "_focus_leave_callbacks_", ()):
            callback()

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

    def __focus_obj_on_side(self, side: BoundFocus.Side) -> None:
        if not self.looping():
            return
        actual_obj: SupportsFocus | None = self.focus_get()
        if actual_obj is None:
            self.focus_set(self.focus_next())
            return
        obj: SupportsFocus | None = actual_obj.focus.get_obj_on_side(side)
        while obj is not None and not obj.focus.take():
            obj = obj.focus.get_obj_on_side(side)
        if obj is not None:
            self.focus_set(obj)

    @property
    @final
    def group(self) -> LayeredGroup:
        return self.__group

    @property
    def focus_container(self) -> FocusableContainer:
        return self.__container


class GUIMainSceneMeta(GUISceneMeta, LayeredMainSceneMeta):
    pass


class GUIMainScene(GUIScene, MainScene, metaclass=GUIMainSceneMeta):
    __slots__ = ()


@runtime_checkable
class _HasFocusMethods(Protocol):
    def _on_focus_set(self) -> None:
        pass

    def _on_focus_leave(self) -> None:
        pass

    def _focus_update(self) -> None:
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
        self.__f: SupportsFocus = focusable
        self.__scene: GUIScene | None = scene if isinstance(scene, GUIScene) else None

    def is_bound_to(self, scene: GUIScene) -> bool:
        bound_scene: GUIScene | None = self.__scene
        return bound_scene is not None and bound_scene is scene

    def get(self) -> SupportsFocus | None:
        scene: GUIScene | None = self.__scene
        if scene is None:
            return None
        return scene.focus_get()

    def has(self) -> bool:
        f: SupportsFocus = self.__self__
        return self.get() is f

    @overload
    def take(self, status: bool) -> None:
        ...

    @overload
    def take(self) -> bool:
        ...

    def take(self, status: bool | None = None) -> bool | None:
        f: SupportsFocus = self.__self__
        if status is not None:
            status = bool(status)
            setattr(f, "_take_focus_", status)
            return None
        scene: GUIScene | None = self.__scene
        if scene is None:
            return False
        taken: bool = truth(getattr(f, "_take_focus_", False))
        if isinstance(f, Drawable):
            taken = taken and f.is_shown()
        return taken

    def set(self) -> bool:
        scene: GUIScene | None = self.__scene
        if scene is None:
            return False
        f: SupportsFocus = self.__self__
        return scene.focus_set(f)

    def leave(self) -> None:
        scene: GUIScene | None = self.__scene
        if scene is None:
            return
        if self.has():
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
        self.set_obj_on_side(dict.fromkeys(sides))

    def remove_all(self) -> None:
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
        return self.__f


class _BoundFocusProxyMeta(type):
    def __new__(metacls, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> _BoundFocusProxyMeta:
        if "BoundFocusProxy" in globals() and not any(issubclass(cls, BoundFocusProxy) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {BoundFocusProxy.__name__} class in order to use {_BoundFocusProxyMeta.__name__} metaclass"
            )

        if "BoundFocusProxy" not in globals() and name == "BoundFocusProxy":

            def proxy_method_wrapper(func: Callable[..., Any]) -> Callable[..., Any]:
                method_name: str = func.__name__

                @wraps(func)
                def wrapper(self: BoundFocusProxy, /, *args: Any, **kwargs: Any) -> Any:
                    focus: BoundFocus = self.original
                    method: Callable[..., Any] = getattr(focus, method_name)
                    return method(*args, **kwargs)

                return wrapper

            def proxy_property_wrapper(name: str, obj: property) -> property:
                if callable(obj.fget):

                    @wraps(obj.fget)
                    def getter(self: BoundFocusProxy, /) -> Any:
                        focus: BoundFocus = self.original
                        return getattr(focus, name)

                    obj = obj.getter(getter)

                if callable(obj.fset):

                    @wraps(obj.fset)
                    def setter(self: BoundFocusProxy, value: Any, /) -> None:
                        focus: BoundFocus = self.original
                        return setattr(focus, name, value)

                    obj = obj.setter(setter)

                if callable(obj.fdel):

                    @wraps(obj.fdel)
                    def deleter(self: BoundFocusProxy, /) -> None:
                        focus: BoundFocus = self.original
                        return delattr(focus, name)

                    obj = obj.deleter(deleter)

                return obj

            for attr_name, attr_obj in vars(BoundFocus).items():
                if isinstance(attr_obj, property):
                    namespace[attr_name] = proxy_property_wrapper(attr_name, attr_obj)
                elif isinstance(attr_obj, (FunctionType, LambdaType)) and not attr_name.startswith("__"):
                    namespace[attr_name] = proxy_method_wrapper(attr_obj)

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class BoundFocusProxy(BoundFocus, metaclass=_BoundFocusProxyMeta):

    __slots__ = ("__focus",)

    def __init__(self, focus: BoundFocus) -> None:
        super().__init__(focus.__self__, getattr_pv(focus, "scene", None, owner=BoundFocus))
        self.__focus: BoundFocus = focus

    def __getattr__(self, name: str, /) -> Any:
        focus: BoundFocus = self.original
        return getattr(focus, name)

    @property
    def original(self) -> BoundFocus:
        return self.__focus


_SIDE_WITH_KEY_EVENT: Final[dict[int, BoundFocus.Side]] = {
    Keyboard.Key.LEFT: BoundFocus.Side.ON_LEFT,
    Keyboard.Key.RIGHT: BoundFocus.Side.ON_RIGHT,
    Keyboard.Key.UP: BoundFocus.Side.ON_TOP,
    Keyboard.Key.DOWN: BoundFocus.Side.ON_BOTTOM,
}


class _GUILayeredGroup(LayeredGroup):

    __slots__ = ("__master",)

    def __init__(self, master: GUIScene) -> None:
        self.__master: GUIScene = master
        super().__init__()

    def draw_onto(self, target: Renderer) -> None:
        master: GUIScene = self.__master
        master.focus_container.update()
        super().draw_onto(target)

    def add(self, *objects: Drawable, layer: int | None = None) -> None:
        super().add(*objects, layer=layer)
        master: GUIScene = self.__master
        container: FocusableContainer = master.focus_container
        for obj in objects:
            if isinstance(obj, SupportsFocus) and obj.focus.is_bound_to(master):
                container.add(obj)

    def remove(self, *objects: Drawable) -> None:
        super().remove(*objects)
        container: FocusableContainer = self.__master.focus_container
        for obj in objects:
            if isinstance(obj, SupportsFocus) and obj in container:
                container.remove(obj)

    def pop(self, index: int = -1) -> Drawable:
        obj: Drawable = super().pop(index=index)
        container: FocusableContainer = self.__master.focus_container
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
        list_length = self.__list.__len__
        return list_length()

    @overload
    def __getitem__(self, index: int, /) -> SupportsFocus:
        ...

    @overload
    def __getitem__(self, index: slice, /) -> Sequence[SupportsFocus]:
        ...

    def __getitem__(self, index: int | slice, /) -> SupportsFocus | Sequence[SupportsFocus]:
        focusable_list: list[SupportsFocus] = self.__list
        if isinstance(index, slice):
            return tuple(focusable_list[index])
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
