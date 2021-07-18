# -*- coding: Utf-8 -*

import pygame.time


class Clock:

    __slots__ = ("__time", "__clock")

    def __init__(self, start: bool = False) -> None:
        self.__time: float = 0
        self.__clock = pygame.time.Clock()
        if start:
            self.restart()

    def get_elapsed_time(self) -> float:
        self.__clock.tick()
        self.__time += self.__clock.get_time()
        return self.__time

    def elapsed_time(self, milliseconds: float, restart: bool = True) -> bool:
        if self.get_elapsed_time() >= milliseconds:
            if restart:
                self.restart()
            return True
        return False

    def restart(self, reset: bool = True) -> None:
        self.__clock.tick()
        if reset:
            self.__time = 0
