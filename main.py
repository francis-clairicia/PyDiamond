#!/usr/bin/env python3
# -*- coding: Utf-8 -*

from pygame.math import Vector2
from my_pygame.window import Window
from my_pygame.scene import Scene

# from my_pygame.shape import RectangleShape, PolygonShape, CircleShape, CrossShape
from my_pygame.shape import RectangleShape, PolygonShape, CircleShape, CrossShape, Shape
from my_pygame.sprite import Sprite
from my_pygame.colors import WHITE, RED
from my_pygame.clock import Clock


class ShapeScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        # self.__r: RectangleShape = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        # self.__p: PolygonShape = PolygonShape(WHITE, outline=3, outline_color=RED)
        # self.__c: CircleShape = CircleShape(30, WHITE, outline=3, outline_color=RED)
        # self.__x: CrossShape = CrossShape(*self.__r.get_local_size(), outline_color=RED, outline=20)
        Shape.set_default_theme("default")
        Shape.set_theme("default", {"outline_color": RED, "outline": 3})
        self.__r: RectangleShape = RectangleShape(50, 50, WHITE)
        self.__p: PolygonShape = PolygonShape(WHITE)
        self.__c: CircleShape = CircleShape(30, WHITE)
        self.__x: CrossShape = CrossShape(*self.__r.get_local_size(), outline_color=RED, outline=20)
        self.__s: Sprite = Sprite()
        self.__p.points = [
            Vector2(20, 0),
            Vector2(40, 0),
            Vector2(40, 20),
            Vector2(60, 20),
            Vector2(60, 40),
            Vector2(40, 40),
            Vector2(40, 60),
            Vector2(20, 60),
            Vector2(20, 40),
            Vector2(0, 40),
            Vector2(0, 20),
            Vector2(20, 20),
        ]
        # self.__r.center = window.center
        self.__r.set_position(center=window.center)
        self.__p.center = self.__r.centerx - window.centery / 4, window.centery
        self.__x.center = self.__r.centerx - window.centery / 2, window.centery
        self.__c.center = self.__r.centerx - window.centery * 3 / 4, window.centery
        self.__clock: Clock = Clock()
        self.__scale: float = 1
        self.__scale_growth: int = 1
        self.__s.center = window.width * 3 / 4, 100
        # self.__r.hide()
        # self.window.after(3000, self.window.close)

    def update(self) -> None:
        degrees: float = 1
        if self.__clock.elapsed_time(20):
            self.__r.rotate(degrees)
            self.__p.rotate(-degrees, point=self.__r.center)
            self.__p.rotate(degrees * 3)
            self.__x.rotate(degrees, point=self.__r.center)
            self.__x.rotate(-degrees * 3)
            self.__c.rotate(-degrees, point=self.__r.center)
            self.__scale += 0.02 * self.__scale_growth
            if self.__scale >= 2:
                self.__scale_growth = -1
            elif self.__scale <= 0.2:
                self.__scale_growth = 1
            # self.__r.scale = self.__scale
            self.__p.scale = self.__scale
            self.__x.scale = self.__scale
            self.__c.scale = self.__scale
            self.__s.scale = self.__scale

            self.__s.default_image = self.__r.to_surface()

    def draw(self) -> None:
        self.window.clear()
        self.window.draw(self.__r)
        self.window.draw(self.__p)
        self.window.draw(self.__x)
        self.window.draw(self.__c)
        self.window.draw(self.__s)


class AnimationScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.rectangle = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        self.rectangle.midleft = window.midleft
        self.rectangle.animation.register_position(center=window.center, speed=5.2)
        self.rectangle.animation.register_rotation(360, offset=2, point=window.center)
        self.rectangle.animation.register_rotation(-360, offset=2)
        self.rectangle.animation.start_in_background(self, after_animation=self.move_to_left)

    def draw(self) -> None:
        self.window.clear()
        self.window.draw(self.rectangle)

    def move_to_left(self) -> None:
        self.rectangle.animation.register_translation((-self.window.centerx / 2, -50), speed=5)
        self.rectangle.animation.start_in_background(self)


def main() -> None:
    w: Window = Window("my window")
    # w.scenes.push_on_top(ShapeScene(w))
    w.scenes.push_on_top(AnimationScene(w))
    w.mainloop()


if __name__ == "__main__":
    main()
