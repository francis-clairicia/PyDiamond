# -*- coding: Utf-8 -*

__all__ = ["Time"]

import pygame.time
from time import time_ns
from typing import ClassVar


class Time:
    __start: ClassVar[int] = time_ns()
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
        return float(pygame.time.wait(round(milliseconds)))

    @staticmethod
    def delay(milliseconds: float) -> float:
        return float(pygame.time.delay(round(milliseconds)))
