# -*- coding: Utf-8 -*

__all__ = ["Time"]

from pygame.time import get_ticks, wait, delay


class Time:
    @staticmethod
    def get_ticks() -> int:
        return get_ticks()

    @staticmethod
    def wait(milliseconds: float) -> float:
        return float(wait(round(milliseconds)))

    @staticmethod
    def delay(milliseconds: float) -> float:
        return float(delay(round(milliseconds)))
