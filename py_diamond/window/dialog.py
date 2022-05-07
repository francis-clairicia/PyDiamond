# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Scene module"""

from __future__ import annotations

__all__ = [
    "Dialog",
    # "PopUpDialog",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

# from typing import Any

# from ..graphics.color import Color
# from ..system.utils import valid_optional_float
# from .event import WindowSizeChangedEvent
from .scene import Dialog  # , SceneWindow

# class PopUpDialog(Dialog):
#     def __init__(self) -> None:
#         super().__init__()
#         self.event.bind(WindowSizeChangedEvent, self.__handle_resize_event)

#     def awake(
#         self,
#         *,
#         width_ratio: float | None = None,
#         height_ratio: float | None = None,
#         width: float | None = None,
#         height: float | None = None,
#         bg_color: Color = Color("white"),
#         outline: int = 3,
#         outline_color: Color = Color("black"),
#         **kwargs: Any,
#     ) -> None:
#         super().awake(**kwargs)
#         window: SceneWindow = self.window
#         width_ratio = valid_optional_float(value=width_ratio, min_value=0, max_value=1)
#         height_ratio = valid_optional_float(value=height_ratio, min_value=0, max_value=1)
#         width = valid_optional_float(value=width, min_value=0)
#         height = valid_optional_float(value=height, min_value=0)
#         if width is not None and width_ratio is not None:
#             raise ValueError("Must be either 'width' or 'width_ratio', not both")
#         if height is not None and height_ratio is not None:
#             raise ValueError("Must be either 'height' or 'height_ratio', not both")

#         if width_ratio is None:
#             width_ratio = 0.5
#         if height_ratio is None:
#             height_ratio = 0.5

#         self.__width_ratio: float | None = width_ratio if width is None else None
#         self.__height_ratio: float | None = height_ratio if height is None else None

#         if width is None:
#             width = window.width * width_ratio
#         if height is None:
#             height = window.height * height_ratio

#     def __handle_resize_event(self, event: WindowSizeChangedEvent) -> None:
#         pass
