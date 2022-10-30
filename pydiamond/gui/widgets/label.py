# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Label module"""

from __future__ import annotations

__all__ = ["Label"]

from typing import TYPE_CHECKING, Any, Literal

from ...graphics.color import BLACK
from ...graphics.text import TextImage as _TextImage
from .abc import Widget

if TYPE_CHECKING:
    from ...audio.sound import Sound
    from ...graphics.color import Color
    from ...graphics.font import _TextFont
    from ...graphics.surface import Surface
    from ...system.theme import ThemeType
    from ...window.cursor import Cursor
    from .abc import AbstractWidget, WidgetsManager


class Label(Widget, _TextImage):
    def __init__(
        self,
        master: AbstractWidget | WidgetsManager,
        message: str = "",
        *,
        img: Surface | None = None,
        compound: str = "left",
        distance: float = 5,
        font: _TextFont | None = None,
        bold: bool | None = None,
        italic: bool | None = None,
        underline: bool | None = None,
        color: Color = BLACK,
        wrap: int = 0,
        justify: str = "left",
        line_spacing: float = 0,
        shadow_x: float = 0,
        shadow_y: float = 0,
        shadow_color: Color = BLACK,
        state: str = "normal",
        hover_sound: Sound | None = None,
        click_sound: Sound | None = None,
        disabled_sound: Sound | None = None,
        hover_cursor: Cursor | None = None,
        disabled_cursor: Cursor | None = None,
        take_focus: bool | Literal["never"] = False,
        focus_on_hover: bool | None = None,
        theme: ThemeType | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            master=master,
            message=message,
            img=img,
            compound=compound,
            distance=distance,
            font=font,
            bold=bold,
            italic=italic,
            underline=underline,
            color=color,
            wrap=wrap,
            justify=justify,
            line_spacing=line_spacing,
            shadow_x=shadow_x,
            shadow_y=shadow_y,
            shadow_color=shadow_color,
            state=state,
            hover_sound=hover_sound,
            click_sound=click_sound,
            disabled_sound=disabled_sound,
            hover_cursor=hover_cursor,
            disabled_cursor=disabled_cursor,
            take_focus=take_focus,
            focus_on_hover=focus_on_hover,
            theme=theme,
            **kwargs,
        )

    def invoke(self) -> None:
        pass
