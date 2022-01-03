# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""GUI system module"""

from __future__ import annotations

__all__ = ["BoundFocus", "GUIMainScene", "GUIScene", "MetaGUIMainScene", "MetaGUIScene", "SupportsFocus"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from enum import Enum, auto, unique
from operator import truth
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Final,
    Iterator,
    List,
    Mapping,
    Optional,
    Protocol,
    Sequence,
    final,
    overload,
    runtime_checkable,
)

from ..graphics.drawable import Drawable, LayeredGroup
from ..graphics.renderer import Renderer
from ..system.utils import setdefaultattr
from .event import Event, KeyDownEvent, MouseEventType
from .keyboard import Keyboard
from .scene import AbstractLayeredScene, MainScene, MetaLayeredMainScene, MetaLayeredScene, Scene


class MetaGUIScene(MetaLayeredScene):
    pass


class GUIScene(AbstractLayeredScene, metaclass=MetaGUIScene):
    def __init__(self, /) -> None:
        super().__init__()
        self.__group: _GUILayeredGroup = _GUILayeredGroup(self)
        self.__focus_index: int = -1
        handle_key_event = self.__handle_key_event
        handle_mouse_event = self.__handle_mouse_event
        self.event.bind_key_press(Keyboard.Key.TAB, handle_key_event)
        self.event.bind_key_press(Keyboard.Key.ESCAPE, handle_key_event)
        for key in _SIDE_WITH_KEY_EVENT:
            self.event.bind_key_press(Keyboard.Key(key), handle_key_event)
        self.event.bind_event(Event.Type.MOUSEBUTTONDOWN, handle_mouse_event)
        self.event.bind_event(Event.Type.MOUSEBUTTONUP, handle_mouse_event)
        self.event.bind_event(Event.Type.MOUSEMOTION, handle_mouse_event)
        self.event.bind_event(Event.Type.MOUSEWHEEL, handle_mouse_event)

    def focus_get(self, /) -> Optional[SupportsFocus]:
        if not self.looping():
            return None
        focus_index: int = self.__focus_index
        if focus_index < 0:
            return None
        for index, focusable in enumerate(self.__group.iter_focusable()):
            if index == focus_index:
                focus: BoundFocus = focusable.focus
                if not focus.take():
                    self.focus_set(self.focus_next())
                    return self.focus_get()
                return focusable
        self.__focus_index = -1
        return None

    def focus_next(self, /) -> Optional[SupportsFocus]:
        if not self.looping():
            return None
        focusable_list: Sequence[SupportsFocus] = tuple(self.__group.iter_focusable())
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

    def focus_prev(self, /) -> Optional[SupportsFocus]:
        if not self.looping():
            return None
        focusable_list: Sequence[SupportsFocus] = tuple(self.__group.iter_focusable())
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
    def focus_set(self, /, focusable: SupportsFocus) -> bool:
        ...

    @overload
    def focus_set(self, /, focusable: None) -> None:
        ...

    def focus_set(self, /, focusable: Optional[SupportsFocus]) -> Optional[bool]:
        if not self.looping():
            return None if focusable is None else False
        if focusable is None:
            focusable = self.focus_get()
            if focusable is not None:
                self.__focus_index = -1
                self.__on_focus_leave(focusable)
            return None
        focusable_list: Sequence[SupportsFocus] = tuple(self.__group.iter_focusable())
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

    def __handle_key_event(self, /, event: KeyDownEvent) -> bool:
        if event.key == Keyboard.Key.TAB:
            BoundFocus.set_mode(BoundFocus.Mode.KEY)
            self.focus_set(self.focus_next() if not event.mod & Keyboard.Modifiers.SHIFT else self.focus_prev())
            return True
        if event.key == Keyboard.Key.ESCAPE:
            BoundFocus.set_mode(BoundFocus.Mode.KEY)
            self.focus_set(None)
            return True
        if event.key in (Keyboard.Key.LEFT, Keyboard.Key.RIGHT) and Keyboard.IME.text_input_enabled():
            return False
        if event.key in _SIDE_WITH_KEY_EVENT:
            BoundFocus.set_mode(BoundFocus.Mode.KEY)
            side: BoundFocus.Side = _SIDE_WITH_KEY_EVENT[event.key]
            self.__focus_obj_on_side(side)
            return True
        return False

    def __handle_mouse_event(self, /, event: MouseEventType) -> None:
        BoundFocus.set_mode(BoundFocus.Mode.MOUSE)

    def __focus_obj_on_side(self, side: BoundFocus.Side) -> None:
        if not self.looping():
            return
        actual_obj: Optional[SupportsFocus] = self.focus_get()
        if actual_obj is None:
            self.focus_set(self.focus_next())
            return
        obj: Optional[SupportsFocus] = actual_obj.focus.get_obj_on_side(side)
        while obj is not None and not obj.focus.take():
            obj = obj.focus.get_obj_on_side(side)
        if obj is not None:
            self.focus_set(obj)

    @property
    @final
    def group(self, /) -> LayeredGroup:
        return self.__group


class MetaGUIMainScene(MetaGUIScene, MetaLayeredMainScene):
    pass


class GUIMainScene(GUIScene, MainScene, metaclass=MetaGUIMainScene):
    pass


@runtime_checkable
class SupportsFocus(Protocol):
    @property
    @abstractmethod
    def focus(self, /) -> BoundFocus:
        raise NotImplementedError

    def _on_focus_set(self, /) -> None:
        pass

    def _on_focus_leave(self, /) -> None:
        pass


class BoundFocus:
    @unique
    class Side(str, Enum):
        def _generate_next_value_(name: str, *args: Any) -> Any:  # type: ignore[override]
            return name.lower()

        ON_TOP = auto()
        ON_BOTTOM = auto()
        ON_LEFT = auto()
        ON_RIGHT = auto()

    @unique
    class Mode(str, Enum):
        def _generate_next_value_(name: str, *args: Any) -> Any:  # type: ignore[override]
            return name.lower()

        KEY = auto()
        MOUSE = auto()

    __mode: ClassVar[Mode] = Mode.MOUSE

    def __init__(self, /, focusable: SupportsFocus, scene: Optional[Scene]) -> None:
        self.__f: SupportsFocus = focusable
        self.__scene: Optional[GUIScene] = scene if isinstance(scene, GUIScene) else None

    def is_bound_to(self, /, scene: GUIScene) -> bool:
        bound_scene: Optional[GUIScene] = self.__scene
        return bound_scene is not None and bound_scene is scene

    def get(self, /) -> Optional[SupportsFocus]:
        scene: Optional[GUIScene] = self.__scene
        if scene is None:
            return None
        return scene.focus_get()

    def has(self, /) -> bool:
        f: SupportsFocus = self.__f
        return self.get() is f

    @overload
    def take(self, /, status: bool) -> None:
        ...

    @overload
    def take(self, /) -> bool:
        ...

    def take(self, /, status: Optional[bool] = None) -> Optional[bool]:
        f: SupportsFocus = self.__f
        if status is not None:
            status = bool(status)
            setattr(f, "_take_focus_", status)
            return None
        scene: Optional[GUIScene] = self.__scene
        if scene is None:
            return False
        taken: bool = truth(getattr(f, "_take_focus_", False))
        if isinstance(f, Drawable):
            taken = taken and f.is_shown()
        return taken

    def set(self, /) -> bool:
        scene: Optional[GUIScene] = self.__scene
        if scene is None:
            return False
        f: SupportsFocus = self.__f
        return scene.focus_set(f)

    def leave(self, /) -> None:
        scene: Optional[GUIScene] = self.__scene
        if scene is None:
            return
        if self.has():
            scene.focus_set(None)

    @overload
    def set_obj_on_side(
        self,
        /,
        *,
        on_top: Optional[SupportsFocus] = ...,
        on_bottom: Optional[SupportsFocus] = ...,
        on_left: Optional[SupportsFocus] = ...,
        on_right: Optional[SupportsFocus] = ...,
    ) -> None:
        ...

    @overload
    def set_obj_on_side(self, __m: Mapping[str, Optional[SupportsFocus]], /) -> None:
        ...

    def set_obj_on_side(
        self,
        __m: Optional[Mapping[str, Optional[SupportsFocus]]] = None,
        /,
        **kwargs: Optional[SupportsFocus],
    ) -> None:
        f: SupportsFocus = self.__f
        bound_object_dict: Dict[BoundFocus.Side, Optional[SupportsFocus]] = setdefaultattr(f, "_bound_focus_objects_", {})
        if __m is not None:
            kwargs = __m | kwargs
        del __m
        for side, obj in kwargs.items():
            side = BoundFocus.Side(side)
            if obj is not None and not isinstance(obj, SupportsFocus):
                raise TypeError(f"Expected None or SupportsFocus object, got {obj!r}")
            bound_object_dict[side] = obj

    def remove_obj_on_side(self, /, *sides: str) -> None:
        self.set_obj_on_side(dict.fromkeys(sides))

    def remove_all(self, /) -> None:
        self.remove_obj_on_side(*BoundFocus.Side)

    def get_obj_on_side(self, /, side: str) -> Optional[SupportsFocus]:
        side = BoundFocus.Side(side)
        f: SupportsFocus = self.__f
        bound_object_dict: Dict[BoundFocus.Side, Optional[SupportsFocus]] = getattr(f, "_bound_focus_objects_", {})
        return bound_object_dict.get(side)

    def register_focus_set_callback(self, /, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__f
        list_callback: List[Callable[[], None]] = setdefaultattr(f, "_focus_set_callbacks_", [])
        if callback not in list_callback:
            list_callback.append(callback)

    def unregister_focus_set_callback(self, /, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__f
        list_callback: List[Callable[[], None]] = setdefaultattr(f, "_focus_set_callbacks_", [])
        list_callback.remove(callback)

    def register_focus_leave_callback(self, /, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__f
        list_callback: List[Callable[[], None]] = setdefaultattr(f, "_focus_leave_callbacks_", [])
        if callback not in list_callback:
            list_callback.append(callback)

    def unregister_focus_leave_callback(self, /, callback: Callable[[], None]) -> None:
        f: SupportsFocus = self.__f
        list_callback: List[Callable[[], None]] = setdefaultattr(f, "_focus_leave_callbacks_", [])
        list_callback.remove(callback)

    @overload
    def _drawn_by_main_group(self, /, status: bool) -> None:
        ...

    @overload
    def _drawn_by_main_group(self, /) -> bool:
        ...

    def _drawn_by_main_group(self, /, status: Optional[bool] = None) -> Optional[bool]:
        f: SupportsFocus = self.__f
        if status is not None:
            status = bool(status)
            setattr(f, "_drawn_by_main_group_", status)
            return None
        return truth(getattr(f, "_drawn_by_main_group_", True))

    @classmethod
    def get_mode(cls, /) -> Mode:
        return cls.__mode

    @classmethod
    def set_mode(cls, /, mode: Mode) -> None:
        cls.__mode = cls.Mode(mode)

    @property
    def __self__(self, /) -> SupportsFocus:
        return self.__f


_SIDE_WITH_KEY_EVENT: Final[Dict[int, BoundFocus.Side]] = {
    Keyboard.Key.LEFT: BoundFocus.Side.ON_LEFT,
    Keyboard.Key.RIGHT: BoundFocus.Side.ON_RIGHT,
    Keyboard.Key.UP: BoundFocus.Side.ON_TOP,
    Keyboard.Key.DOWN: BoundFocus.Side.ON_BOTTOM,
}


class _GUILayeredGroup(LayeredGroup):
    def __init__(self, /, master: GUIScene) -> None:
        super().__init__()
        self.__master: GUIScene = master

    def draw_onto(self, /, target: Renderer) -> None:
        for d in self:
            try:
                focus_update: Callable[[], None] = getattr(d, "_focus_update")
            except AttributeError:
                pass
            else:
                focus_update()
            if not isinstance(d, SupportsFocus) or d.focus._drawn_by_main_group():
                d.draw_onto(target)

    def iter_focusable(self, /) -> Iterator[SupportsFocus]:
        master: GUIScene = self.__master
        yield from filter(lambda d: d.focus.is_bound_to(master), self.find(SupportsFocus))  # type: ignore[misc]
