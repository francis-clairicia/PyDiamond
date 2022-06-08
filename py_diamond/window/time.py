# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's Time management module"""

from __future__ import annotations

__all__ = ["Time"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from time import monotonic_ns as time_ns
from typing import ClassVar, Final

from pygame.time import delay as _pg_time_delay, wait as _pg_time_wait

from ..system.namespace import ClassNamespace


class Time(ClassNamespace):
    __start: Final[int] = time_ns()
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
        return (time_ns() - Time.__start) / 1000000

    @staticmethod
    def wait(milliseconds: float) -> float:
        return float(_pg_time_wait(round(milliseconds)))

    @staticmethod
    def delay(milliseconds: float) -> float:
        return float(_pg_time_delay(round(milliseconds)))
