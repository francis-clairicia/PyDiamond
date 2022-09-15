# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Draggable objects module"""

from __future__ import annotations

__all__ = ["Draggable", "DraggingContainer"]

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Protocol, TypeVar

from ..system.utils.abc import concreteclass
from .clickable import Clickable

if TYPE_CHECKING:
    from ..audio.sound import Sound
    from ..graphics.rect import Rect
    from .cursor import Cursor
    from .display import Window
    from .event import MouseMotionEvent
    from .scene import Scene


class Draggable(Clickable):
    def __init__(
        self,
        master: Clickable | Scene | Window,
        *,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master=master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            **kwargs,
        )
        self.set_active_only_on_hover(False)

    @abstractmethod
    def translate(self, __vector: tuple[int, int], /) -> None:
        raise NotImplementedError

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        if self.active:
            self.translate(event.rel)
        return super()._on_mouse_motion(event)


class SupportsDragging(Protocol):
    @abstractmethod
    def get_rect(self) -> Rect:
        raise NotImplementedError

    @abstractmethod
    def translate(self, __vector: tuple[int, int], /) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_shown(self) -> bool:
        raise NotImplementedError


_D = TypeVar("_D", bound=SupportsDragging)


@concreteclass
class DraggingContainer(Draggable, Generic[_D]):
    def __init__(
        self,
        master: Clickable | Scene | Window,
        target: _D,
        *,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
    ) -> None:
        super().__init__(
            master,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
        )

        self.__target: _D = target

    def is_shown(self) -> bool:
        return self.target.is_shown()

    def invoke(self) -> None:
        pass

    def translate(self, __vector: tuple[int, int], /) -> None:
        return self.target.translate(__vector)

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.target.get_rect().collidepoint(mouse_pos)

    @property
    def target(self) -> _D:
        return self.__target
