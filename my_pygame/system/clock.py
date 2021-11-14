# -*- coding: Utf-8 -*

__all__ = ["Clock"]

from time import time_ns


class Clock:

    __slots__ = ("__time", "__last_tick")

    def __init__(self, /, start: bool = False) -> None:
        self.__time: float = 0
        self.__last_tick: int = 0
        if start:
            self.__last_tick = time_ns()

    def get_elapsed_time(self, /) -> float:
        last_tick: int = self.__last_tick
        now: int = time_ns()
        if last_tick:
            self.__time += now - last_tick
        self.__last_tick = now
        return self.__time / 1000000.0

    def elapsed_time(self, /, milliseconds: float, restart: bool = True) -> bool:
        if self.get_elapsed_time() >= milliseconds:
            if restart:
                self.__time = 0
            return True
        return False

    def restart(self, /, reset: bool = True) -> None:
        self.__last_tick = time_ns()
        if reset:
            self.__time = 0
