# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's Time management module"""

from __future__ import annotations

__all__ = ["Time"]


from typing import ClassVar, Final

import pygame.time as _pg_time

from .clock import Clock
from .namespace import ClassNamespace


class Time(ClassNamespace):
    __start: Final[int] = Clock.get_time_ns()
    __delta: ClassVar[float] = 1
    __fixed_delta: ClassVar[float] = 1

    @staticmethod
    def delta() -> float:
        return Time.__delta

    @staticmethod
    def fixed_delta() -> float:
        return Time.__fixed_delta

    @staticmethod
    def get_ticks() -> float:
        return (Clock.get_time_ns() - Time.__start) / 1000000

    @staticmethod
    def wait(milliseconds: float) -> int | float:
        return _pg_time.wait(round(milliseconds))

    @staticmethod
    def delay(milliseconds: float) -> int | float:
        return _pg_time.delay(round(milliseconds))
