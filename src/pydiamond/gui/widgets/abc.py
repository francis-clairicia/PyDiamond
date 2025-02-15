# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Widgets module"""

from __future__ import annotations

__all__ = [
    "AbstractWidget",
    "Widget",
    "WidgetState",
]

from abc import abstractmethod
from collections.abc import Callable, Iterator
from enum import auto, unique
from itertools import takewhile
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Final,
    Literal,
    TypeGuard,
    TypeVar,
    assert_never,
    cast,
    final,
    overload,
)
from weakref import WeakMethod, WeakSet, WeakValueDictionary, ref as weakref

from ...audio.sound import Sound
from ...graphics.drawable import Drawable
from ...graphics.movable import Movable
from ...graphics.renderer import AbstractRenderer
from ...math.rect import Rect
from ...scene.abc import Scene
from ...scene.window import SceneWindow
from ...system.collections import OrderedSet, OrderedWeakSet
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.object import Object
from ...system.utils.abc import isabstractmethod
from ...system.utils.enum import AutoLowerNameEnum
from ...system.utils.functools import wraps
from ...system.utils.weakref import weakref_unwrap
from ...window.controller import ControllerButton
from ...window.cursor import Cursor, SystemCursor
from ...window.event import (
    BoundEventManager,
    ControllerButtonDownEvent,
    ControllerButtonEvent,
    ControllerButtonUpEvent,
    Event,
    KeyDownEvent,
    KeyEvent,
    KeyUpEvent,
    MouseButtonDownEvent,
    MouseButtonEvent,
    MouseButtonUpEvent,
    MouseMotionEvent,
)
from ...window.keyboard import Key
from ...window.mouse import MouseButton
from ..focus import BoundFocus
from ..scene import FocusMode


@unique
class WidgetState(AutoLowerNameEnum):
    NORMAL = auto()
    DISABLED = auto()


def __prepare_abstract_widget(mcs: Any, name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> None:
    from ...system.utils._mangling import mangle_private_attribute

    for attr in ("x", "y"):
        namespace[mangle_private_attribute(Movable, attr)] = namespace[f"_{name.strip('_')}__{attr}"]


class AbstractWidget(Drawable, Movable, prepare_namespace=__prepare_abstract_widget):
    __take_children: ClassVar[bool] = True

    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="AbstractWidget")

    def __init_subclass__(cls, *, children: bool | None = None, **kwargs: Any) -> None:
        if children is not None:
            cls.__take_children = bool(children)
        else:
            cls.__take_children = all(b.__take_children for b in cls.__bases__ if issubclass(b, AbstractWidget))
        super().__init_subclass__(**kwargs)
        draw_method: Callable[[AbstractWidget, AbstractRenderer], None] = getattr(cls, "draw_onto")
        if not getattr(draw_method, "__draw_onto_decorator__", False) and not isabstractmethod(draw_method):
            type.__setattr__(cls, "draw_onto", cls._draw_decorator(draw_method))

    @classmethod
    @final
    def take_children(cls) -> bool:
        return cls.__take_children

    @classmethod
    @final
    def _draw_decorator(
        cls: type[__Self],
        func: Callable[[__Self, AbstractRenderer], None],
    ) -> Callable[[__Self, AbstractRenderer], None]:
        from ._renderer import WidgetRendererView

        @wraps(func)
        def wrapper(self: AbstractWidget.__Self, /, target: AbstractRenderer) -> None:
            if self.__drawing:  # super().draw_onto() used
                return func(self, target)

            if (parent := self.__parent()) is not None:
                if not parent.__drawing:
                    raise TypeError(f"{self!r}: drawing asked outside parent widget")
            elif not weakref_unwrap(self.__manager)._draw_requested:
                raise TypeError(f"{self!r}: drawing asked outside manager")
            if self.is_shown():
                target = WidgetRendererView(self, target)
                self.__drawing = True
                try:
                    with target.using_clip(None):
                        self._before_widget_render(target)
                        func(self, target)
                        self._after_widget_render(target)
                finally:
                    self.__drawing = False

        wrapper.__qualname__ = f"{cls.__qualname__}.{wrapper.__name__}"
        wrapper.__module__ = cls.__module__
        setattr(wrapper, "__draw_onto_decorator__", True)
        return wrapper

    def __init__(self, master: AbstractWidget | WidgetsManager, **kwargs: Any) -> None:
        self.__event: _WidgetEventManager
        self.__event = event = _WidgetEventManager(self, priority_callbacks=True)
        self.__drawing: bool = False
        self.__shown: bool = True

        parent: AbstractWidget | None
        manager: WidgetsManager
        match master:
            case AbstractWidget() as parent:
                if not parent.__class__.__take_children:
                    raise TypeError(f"{parent.__class__.__name__} does not accept children widget")
                manager = parent._manager
                parent.__event._bind_event_manager(event)
            case WidgetsManager() as manager:
                parent = None
            case _:
                assert_never(master)

        self.__parent: Callable[[], AbstractWidget | None]
        if parent is not None:
            self.__parent = weakref(parent)
        else:
            self.__parent = lambda: None

        self.__manager: weakref[WidgetsManager] = weakref(manager)
        self.__children: OrderedSet[AbstractWidget] = OrderedSet()

        super().__init__(**kwargs)

        if parent is not None:
            parent.__children.add(self)
            try:
                parent._child_added(self)
            except BaseException:
                parent.__children.discard(self)
                try:
                    parent._child_removed(self)
                finally:
                    self.__parent = lambda: None
                    event._unbind_from_parents()
                raise
        elif manager is not None:
            manager._register(self)

    def _child_added(self, child: AbstractWidget) -> None:
        self._check_is_child(child)

    def _child_removed(self, child: AbstractWidget) -> None:
        if child.__parent() is not self:
            raise ValueError("widget was not a child")
        if child in self.__children:
            raise ValueError("child was not removed ?")

    def _before_widget_render(self, target: AbstractRenderer) -> None:
        pass

    def _update_widget(self) -> None:
        pass

    def _after_widget_render(self, target: AbstractRenderer) -> None:
        pass

    @final
    def _check_is_child(self, widget: AbstractWidget) -> None:
        if widget.__parent() is not self or widget not in self.__children:
            raise ValueError("widget is not in children")

    @final
    def _is_child(self, obj: Any) -> TypeGuard[AbstractWidget]:
        return obj in self.__children

    @final
    def iter_children(self) -> Iterator[AbstractWidget]:
        return iter(self.__children)

    @final
    def unlink(self) -> None:
        if (parent := self.__parent()) is None:
            try:
                weakref_unwrap(self.__manager)._unregister(self)
            except KeyError:
                pass
            return
        parent.__children.discard(self)
        try:
            parent._child_removed(self)
        finally:
            self.__parent = lambda: None
            self.__event._unbind_from_parents()

    def get_clip(self) -> Rect:
        return self.get_rect()

    @final
    def get_visible_rect(self) -> Rect:
        parent: AbstractWidget | None = self.__parent()
        self_rect = self.get_clip().clip(Rect(self.topleft, self.get_size()))
        master_rect: Rect
        if parent is None:
            master_rect = weakref_unwrap(self.__manager).window.rect
        else:
            master_rect = parent.get_visible_rect()
        return self_rect.clip(master_rect)

    @overload
    def get_relative_position(
        self,
        anchor: Literal["x", "y", "left", "top", "right", "bottom", "centerx", "centery"],
    ) -> float: ...

    @overload
    def get_relative_position(
        self,
        anchor: Literal[
            "center",
            "topleft",
            "topright",
            "bottomleft",
            "bottomright",
            "midleft",
            "midright",
            "midtop",
            "midbottom",
        ],
    ) -> tuple[float, float]: ...

    @overload
    def get_relative_position(self, anchor: str) -> float | tuple[float, float]: ...

    @final
    def get_relative_position(self, anchor: str) -> float | tuple[float, float]:
        parent: AbstractWidget | None = self.__parent()
        if parent is None:
            return self.get_position(anchor)
        if anchor in ("x", "left", "right", "centerx"):
            self_x = self._get_single_component_position(anchor)
            return self_x - parent.x
        if anchor in ("y", "top", "bottom", "centery"):
            self_y = self._get_single_component_position(anchor)
            return self_y - parent.y
        parent_x, parent_y = parent.topleft
        self_x, self_y = self._get_point_position(anchor)
        return self_x - parent_x, self_y - parent_y

    @final
    def get_relative_rect(self) -> Rect:
        return Rect(self.get_relative_position("topleft"), self.get_size())

    @overload
    def set_relative_position(
        self,
        *,
        x: float = ...,
        y: float = ...,
        left: float = ...,
        right: float = ...,
        top: float = ...,
        bottom: float = ...,
        centerx: float = ...,
        centery: float = ...,
    ) -> None: ...

    @overload
    def set_relative_position(
        self,
        *,
        center: tuple[float, float] = ...,
        topleft: tuple[float, float] = ...,
        topright: tuple[float, float] = ...,
        bottomleft: tuple[float, float] = ...,
        bottomright: tuple[float, float] = ...,
        midleft: tuple[float, float] = ...,
        midright: tuple[float, float] = ...,
        midtop: tuple[float, float] = ...,
        midbottom: tuple[float, float] = ...,
    ) -> None: ...

    @final
    def set_relative_position(self, **kwargs: Any) -> None:
        if not kwargs:
            return

        parent: AbstractWidget | None = self.__parent()
        if parent is not None:
            parent_x, parent_y = parent.topleft
            for anchor in kwargs:
                match anchor:
                    case "x" | "left" | "right" | "centerx":
                        kwargs[anchor] += parent_x
                    case "y" | "top" | "bottom" | "centery":
                        kwargs[anchor] += parent_y
                    case _:
                        x: float
                        y: float
                        x, y = kwargs[anchor]
                        kwargs[anchor] = (x + parent_x, y + parent_y)

        return self.set_position(**kwargs)

    @final
    def is_shown(self) -> bool:
        if not self.__shown:
            return False
        rect = self.get_visible_rect()
        return rect.width > 0 and rect.height > 0

    @final
    def show(self) -> None:
        self.__shown = True

    @final
    def hide(self) -> None:
        self.__shown = False

    @final
    def set_visibility(self, status: bool) -> None:
        self.__shown = bool(status)

    def kill(self) -> None:
        super().kill()
        self.unlink()

    @final
    def is_mouse_hovering(self, mouse_pos: tuple[float, float]) -> bool:
        if not self.get_visible_rect().collidepoint(mouse_pos):
            return False
        if (parent := self.__parent()) is not None:
            if not parent._is_mouse_hovering_child(self, mouse_pos):
                return False
        elif not weakref_unwrap(self.__manager)._is_mouse_hovering_widget(self, mouse_pos):
            return False
        x, y = self.topleft
        point = mouse_pos[0] - x, mouse_pos[1] - y
        return self._point_in_hitbox(point)

    def _is_mouse_hovering_child(self, widget: AbstractWidget, mouse_pos: tuple[float, float]) -> bool:
        return True

    def _point_in_hitbox(self, point: tuple[float, float]) -> bool:
        return True

    @property
    @final
    def parent(self) -> AbstractWidget | None:
        return self.__parent()

    @property
    @final
    def children(self) -> tuple[AbstractWidget, ...]:
        return tuple(self.__children)

    @property
    @final
    def window(self) -> SceneWindow:
        return weakref_unwrap(self.__manager).window

    @property
    @final
    def scene(self) -> Scene | None:
        return weakref_unwrap(self.__manager).scene

    @property
    @final
    def event(self: __Self) -> BoundEventManager[__Self]:
        return self.__event

    @property
    @final
    def _manager(self) -> WidgetsManager:
        return weakref_unwrap(self.__manager)

    ### THE EVIL AND DANGEROUS PART

    @property
    def __x(self) -> float:
        self.__rel_x: float
        parent: AbstractWidget | None = self.__parent()
        if parent is None:
            return self.__rel_x
        return self.__rel_x + parent.__x

    @__x.setter
    def __x(self, x: float) -> None:
        parent: AbstractWidget | None = self.__parent()
        if parent is None:
            self.__rel_x = x
            return
        self.__rel_x = x - parent.__x

    @property
    def __y(self) -> float:
        self.__rel_y: float
        parent: AbstractWidget | None = self.__parent()
        if parent is None:
            return self.__rel_y
        return self.__rel_y + parent.__y

    @__y.setter
    def __y(self, y: float) -> None:
        parent: AbstractWidget | None = self.__parent()
        if parent is None:
            self.__rel_y = y
            return
        self.__rel_y = y - parent.__y


del __prepare_abstract_widget


class Widget(AbstractWidget, children=False):
    __default_focus_on_hover: ClassVar[bool] = False

    __default_hover_cursor: Final[MappingProxyType[WidgetState, Cursor]] = MappingProxyType(
        {
            WidgetState.NORMAL: SystemCursor.HAND,
            WidgetState.DISABLED: SystemCursor.NO,
        }
    )

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "state",
        "hover_sound",
        "click_sound",
        "disabled_sound",
        "hover_cursor",
        "disabled_cursor",
    )

    state: OptionAttribute[str] = OptionAttribute()
    hover_sound: OptionAttribute[Sound | None] = OptionAttribute()
    click_sound: OptionAttribute[Sound | None] = OptionAttribute()
    disabled_sound: OptionAttribute[Sound | None] = OptionAttribute()
    hover_cursor: OptionAttribute[Cursor] = OptionAttribute()
    disabled_cursor: OptionAttribute[Cursor] = OptionAttribute()

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        invoke_method: Callable[[Widget], None] = getattr(cls, "invoke")
        if not getattr(invoke_method, "__invoke_decorator__", False) and not isabstractmethod(invoke_method):
            type.__setattr__(cls, "invoke", cls._invoke_decorator(invoke_method))

    @classmethod
    @final
    def _invoke_decorator(cls, func: Callable[[Widget], None]) -> Callable[[Widget], None]:
        @wraps(func)
        def wrapper(self: Widget) -> None:
            if self.__state != WidgetState.DISABLED:
                func(self)

        wrapper.__qualname__ = f"{cls.__qualname__}.{wrapper.__name__}"
        wrapper.__module__ = cls.__module__
        setattr(wrapper, "__invoke_decorator__", True)
        return wrapper

    @initializer
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        *,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        take_focus: bool | Literal["never"] = True,
        focus_on_hover: bool | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(master=master, **kwargs)

        if focus_on_hover is None:
            focus_on_hover = self.__default_focus_on_hover
        self.__focus_on_hover: bool = bool(focus_on_hover)

        self.__state: WidgetState = WidgetState(state)
        self.__hover: bool = False
        self.__active: bool = False
        self.__active_only_on_hover: bool = True
        self.__hover_sound: Sound | None = None
        self.__click_sound: dict[WidgetState, Sound | None] = dict.fromkeys(WidgetState)
        self.__hover_cursor: dict[WidgetState, Cursor] = self.__default_hover_cursor.copy()
        if isinstance(hover_cursor, Cursor):
            self.__hover_cursor[WidgetState.NORMAL] = hover_cursor
        if isinstance(disabled_cursor, Cursor):
            self.__hover_cursor[WidgetState.DISABLED] = disabled_cursor

        self.hover_sound = hover_sound
        self.click_sound = click_sound
        self.disabled_sound = disabled_sound
        self.__focus: BoundFocus
        match take_focus:
            case True | False:
                self.__focus = BoundFocus(self, self.scene)
                self.__focus.take(take_focus)
            case "never":
                self.__focus = BoundFocus(self, False)
            case _:
                assert_never(take_focus)

        self.event.bind(MouseButtonDownEvent, WeakMethod(self.__handle_click_event))
        self.event.bind(MouseButtonUpEvent, WeakMethod(self.__handle_click_event))
        self.event.bind(MouseMotionEvent, WeakMethod(self.__handle_mouse_motion))
        self.event.bind(KeyDownEvent, lambda self, event: self.__handle_press_event(event, focus_handle_event=False))
        self.event.bind(KeyUpEvent, lambda self, event: self.__handle_press_event(event, focus_handle_event=False))
        self.event.bind(ControllerButtonDownEvent, lambda self, event: self.__handle_press_event(event, focus_handle_event=False))
        self.event.bind(ControllerButtonUpEvent, lambda self, event: self.__handle_press_event(event, focus_handle_event=False))
        self.event.bind_mouse_position(WeakMethod(self.__handle_mouse_position))

    @abstractmethod
    def invoke(self) -> None:
        raise NotImplementedError

    @classmethod
    @final
    def get_default_cursor(cls) -> Cursor:
        return cls.__default_hover_cursor[WidgetState.NORMAL]

    @classmethod
    @final
    def get_default_disabled_cursor(cls) -> Cursor:
        return cls.__default_hover_cursor[WidgetState.DISABLED]

    @final
    def set_cursor_to_default(self) -> None:
        self.hover_cursor = self.__default_hover_cursor[WidgetState.NORMAL]

    @final
    def set_disabled_cursor_to_default(self) -> None:
        self.disabled_cursor = self.__default_hover_cursor[WidgetState.DISABLED]

    def set_active_only_on_hover(self, status: bool) -> None:
        self.__active_only_on_hover = bool(status)

    def get_focus_on_hover(self) -> bool:
        return self.__focus_on_hover

    def set_focus_on_hover(self, status: bool) -> None:
        self.__focus_on_hover = focus_on_hover = bool(status)
        if focus_on_hover and self.hover:
            self.focus.set()

    @classmethod
    def set_default_focus_on_hover(cls, status: bool | None) -> None:
        if status is not None:
            cls.__default_focus_on_hover = bool(status)
            return
        if cls is AbstractWidget:
            cls.__default_focus_on_hover = False
        else:
            try:
                del cls.__default_focus_on_hover
            except AttributeError:
                pass

    @classmethod
    def get_default_focus_on_hover(cls) -> bool:
        return cls.__default_focus_on_hover

    def __handle_click_event(self, event: MouseButtonEvent) -> bool:
        if not self.is_shown():
            self.active = self.hover = False
            return False

        if self._should_ignore_event(event):
            return False

        valid_click: bool = bool(self._valid_mouse_button(event.button) and self.is_mouse_hovering(event.pos))

        match event:
            case MouseButtonDownEvent() if valid_click:
                self.active = True
                self._on_click_down(event)
                return True
            case MouseButtonDownEvent():
                self.active = False
                self._on_click_out(event)
                return False
            case MouseButtonUpEvent() if self.active:
                self.active = False
                self._on_click_up(event)
                if not valid_click:
                    return False
                self.focus.set()
                if (click_sound := self.__click_sound[self.__state]) is not None:
                    click_sound.play()
                self._on_valid_click(event)
                self._on_hover()
                self.invoke()
                return True
            case MouseButtonUpEvent():
                self.active = False
                return False
        return False

    def __handle_mouse_motion(self, event: MouseMotionEvent) -> bool:
        if not self.is_shown():
            self.active = self.hover = False
            return False

        if self._should_ignore_event(event):
            return False

        hover = bool(self.is_mouse_hovering(event.pos))
        event_handled = False

        self.hover = hover
        if hover or (not self.__active_only_on_hover and self.active):
            event_handled = True
        self._on_mouse_motion(event)
        return event_handled

    def __handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        if not self.is_shown():
            self.active = self.hover = False
            return

        if self.focus.get_mode() not in (FocusMode.MOUSE, FocusMode.NONE) or self._should_ignore_mouse_position(mouse_pos):
            return

        if self.hover or (not self.__active_only_on_hover and self.active):
            window: SceneWindow = self.window
            window.set_cursor(self.__hover_cursor[self.__state], nb_frames=1)

    def __handle_press_event(self, event: KeyEvent | ControllerButtonEvent, focus_handle_event: bool) -> bool:
        if self.focus.get_mode() == FocusMode.NONE or self._should_ignore_event(event):
            return False

        if isinstance(event, KeyEvent) and event.key in (
            Key.K_NUMLOCK,
            Key.K_CAPSLOCK,
            Key.K_SCROLLOCK,
            Key.K_RSHIFT,
            Key.K_LSHIFT,
            Key.K_RCTRL,
            Key.K_LCTRL,
            Key.K_RALT,
            Key.K_LALT,
            Key.K_RMETA,
            Key.K_LMETA,
            Key.K_LSUPER,
            Key.K_RSUPER,
            Key.K_MODE,
        ):
            return False

        if not self.is_shown():
            self.active = self.hover = False
            return False

        if not focus_handle_event:
            if not self.focus.has():
                self.active = self.hover = False
            return False

        valid_key: bool
        match event:
            case KeyEvent():
                valid_key = self._valid_key(event.key)
            case ControllerButtonEvent():
                valid_key = self._valid_controller_button(event.button)
            case _:
                assert_never(event)

        valid_key = bool(valid_key and self.hover)

        match event:
            case KeyDownEvent() | ControllerButtonDownEvent() if valid_key:
                self.active = True
                self._on_press_down(event)
                return True
            case KeyDownEvent() | ControllerButtonDownEvent():
                self.active = False
                self._on_press_out(event)
                return False
            case KeyUpEvent() | ControllerButtonUpEvent() if self.active:
                self.active = False
                self._on_press_up(event)
                if not valid_key:
                    return False
                self.focus.set()
                if (click_sound := self.__click_sound[self.__state]) is not None:
                    click_sound.play()
                self._on_valid_click(event)
                self._on_hover()
                self.invoke()
                return True
            case KeyUpEvent() | ControllerButtonUpEvent():
                self.active = False
                return False
        return False

    def _should_ignore_event(self, event: Event) -> bool:
        return False

    def _should_ignore_mouse_position(self, mouse_pos: tuple[float, float]) -> bool:
        return False

    def _valid_mouse_button(self, button: int) -> bool:
        return button == MouseButton.LEFT

    def _valid_key(self, key: int) -> bool:
        return key in (Key.K_RETURN, Key.K_KP_ENTER)

    def _valid_controller_button(self, button: int) -> bool:
        return button == ControllerButton.BUTTON_A

    def _focus_handle_event(self, event: Event) -> bool:
        if isinstance(event, (KeyEvent, ControllerButtonEvent)) and self.__handle_press_event(event, focus_handle_event=True):
            return True
        return self.event._process_event(event)

    def _focus_update(self) -> None:
        match self.focus.get_mode():
            case FocusMode.KEY | FocusMode.JOY:
                self.hover = self.focus.has()
            case FocusMode.MOUSE if self.__focus_on_hover and self.hover and not self.focus.has():
                self.focus.set()

    def _on_change_state(self) -> None:
        pass

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        pass

    def _on_click_up(self, event: MouseButtonUpEvent) -> None:
        pass

    def _on_click_out(self, event: MouseButtonDownEvent) -> None:
        pass

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        pass

    def _on_hover(self) -> None:
        pass

    def _on_leave(self) -> None:
        pass

    def _on_active_set(self) -> None:
        pass

    def _on_press_down(self, event: KeyDownEvent | ControllerButtonDownEvent) -> None:
        pass

    def _on_press_up(self, event: KeyUpEvent | ControllerButtonUpEvent) -> None:
        pass

    def _on_press_out(self, event: KeyDownEvent | ControllerButtonDownEvent) -> None:
        pass

    def _on_valid_click(self, event: KeyUpEvent | ControllerButtonUpEvent | MouseButtonUpEvent) -> None:
        pass

    def _on_focus_set(self) -> None:
        pass

    def _on_focus_leave(self) -> None:
        pass

    @property
    def focus(self) -> BoundFocus:
        return self.__focus

    @property
    def hover(self) -> bool:
        return self.__hover

    @hover.setter
    def hover(self, status: bool) -> None:
        status = bool(status)
        if status == self.__hover:
            return
        self.__hover = status
        if status is True:
            if (hover_sound := self.__hover_sound) is not None:
                hover_sound.play()
            if self.__focus_on_hover:
                self.focus.set()
            self._on_hover()
            if self.active:
                self._on_active_set()
        else:
            self._on_leave()

    @property
    def active(self) -> bool:
        return bool(self.__active and (self.hover or not self.__active_only_on_hover))

    @active.setter
    def active(self, status: bool) -> None:
        status = bool(status)
        if status == self.__active:
            return
        self.__active = status
        if self.active:
            self._on_active_set()

    config.add_enum_converter("state", WidgetState, return_value_on_get=True)

    @config.on_update("state", use_override=False)
    def __update_state(self) -> None:
        if self.hover:
            self._on_hover()
            if self.active:
                self._on_active_set()
        else:
            self._on_leave()
        self._on_change_state()

    del __update_state

    config.add_value_validator_static("hover_sound", Sound, accept_none=True)
    config.add_value_validator_static("click_sound", Sound, accept_none=True)
    config.add_value_validator_static("disabled_sound", Sound, accept_none=True)

    @config.getter_with_key("click_sound", use_key=WidgetState.NORMAL, use_override=False)
    @config.getter_with_key("disabled_sound", use_key=WidgetState.DISABLED, use_override=False)
    def __get_click_sound(self, state: WidgetState) -> Sound | None:
        return self.__click_sound.get(state, None)

    @config.setter_with_key("click_sound", use_key=WidgetState.NORMAL, use_override=False)
    @config.setter_with_key("disabled_sound", use_key=WidgetState.DISABLED, use_override=False)
    def __set_click_sound(self, state: WidgetState, sound: Sound | None) -> None:
        self.__click_sound[state] = sound

    del __get_click_sound, __set_click_sound

    config.add_value_validator_static("hover_cursor", Cursor)
    config.add_value_validator_static("disabled_cursor", Cursor)

    @config.getter_with_key("hover_cursor", use_key=WidgetState.NORMAL, use_override=False)
    @config.getter_with_key("disabled_cursor", use_key=WidgetState.DISABLED, use_override=False)
    def __get_hover_cursor(self, state: WidgetState) -> Cursor:
        return self.__hover_cursor[state]

    @config.setter_with_key("hover_cursor", use_key=WidgetState.NORMAL, use_override=False)
    @config.setter_with_key("disabled_cursor", use_key=WidgetState.DISABLED, use_override=False)
    def __set_hover_cursor(self, state: WidgetState, cursor: Cursor) -> None:
        self.__hover_cursor[state] = cursor

    del __get_hover_cursor, __set_hover_cursor


class WidgetsManager(Object):
    __slots__ = ("__scene", "__window", "__event", "__widgets", "__drawing", "__weakref__")

    def __init__(self, master: WidgetsManager | Scene | SceneWindow) -> None:
        super().__init__()

        self.__scene: Scene | None
        self.__window: SceneWindow
        self.__event: _WidgetEventManager = _WidgetEventManager(self, priority_callbacks=True)
        self.__widgets: OrderedSet[AbstractWidget] = OrderedSet()
        self.__drawing: bool = False

        event_callback: WeakMethod[Callable[..., Any]] = WeakMethod(self.__event._process_event)  # TODO: Fix type hinting
        mouse_callback: WeakMethod[Callable[..., Any]] = WeakMethod(self.__event._handle_mouse_position)  # TODO: Fix type hinting

        match master:
            case WidgetsManager():
                self.__scene = master.__scene
                self.__window = master.__window
                master.__event.static.bind(None, event_callback)
                master.__event.static.bind_mouse_position(mouse_callback)
            case Scene():
                master.event.bind(None, event_callback)
                master.event.bind_mouse_position(mouse_callback)
                self.__scene = master
                self.__window = master.window
            case SceneWindow():
                master.event.bind(None, event_callback)
                master.event.bind_mouse_position(mouse_callback)
                self.__scene = None
                self.__window = master
            case _:
                assert_never(master)

    def draw_onto(self, target: AbstractRenderer) -> None:
        def update_widget_and_its_children(widget: AbstractWidget) -> None:
            for child in widget.iter_children():
                update_widget_and_its_children(child)
            widget._update_widget()

        self.__drawing = True
        try:
            for widget in self.__widgets:
                update_widget_and_its_children(widget)
                widget.draw_onto(target)
        finally:
            self.__drawing = False

    def _register(self, widget: AbstractWidget) -> None:
        assert isinstance(widget, AbstractWidget)
        if widget._manager is not self:
            raise ValueError("widget.manager is not self")
        if widget.parent is not None:
            raise ValueError("widget parent is not None")
        widget_event_manager = cast(_WidgetEventManager, widget.event)
        self.__widgets.add(widget)
        self.__event._bind_event_manager(widget_event_manager)

    def _unregister(self, widget: AbstractWidget) -> None:
        assert isinstance(widget, AbstractWidget)
        if widget._manager is not self:
            raise ValueError("widget.manager is not self")
        widget_event_manager = cast(_WidgetEventManager, widget.event)
        self.__widgets.remove(widget)
        self.__event._unbind_event_manager(widget_event_manager)

    @final
    def _is_mouse_hovering_widget(self, widget: AbstractWidget, mouse_pos: tuple[float, float]) -> bool:
        return not any(
            child.get_visible_rect().collidepoint(mouse_pos)
            for child in takewhile(lambda child: child is not widget, reversed(self.__widgets))
        )

    @property
    @final
    def scene(self) -> Scene | None:
        return self.__scene

    @property
    @final
    def window(self) -> SceneWindow:
        return self.__window

    @property
    @final
    def children(self) -> tuple[AbstractWidget, ...]:
        return tuple(self.__widgets)

    @property
    @final
    def _draw_requested(self) -> bool:
        return self.__drawing


@final
class _WidgetEventManager(BoundEventManager[Any]):
    __slots__ = (
        "__other_manager_list",
        "__priority_manager",
        "__parent_managers",
    )

    def __init__(self, obj: AbstractWidget | WidgetsManager, *, priority_callbacks: bool = True) -> None:
        assert isinstance(obj, (AbstractWidget, WidgetsManager))

        selfref: weakref[_WidgetEventManager] = weakref(self)

        def unbind_all() -> None:
            self = selfref()
            if self is not None:
                for manager in list(self.__parent_managers):
                    try:
                        manager._unbind_event_manager(self)
                    except KeyError:
                        pass
                self.__other_manager_list.clear()
                self.__priority_manager.clear()

        super().__init__(obj, priority_callbacks=priority_callbacks, weakref_callback=unbind_all)
        self.__other_manager_list: OrderedWeakSet[_WidgetEventManager] = OrderedWeakSet()
        self.__priority_manager: WeakValueDictionary[type[Event], _WidgetEventManager] = WeakValueDictionary()
        self.__parent_managers: WeakSet[_WidgetEventManager] = WeakSet()

    def __del__(self) -> None:
        self.__other_manager_list.clear()
        self.__priority_manager.clear()
        self.__parent_managers.clear()
        return super().__del__()

    def _unbind_from_parents(self) -> None:
        for manager in list(self.__parent_managers):
            manager._unbind_event_manager(self)

    def _bind_event_manager(self, manager: _WidgetEventManager) -> None:
        assert isinstance(manager, _WidgetEventManager)
        self.__other_manager_list.add(manager)
        manager.__parent_managers.add(self)

    def _unbind_event_manager(self, manager: _WidgetEventManager) -> None:
        self.__other_manager_list.remove(manager)
        manager.__parent_managers.discard(self)
        for event_type in tuple(
            event_type for event_type, priority_manager in self.__priority_manager.items() if priority_manager is manager
        ):
            self.__priority_manager.pop(event_type)

    def _process_event(self, event: Event) -> bool:
        event_type: type[Event] = type(event)

        priority_manager: _WidgetEventManager | None = self.__priority_manager.get(event_type)
        if priority_manager is not None:
            if priority_manager._process_event(event):
                return True
            del self.__priority_manager[event_type]

        for manager in self.__other_manager_list:
            if manager is not priority_manager and manager._process_event(event):
                self.__priority_manager[event_type] = manager
                return True

        return super()._process_event(event)

    def _handle_mouse_position(self, mouse_pos: tuple[float, float]) -> None:
        for manager in self.__other_manager_list:
            manager._handle_mouse_position(mouse_pos)
        return super()._handle_mouse_position(mouse_pos)
