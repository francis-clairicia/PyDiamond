# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""ScrollBar and ScrollArea module"""

from __future__ import annotations

__all__ = ["ScrollArea", "ScrollAreaElement", "ScrollBar"]


from abc import abstractmethod
from contextlib import suppress
from enum import auto, unique
from typing import TYPE_CHECKING, Any, ClassVar, Protocol, Sequence, final, runtime_checkable

from ...graphics.color import BLACK, GRAY, TRANSPARENT, WHITE, Color
from ...graphics.drawable import BaseLayeredDrawableGroup, Drawable, SupportsDrawableGroups
from ...graphics.movable import Movable
from ...graphics.rect import Rect
from ...graphics.renderer import AbstractRenderer
from ...graphics.shape import RectangleShape
from ...graphics.surface import SurfaceRenderer
from ...graphics.transformable import Transformable
from ...system.configuration import ConfigurationTemplate, OptionAttribute, initializer
from ...system.enum import AutoLowerNameEnum
from ...system.theme import ThemedObjectMeta, ThemeType
from ...system.utils._mangling import mangle_private_attribute
from ...window.clickable import Clickable
from ...window.event import MouseButtonDownEvent, MouseButtonUpEvent, MouseMotionEvent, MouseWheelEvent
from ...window.mouse import Mouse

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...window.cursor import Cursor
    from ...window.display import Window
    from ...window.scene import Scene


class ScrollBar(Drawable, Transformable, Clickable, metaclass=ThemedObjectMeta):
    __theme_ignore__: ClassVar[Sequence[str]] = ("orient",)

    @unique
    class Orient(AutoLowerNameEnum):
        HORIZONTAL = auto()
        VERTICAL = auto()

    config: ClassVar[ConfigurationTemplate] = ConfigurationTemplate(
        "local_width",
        "local_height",
        "local_size",
        "cursor_color",
        "color",
        "outline",
        "outline_color",
        "border_radius",
        "border_top_left_radius",
        "border_top_right_radius",
        "border_bottom_left_radius",
        "border_bottom_right_radius",
        "orient",
    )

    local_width: OptionAttribute[float] = OptionAttribute()
    local_height: OptionAttribute[float] = OptionAttribute()
    local_size: OptionAttribute[tuple[float, float]] = OptionAttribute()
    cursor_color: OptionAttribute[Color] = OptionAttribute()
    color: OptionAttribute[Color] = OptionAttribute()
    outline: OptionAttribute[int] = OptionAttribute()
    outline_color: OptionAttribute[Color] = OptionAttribute()
    border_radius: OptionAttribute[int] = OptionAttribute()
    border_top_left_radius: OptionAttribute[int] = OptionAttribute()
    border_top_right_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_left_radius: OptionAttribute[int] = OptionAttribute()
    border_bottom_right_radius: OptionAttribute[int] = OptionAttribute()
    orient: OptionAttribute[str] = OptionAttribute()

    @initializer
    def __init__(
        self,
        master: ScrollArea,
        width: float,
        height: float,
        *,
        orient: str = "horizontal",
        color: Color = WHITE,
        cursor_color: Color = GRAY,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        outline: int = 0,
        outline_color: Color = BLACK,
        border_radius: int = 0,
        border_top_left_radius: int = -1,
        border_top_right_radius: int = -1,
        border_bottom_left_radius: int = -1,
        border_bottom_right_radius: int = -1,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        if not isinstance(master, ScrollArea):
            raise TypeError("ScrollBar objects must be created for a ScrollArea object")
        self.__master: ScrollArea = master
        super().__init__(
            master=master.master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            **kwargs,
        )
        self.__bg_shape: RectangleShape = RectangleShape(
            width=width,
            height=height,
            color=color,
            outline=0,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        self.__outline_shape: RectangleShape = RectangleShape(
            width=width,
            height=height,
            color=TRANSPARENT,
            outline=outline,
            outline_color=outline_color,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        self.__start: float = 0
        self.__end: float = 0
        self.__cursor_click: float
        self.__cursor_shape: RectangleShape = RectangleShape(
            width=0,
            height=0,
            color=cursor_color,
            outline=0,
            border_radius=border_radius,
            border_top_left_radius=border_top_left_radius,
            border_top_right_radius=border_top_right_radius,
            border_bottom_left_radius=border_bottom_left_radius,
            border_bottom_right_radius=border_bottom_right_radius,
        )
        self.orient = orient
        self.set_active_only_on_hover(False)
        master._bind(self)

    def get_local_size(self) -> tuple[float, float]:
        return self.__outline_shape.get_local_size()

    def get_size(self) -> tuple[float, float]:
        return self.__outline_shape.get_size()

    def draw_onto(self, target: AbstractRenderer) -> None:
        bg_shape: RectangleShape = self.__bg_shape
        cursor_shape: RectangleShape = self.__cursor_shape
        outline_shape: RectangleShape = self.__outline_shape
        outline: int = outline_shape.outline

        bg_shape.draw_onto(target)

        cursor_start: float = self.__start
        cursor_end: float = self.__end
        cursor_middle: float = (cursor_start + cursor_end) / 2
        if self.orient == ScrollBar.Orient.HORIZONTAL:
            if cursor_middle <= 0.5:
                cursor_shape.midleft = (
                    max(bg_shape.left + bg_shape.width * cursor_start, bg_shape.left + (outline / 2)),
                    bg_shape.centery,
                )
            else:
                cursor_shape.midright = (
                    min(bg_shape.left + bg_shape.width * cursor_end, bg_shape.right - (outline / 2)),
                    bg_shape.centery,
                )
        else:
            if cursor_middle <= 0.5:
                cursor_shape.midtop = (
                    bg_shape.centerx,
                    max(bg_shape.top + bg_shape.height * cursor_start, bg_shape.top + (outline / 2)),
                )
            else:
                cursor_shape.midbottom = (
                    bg_shape.centerx,
                    min(bg_shape.top + bg_shape.height * cursor_end, bg_shape.bottom - (outline / 2)),
                )

        cursor_shape.draw_onto(target)
        outline_shape.draw_onto(target)

    def invoke(self) -> None:
        pass

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.get_rect().collidepoint(mouse_pos)

    def _on_click_down(self, event: MouseButtonDownEvent) -> None:
        cursor_rect: Rect = self.__get_cursor_shape_rect()
        if not cursor_rect.collidepoint(event.pos):
            cursor_rect.center = event.pos
            self.__set_cursor_bounds(cursor_rect)
            self.__cursor_click = 0.5
        elif self.orient == ScrollBar.Orient.HORIZONTAL:
            self.__cursor_click = (event.pos[0] - cursor_rect.left) / cursor_rect.width
        else:
            self.__cursor_click = (event.pos[1] - cursor_rect.top) / cursor_rect.height
        return super()._on_click_down(event)

    def _on_click_up(self, event: MouseButtonUpEvent) -> None:
        with suppress(AttributeError):
            del self.__cursor_click
        return super()._on_click_up(event)

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        rect: Rect = self.get_rect()

        def in_bounds() -> bool:
            if self.orient == ScrollBar.Orient.HORIZONTAL:
                return rect.left <= event.pos[0] <= rect.right
            return rect.top <= event.pos[1] <= rect.bottom

        if self.active and in_bounds():
            cursor_rect: Rect = self.__get_cursor_shape_rect()
            cursor_click: float = self.__cursor_click
            if self.orient == ScrollBar.Orient.HORIZONTAL:
                cursor_rect.left = int(event.pos[0] - cursor_click * cursor_rect.width)
            else:
                cursor_rect.top = int(event.pos[1] - cursor_click * cursor_rect.height)
            self.__set_cursor_bounds(cursor_rect)
        return super()._on_mouse_motion(event)

    def _on_move(self) -> None:
        self.__bg_shape.center = self.__outline_shape.center = self.center
        return super()._on_move()

    def _apply_both_rotation_and_scale(self) -> None:
        raise NotImplementedError

    def _apply_only_rotation(self) -> None:
        raise NotImplementedError

    def _apply_only_scale(self) -> None:
        self.__outline_shape.scale = self.__bg_shape.scale = self.__cursor_shape.scale = self.scale

    def __get_cursor_shape_rect(self) -> Rect:
        cursor_shape: RectangleShape = self.__cursor_shape
        cursor_rect: Rect = cursor_shape.get_rect()

        cursor_start: float = self.__start
        if self.orient == ScrollBar.Orient.HORIZONTAL:
            cursor_rect.midleft = int(self.left + self.width * cursor_start), int(self.centery)
        else:
            cursor_rect.midtop = int(self.centerx), int(self.top + self.height * cursor_start)
        return cursor_rect

    def __set_cursor_bounds(self, cursor_rect: Rect) -> None:
        offset: float = round(self.__end - self.__start, 2)
        if self.orient == ScrollBar.Orient.HORIZONTAL:
            left: float = self.left
            width: float = self.width
            if width == 0:
                return
            if cursor_rect.left < left:
                cursor_rect.left = int(left)
            self.__start = max((cursor_rect.left - left) / width, 0)
        else:
            top: float = self.top
            height: float = self.height
            if height == 0:
                return
            if cursor_rect.top < top:
                cursor_rect.top = int(top)
            self.__start = max((cursor_rect.top - top) / height, 0)
        if (end := self.__start + offset) > 1:
            end = 1
            self.__start = 1 - offset
        self.__end = end
        self.__master._update()

    config.add_enum_converter("orient", Orient, return_value_on_get=True)

    @config.getter_with_key("cursor_color", use_key="color")
    def __get_cursor_shape_options(self, option: str) -> Any:
        return self.__cursor_shape.config.get(option)

    @config.setter_with_key("cursor_color", use_key="color")
    def __set_cursor_shape_options(self, option: str, value: Any) -> Any:
        return self.__cursor_shape.config.set(option, value)

    @config.getter_with_key("outline")
    @config.getter_with_key("outline_color")
    def __get_outline_options(self, option: str) -> Any:
        return self.__outline_shape.config.get(option)

    @config.setter_with_key("outline")
    @config.setter_with_key("outline_color")
    def __set_outline_options(self, option: str, value: Any) -> None:
        self.__outline_shape.config.set(option, value)

    @config.getter_with_key("local_width")
    @config.getter_with_key("local_height")
    @config.getter_with_key("local_size")
    @config.getter_with_key("color")
    @config.getter_with_key("border_radius")
    @config.getter_with_key("border_top_left_radius")
    @config.getter_with_key("border_top_right_radius")
    @config.getter_with_key("border_bottom_left_radius")
    @config.getter_with_key("border_bottom_right_radius")
    def __get_shape_option(self, option: str) -> Any:
        return self.__bg_shape.config.get(option)

    @config.setter_with_key("local_width")
    @config.setter_with_key("local_height")
    @config.setter_with_key("local_size")
    @config.setter_with_key("color")
    @config.setter_with_key("border_radius")
    @config.setter_with_key("border_top_left_radius")
    @config.setter_with_key("border_top_right_radius")
    @config.setter_with_key("border_bottom_left_radius")
    @config.setter_with_key("border_bottom_right_radius")
    def __set_shape_option(self, option: str, value: Any) -> Any:
        return self.__bg_shape.config.set(option, value)

    @config.on_update_value_with_key("border_radius")
    @config.on_update_value_with_key("border_top_left_radius")
    @config.on_update_value_with_key("border_top_right_radius")
    @config.on_update_value_with_key("border_bottom_left_radius")
    @config.on_update_value_with_key("border_bottom_right_radius")
    def __update_cursor_shape_option(self, option: str, value: Any) -> None:
        self.__cursor_shape.config.set(option, value)
        self.__outline_shape.config.set(option, value)

    @config.on_update("orient")
    @config.on_update("local_width")
    @config.on_update("local_height")
    @config.on_update("local_size")
    def __update_all_shape(self) -> None:
        outline_shape: RectangleShape = self.__outline_shape
        outline_shape.local_size = self.local_size
        self._update()

    def _update(self) -> None:
        width, height = self.local_size
        orient: str = self.orient
        cursor_shape: RectangleShape = self.__cursor_shape
        cursor_size_percent: float = self.__end - self.__start
        if orient == ScrollBar.Orient.HORIZONTAL:
            cursor_shape.local_size = (width * cursor_size_percent, height)
        else:
            cursor_shape.local_size = (width, height * cursor_size_percent)

    @property
    @final
    def scroll_area(self) -> ScrollArea:
        return self.__master

    @property
    @final
    def bounds(self) -> tuple[float, float]:
        return (self.__start, self.__end)


@runtime_checkable
class ScrollAreaElement(SupportsDrawableGroups, Protocol):
    @abstractmethod
    def get_rect(self) -> Rect:
        raise NotImplementedError


class ScrollArea(BaseLayeredDrawableGroup[ScrollAreaElement], Drawable, Movable):
    __h_flip: ClassVar[bool] = False
    __v_flip: ClassVar[bool] = False

    def __init__(
        self,
        *objects: ScrollAreaElement,
        master: Scene | Window,
        width: float,
        height: float,
        default_layer: int = 0,
        bg_color: Color = TRANSPARENT,
        **kwargs: Any,
    ) -> None:
        super().__init__(*objects, default_layer=default_layer, **kwargs)
        self.__master: Scene | Window = master
        self.__view_rect: Rect = Rect(0, 0, width, height)
        self.__whole_area: SurfaceRenderer = SurfaceRenderer((width, height))
        self.__h_scroll: ScrollBar | None = None
        self.__v_scroll: ScrollBar | None = None
        self.__bg_color: Color = bg_color
        master.event.bind(MouseWheelEvent, self.__handle_wheel_event)

    @classmethod
    def set_horizontal_flip(cls, status: bool) -> None:
        cls.__h_flip = bool(status)

    @classmethod
    def set_vertical_flip(cls, status: bool) -> None:
        cls.__v_flip = bool(status)

    @classmethod
    def get_wheel_flip(cls) -> tuple[bool, bool]:
        return (cls.__h_flip, cls.__v_flip)

    def get_size(self) -> tuple[float, float]:
        return self.__view_rect.size

    def add(self, *objects: ScrollAreaElement, layer: int | None = None) -> None:
        if any(not isinstance(obj, ScrollAreaElement) for obj in objects):
            raise TypeError("Invalid arguments")
        return super().add(*objects, layer=layer)

    def draw_onto(self, target: AbstractRenderer) -> None:
        whole_area = self.__update_whole_area()
        super().draw_onto(whole_area)
        target.draw_surface(whole_area.surface, self.topleft, area=self.__view_rect)

    def _bind(self, scrollbar: ScrollBar) -> None:
        if scrollbar.scroll_area is not self:
            raise ValueError("scrollbar bound to an another ScrollArea")
        if scrollbar.orient == ScrollBar.Orient.HORIZONTAL:
            if (h_scroll := self.__h_scroll) is not None:
                if h_scroll is not scrollbar:
                    raise ValueError("self already have a horizontal scrollbar")
                return
            self.__h_scroll = scrollbar
        else:
            if (v_scroll := self.__v_scroll) is not None:
                if v_scroll is not scrollbar:
                    raise ValueError("self already have a vertical scrollbar")
                return
            self.__v_scroll = scrollbar
        self.__update_scrollbars_cursor()

    def _update(self) -> None:
        whole_area: SurfaceRenderer = self.__whole_area
        whole_area_rect = whole_area.get_rect()
        view_rect: Rect = self.__view_rect
        start: float
        end: float
        h_scroll: ScrollBar | None = self.__h_scroll
        v_scroll: ScrollBar | None = self.__v_scroll
        if h_scroll is not None:
            start, end = h_scroll.bounds
            view_rect.left = int(whole_area_rect.width * start)
            view_rect.width = int(whole_area_rect.width * (end - start))
        if v_scroll is not None:
            start, end = v_scroll.bounds
            view_rect.top = int(whole_area_rect.height * start)
            view_rect.height = int(whole_area_rect.height * (end - start))

    def __handle_wheel_event(self, event: MouseWheelEvent) -> bool:
        if not self.get_rect().collidepoint(Mouse.get_pos()):
            return False
        view_rect: Rect = self.__view_rect
        whole_area: SurfaceRenderer = self.__whole_area
        whole_area_rect = whole_area.get_rect()
        offset: int = 20
        need_update: bool = False
        if event.x != 0:
            x: int = (1 if event.x > 0 else -1) if not self.__h_flip else (-1 if event.x > 0 else 1)
            if event.flipped:
                x = -x
            view_rect.x += offset * x
            if x > 0:
                view_rect.right = min(view_rect.right, whole_area_rect.right)
            else:
                view_rect.left = max(view_rect.left, whole_area_rect.left)
            need_update = True
        if event.y != 0:
            y: int = (1 if event.y > 0 else -1) if not self.__v_flip else (-1 if event.y > 0 else 1)
            if event.flipped:
                y = -y
            view_rect.y += offset * y
            if y > 0:
                view_rect.bottom = min(view_rect.bottom, whole_area_rect.bottom)
            else:
                view_rect.top = max(view_rect.top, whole_area_rect.top)
            need_update = True
        if need_update:
            self.__update_whole_area()
            self.__update_scrollbars_cursor()
        return True

    def __update_whole_area(self) -> SurfaceRenderer:
        whole_area: SurfaceRenderer = self.__whole_area
        view_rect: Rect = self.__view_rect
        width: int = view_rect.width
        height: int = view_rect.height
        for m in self:
            m_rect = m.get_rect()
            width = max(width, m_rect.right)
            height = max(height, m_rect.bottom)

        if (width, height) != whole_area.get_size():
            self.__whole_area = whole_area = SurfaceRenderer((width, height))
            whole_area_rect = whole_area.get_rect()
            view_rect.right = min(view_rect.right, whole_area_rect.right)
            view_rect.bottom = min(view_rect.bottom, whole_area_rect.bottom)
            self.__update_scrollbars_cursor()
        whole_area.fill(self.__bg_color)
        return whole_area

    def __update_scrollbars_cursor(self) -> None:
        start_attr: str = mangle_private_attribute(ScrollBar, "start")
        end_attr: str = mangle_private_attribute(ScrollBar, "end")
        whole_area_rect = self.__whole_area.get_rect()
        view_rect: Rect = self.__view_rect
        start: float
        end: float
        h_scroll: ScrollBar | None = self.__h_scroll
        v_scroll: ScrollBar | None = self.__v_scroll
        if h_scroll is not None:
            start = (view_rect.left - whole_area_rect.left) / whole_area_rect.width
            end = view_rect.right / whole_area_rect.width
            setattr(h_scroll, start_attr, start)
            setattr(h_scroll, end_attr, end)
            h_scroll._update()
        if v_scroll is not None:
            start = view_rect.top / whole_area_rect.height
            end = view_rect.bottom / whole_area_rect.height
            setattr(v_scroll, start_attr, start)
            setattr(v_scroll, end_attr, end)
            v_scroll._update()

    @property
    def master(self) -> Scene | Window:
        return self.__master
