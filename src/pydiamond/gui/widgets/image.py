# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2023, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Image module"""

from __future__ import annotations

__all__ = ["Image"]

from typing import TYPE_CHECKING, Any, Literal

from ...graphics.image import Image as _Image
from .abc import Widget

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...graphics.surface import Surface
    from ...window.cursor import Cursor
    from .abc import AbstractWidget, WidgetsManager


class Image(Widget, _Image):
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        image: Surface | None = None,
        *,
        width: float | None = None,
        height: float | None = None,
        copy: bool = True,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        take_focus: bool | Literal["never"] = False,
        focus_on_hover: bool | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master=master,
            image=image,
            width=width,
            height=height,
            copy=copy,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            take_focus=take_focus,
            focus_on_hover=focus_on_hover,
            **kwargs,
        )

    def invoke(self) -> None:
        pass
