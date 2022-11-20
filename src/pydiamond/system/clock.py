# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Clock module"""

from __future__ import annotations

__all__ = ["Clock"]

import time
from typing import TYPE_CHECKING


class Clock:

    __slots__ = ("__time", "__last_tick")

    if TYPE_CHECKING:

        @staticmethod
        def get_time_ns() -> int:
            return time.perf_counter_ns()

    else:

        get_time_ns = staticmethod(time.perf_counter_ns)

    def __init__(self, start: bool = False) -> None:
        self.__time: float = 0
        self.__last_tick: int = 0
        if start:
            self.__last_tick = self.get_time_ns()

    def get_elapsed_time(self) -> float:
        now: int = self.get_time_ns()
        if last_tick := self.__last_tick:
            self.__time += (now - last_tick) / 1000000.0
        self.__last_tick = now
        return self.__time

    def elapsed_time(self, milliseconds: float, restart: bool = True) -> bool:
        if self.get_elapsed_time() >= milliseconds:
            if restart:
                self.__time = max(self.__time - milliseconds, 0)
            return True
        return False

    def restart(self, reset: bool = True) -> None:
        self.__last_tick = self.get_time_ns()
        if reset:
            self.__time = 0
