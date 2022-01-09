# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Clock module"""

__all__ = ["Clock"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from time import monotonic_ns as time_ns


class Clock:

    __slots__ = ("__time", "__last_tick")

    def __init__(self, start: bool = False) -> None:
        self.__time: float = 0
        self.__last_tick: int = 0
        if start:
            self.__last_tick = time_ns()

    def get_elapsed_time(self) -> float:
        last_tick: int = self.__last_tick
        now: int = time_ns()
        if last_tick:
            self.__time += (now - last_tick) / 1000000.0
        self.__last_tick = now
        return self.__time

    def elapsed_time(self, milliseconds: float, restart: bool = True) -> bool:
        elapsed: float = self.get_elapsed_time()
        if elapsed >= milliseconds:
            if restart:
                self.__time = max(self.__time - milliseconds, 0)
            return True
        return False

    def restart(self, reset: bool = True) -> None:
        self.__last_tick = time_ns()
        if reset:
            self.__time = 0
