# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Widget's Renderer view module"""

from __future__ import annotations

__all__ = ["WidgetRendererView"]

from typing import TYPE_CHECKING, ContextManager, final

from ...graphics.renderer import AbstractRenderer, RendererView
from ...math.rect import Rect

if TYPE_CHECKING:
    from pygame._common import _CanBeRect

    from .abc import AbstractWidget


@final
class WidgetRendererView(RendererView):
    __slots__ = ("__widget",)

    def __init__(self, widget: AbstractWidget, target: AbstractRenderer) -> None:
        self.__widget: AbstractWidget = widget
        super().__init__(target)

    def __clip_rect(self, rect: _CanBeRect | None) -> Rect:
        widget_clip = self.__widget.get_visible_rect()
        if rect is None:
            return widget_clip.copy()
        if not isinstance(rect, Rect):
            rect = Rect(*rect)
        return rect.clip(widget_clip)

    def using_clip(self, rect: _CanBeRect | None) -> ContextManager[None]:
        return super().using_clip(self.__clip_rect(rect))
