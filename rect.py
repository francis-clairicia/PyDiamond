#!/usr/bin/env python3
# -*- coding: Utf-8 -*

from typing import Optional, Tuple, Union, overload
import pygame
import pygame.display
import pygame.event
import pygame.draw

from pygame.surface import Surface
from pygame.rect import Rect
from pygame.time import Clock


@overload
def add(a: int, b: int) -> int:
    ...


@overload
def add(a: Tuple[int, ...]) -> int:
    ...


def add(a: Union[int, Tuple[int, ...]], b: Optional[int] = None) -> int:
    if isinstance(a, tuple):
        return sum(a)
    if isinstance(a, int) and b is not None:
        return a + b
    raise TypeError("Bad arguments")


def main() -> None:
    if pygame.init()[1] > 0:
        raise pygame.error("Error on initialization")

    screen: Surface = pygame.display.set_mode((800, 600))

    rect: Rect = Rect(0, 0, 50, 50)

    done = False
    clock: Clock = Clock()
    x: float = rect.x
    y: float = rect.y
    while not done:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                done = True
                break
        if done:
            break
        x += 0.5
        y += 0.5
        rect.topleft = int(x), int(y)
        screen.fill("black")
        pygame.draw.rect(screen, "white", rect)
        pygame.display.flip()
        clock.tick(60)

    pygame.quit()


if __name__ == "__main__":
    main()
