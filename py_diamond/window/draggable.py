# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Draggable objects module"""

from __future__ import annotations

__all__ = ["Draggable"]

from abc import abstractmethod
from typing import TYPE_CHECKING, Callable, Generic, Protocol, TypeVar
from weakref import ref

from ..system.utils.abc import concreteclass
from .clickable import Clickable

if TYPE_CHECKING:
    from ..audio.sound import Sound
    from ..graphics.rect import Rect
    from .cursor import AbstractCursor
    from .display import Window
    from .event import MouseMotionEvent
    from .scene import Scene


class SupportsDragging(Protocol):
    @property
    @abstractmethod
    def rect(self) -> Rect:
        raise NotImplementedError
    
    @abstractmethod
    def translate(self, __vector: tuple[int, int], /) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_shown(self) -> bool:
        raise NotImplementedError


_D = TypeVar("_D", bound=SupportsDragging)


@concreteclass
class Draggable(Clickable, Generic[_D]):
    def __init__(
        self,
        master: Scene | Window,
        target: _D,
        *,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: AbstractCursor | None = None,
        disabled_cursor: AbstractCursor | None = None,
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
        self.set_active_only_on_hover(False)

        self.__target: Callable[[], _D | None]
        if target is self:  # type: ignore[comparison-overlap]  # noqa: I decide it is possible
            self.__target = ref(target)
        else:
            assert target is not None, "hey man, why None ?"
            self.__target = lambda: target

    def is_shown(self) -> bool:
        return True

    def invoke(self) -> None:
        pass

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.target.rect.collidepoint(mouse_pos)

    def _on_mouse_motion(self, event: MouseMotionEvent) -> None:
        if self.active:
            self.target.translate(event.rel)
        return super()._on_mouse_motion(event)

    @property
    def target(self) -> _D:
        target = self.__target()
        if target is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        return target
