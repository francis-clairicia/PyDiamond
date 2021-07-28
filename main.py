#!/usr/bin/env python3
# -*- coding: Utf-8 -*

from my_pygame.button import Button, ImageButton
from my_pygame.mouse import Mouse
from typing import List, Type
import pygame
from pygame.event import Event
from pygame.surface import Surface
from my_pygame.text import Text, TextImage
from my_pygame.window import Window
from my_pygame.scene import Scene, SceneEnum

from my_pygame.resource import FontLoader, ImageLoader, ResourceManager

from my_pygame.shape import RectangleShape, PolygonShape, CircleShape, CrossShape
from my_pygame.gradients import HorizontalGradientShape, RadialGradientShape, SquaredGradientShape, VerticalGradientShape
from my_pygame.sprite import AnimatedSprite, Sprite
from my_pygame.colors import BLUE_DARK, TRANSPARENT, WHITE, RED, YELLOW
from my_pygame.clock import Clock


class MyScenes(SceneEnum):
    Shape: str


class ShapeScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        # self.__r: RectangleShape = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        # self.__p: PolygonShape = PolygonShape(WHITE, outline=3, outline_color=RED)
        # self.__c: CircleShape = CircleShape(30, WHITE, outline=3, outline_color=RED)
        # self.__x: CrossShape = CrossShape(*self.__r.get_local_size(), outline_color=RED, outline=20)
        for cls in [RectangleShape, PolygonShape, CircleShape, CrossShape]:
            cls.set_default_theme("default")
            cls.set_theme("default", {"outline_color": RED, "outline": 3})
        self.__r: RectangleShape = RectangleShape(50, 50, WHITE)
        self.__p: PolygonShape = PolygonShape(WHITE)
        self.__c: CircleShape = CircleShape(30, WHITE, outline=4)
        self.__x: CrossShape = CrossShape(
            50,
            50,
            type="diagonal",
            color=RED,
            outline_color=WHITE,
        )
        self.__s: Sprite = Sprite()
        self.__p.set_points(
            [
                (20, 0),
                (40, 0),
                (40, 20),
                (60, 20),
                (60, 40),
                (40, 40),
                (40, 60),
                (20, 60),
                (20, 40),
                (0, 40),
                (0, 20),
                (20, 20),
            ]
        )
        self.__shape_copy: PolygonShape = PolygonShape(TRANSPARENT, outline_color=WHITE)
        self.__r.center = window.center
        self.__r.set_position(center=window.center)
        self.__p.center = self.__r.centerx - window.centery / 4, window.centery
        self.__x.center = self.__r.centerx - window.centery / 2, window.centery
        # self.__x.topleft = (50, 50)
        self.__c.center = self.__r.centerx - window.centery * 3 / 4, window.centery

        self.__x_trajectory: CircleShape = CircleShape(
            abs(self.__x.centerx - self.__r.centerx), TRANSPARENT, outline_color=YELLOW, outline=1
        )
        self.__x_trajectory.center = self.__r.center
        self.__x_center: CircleShape = CircleShape(5, YELLOW, outline=0)

        self.__c_trajectory: CircleShape = CircleShape(
            abs(self.__c.centerx - self.__r.centerx), TRANSPARENT, outline_color=YELLOW, outline=2
        )
        self.__c_trajectory.center = self.__r.center
        self.__c_center: CircleShape = CircleShape(5, YELLOW, outline=0)

        self.__clock: Clock = Clock()
        self.__scale: float = 1
        self.__scale_growth: int = 1
        self.__s.center = window.width * 3 / 4, 100
        self.__shape_copy.center = window.width / 4, window.height * 3 / 4
        # self.__r.hide()
        # self.window.after(3000, self.window.close)

    def update(self) -> None:
        degrees: float = 1
        if self.__clock.elapsed_time(15):
            self.__r.rotate(degrees)
            self.__p.rotate(-degrees, pivot=self.__r.center)
            self.__p.rotate(degrees * 3)
            self.__x.rotate(degrees, pivot=self.__r.center)
            self.__x.rotate(-degrees * 3)
            self.__c.rotate(-degrees, pivot=self.__r.center)
            # self.__scale += 0.02 * self.__scale_growth
            # if self.__scale >= 2:
            #     self.__scale_growth = -1
            # elif self.__scale <= 0.2:
            #     self.__scale_growth = 1
            # # self.__r.scale = self.__scale
            # self.__p.scale = self.__scale
            # self.__x.scale = self.__scale
            # self.__c.scale = self.__scale
            # self.__s.scale = self.__scale
        self.__x_center.center = self.__x.center
        self.__c_center.center = self.__c.center
        self.__s.default_image = self.__r.to_surface()
        self.__shape_copy.set_points(self.__c.get_vertices())

    def draw(self) -> None:
        self.window.draw(self.__r)
        self.window.draw(self.__p)
        self.window.draw(self.__c)
        self.window.draw(self.__c_center)
        self.window.draw(self.__c_trajectory)
        self.window.draw(self.__s)
        self.window.draw(self.__x)
        self.window.draw(self.__shape_copy)
        self.window.draw(self.__x_center)
        self.window.draw(self.__x_trajectory)


class AnimationScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.rectangle = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)

    def on_start_loop(self) -> None:
        window: Window = self.window
        self.rectangle.angle = 0
        self.rectangle.scale = 1
        self.rectangle.midleft = window.midleft
        self.rectangle.animation.register_position(center=window.center, speed=3.7)
        self.rectangle.animation.register_rotation(360, offset=2, pivot=window.center)
        self.rectangle.animation.register_rotation(360, offset=2)
        self.rectangle.animation.start_in_background(self, after_animation=self.move_to_left)

    def draw(self) -> None:
        self.window.draw(self.rectangle)

    def move_to_left(self) -> None:
        self.rectangle.animation.register_rotation_set(270, offset=5)
        self.rectangle.animation.register_translation((-self.window.centerx / 2, -50), speed=5)
        self.rectangle.animation.register_width_set(100)
        self.rectangle.animation.start(self)


class GradientScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        self.horizontal: HorizontalGradientShape = HorizontalGradientShape(100, 100, RED, YELLOW)
        self.vertical: VerticalGradientShape = VerticalGradientShape(100, 100, RED, YELLOW)
        self.squared: SquaredGradientShape = SquaredGradientShape(100, RED, YELLOW)
        self.radial: RadialGradientShape = RadialGradientShape(50, RED, YELLOW)

    def update(self) -> None:
        self.horizontal.midleft = self.window.midleft
        self.vertical.midright = self.window.midright
        self.radial.center = self.window.center
        self.squared.midbottom = self.window.midbottom

    def draw(self) -> None:
        for obj in [self.horizontal, self.vertical, self.squared, self.radial]:
            self.window.draw(obj)


class TextScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        self.text = Text(
            "I'm a text", font=(None, 300), italic=True, color=WHITE, shadow_x=-25, shadow_y=-25, wrap=5, justify="center"
        )

    def on_start_loop(self) -> None:
        self.text.angle = 0
        self.text.center = self.window.center
        self.text.animation.register_rotation(360).start_in_background(self)

    def draw(self) -> None:
        self.window.draw(self.text)


class MyResources(ResourceManager):
    cactus: Surface
    cooperblack: str
    car: List[Surface]
    cross: Surface
    cross_hover: Surface
    __resources_files__ = {
        "cactus": {"path": "./files/img/cactus.png", "loader": ImageLoader},
        "cooperblack": {"path": "./files/fonts/COOPBL.ttf", "loader": FontLoader},
        "car": {
            "path": [f"./files/img/gameplay/voiture_7/{i + 1}.png" for i in range(10)],
            "loader": ImageLoader,
        },
        "cross": {"path": "./files/img/croix_rouge.png", "loader": ImageLoader},
        "cross_hover": {"path": "./files/img/croix_rouge_over.png", "loader": ImageLoader},
    }


class ResourceScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.cactus = Sprite(image=MyResources.cactus)
        self.cactus.size = 100, 100
        self.cactus.topleft = 20, 20
        self.text = Text("I'm a text", font=(MyResources.cooperblack, 300), italic=True, color=WHITE, wrap=5, justify="center")
        self.text.center = window.center

    def draw(self) -> None:
        self.window.draw(self.cactus)
        self.window.draw(self.text)


class AnimatedSpriteScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        self.sprite: AnimatedSprite = AnimatedSprite(*MyResources.car)
        self.sprite.start_sprite_animation(loop=True)
        self.sprite.ratio = 20

    def on_start_loop(self) -> None:
        self.sprite.angle = 0
        self.sprite.center = self.window.center
        self.sprite.animation.register_rotation(360, offset=2).start_in_background(self)

    def update(self) -> None:
        self.sprite.update()

    def draw(self) -> None:
        self.window.draw(self.sprite)


class EventScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        self.cross: CrossShape = CrossShape(50, 50, type="diagonal", color=RED, outline_color=WHITE, outline=3)
        self.circle: CircleShape = CircleShape(4, color=YELLOW)
        self.bind_mouse_position(lambda pos: self.cross.set_position(center=pos))
        self.bind_mouse_button(Mouse.LEFT, self.__switch_color)

    def on_start_loop(self) -> None:
        Mouse.hide_cursor()

    def on_quit(self) -> None:
        Mouse.show_cursor()

    def update(self) -> None:
        self.circle.center = self.cross.center

    def draw(self) -> None:
        self.window.draw(self.cross)
        self.window.draw(self.circle)

    def __switch_color(self, event: Event) -> None:
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.cross.color = YELLOW
        elif event.type == pygame.MOUSEBUTTONUP:
            self.cross.color = RED


class TextImageScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        self.text: TextImage = TextImage("I'm a text", font=(None, 50), color=WHITE, shadow_x=-5, shadow_y=-5, wrap=5)
        self.text.img = MyResources.cactus
        self.text.img_scale_to_size((100, 100))
        self.text.center = window.center

    def on_start_loop(self) -> None:
        self.text.angle = 0
        self.text.scale = 1
        self.text.animation.register_rotation(360).register_width_offset(100).start_in_background(self)

    def draw(self) -> None:
        self.window.draw(self.text)


class ButtonScene(Scene):
    def __init__(self, window: Window) -> None:
        super().__init__(window, framerate=120)
        self.background_color = BLUE_DARK
        self.button = Button(self, font=(None, 80), img=MyResources.cactus, callback=self.__increase_counter, text_offset=(2, 2))
        self.button.img_scale_to_size((100, 100))
        self.button.center = window.center

        self.cancel = ImageButton(self, img=MyResources.cross, active_img=MyResources.cross_hover, callback=self.__reset)
        self.cancel.center = window.center
        self.cancel.move(450, 0)

    def on_start_loop(self) -> None:
        self.__reset()

    def __reset(self) -> None:
        self.counter = 0
        self.button.text = "0"
        self.button.scale = 1
        self.button.animation.register_width_offset(100).start_in_background(self)

    def __increase_counter(self) -> None:
        self.counter += 1
        self.button.text = str(self.counter)

    def draw(self) -> None:
        self.window.draw(self.button)
        self.window.draw(self.cancel)


class MainWindow(Window):

    __SCENES: List[Type[Scene]] = [
        ShapeScene,
        AnimationScene,
        GradientScene,
        TextScene,
        ResourceScene,
        AnimatedSpriteScene,
        EventScene,
        TextImageScene,
        ButtonScene,
    ]

    def __init__(self) -> None:
        # super().__init__("my window", (0, 0))
        super().__init__("my window", (1366, 768))
        self.text_framerate.show()
        self.all_scenes: List[Scene] = []
        for cls in MainWindow.__SCENES:
            cls.set_theme_namespace(cls.__name__)
            self.all_scenes.append(cls(self))

        Button.set_default_theme("default")
        Button.set_theme("default", {"font": (MyResources.cooperblack, 20), "border_radius": 5})

        self.index: int = 0
        self.all_scenes[0].start()
        self.prev_button: Button = Button(self, "Previous", callback=self.__previous_scene)
        self.prev_button.topleft = self.left + 10, self.top + 10
        self.next_button: Button = Button(self, "Next", callback=self.__next_scene)
        self.next_button.topright = self.right - 10, self.top + 10

    def draw_screen(self) -> None:
        super().draw_screen()
        self.draw(self.prev_button)
        self.draw(self.next_button)

    def __next_scene(self) -> None:
        self.all_scenes[self.index].stop()
        self.index = (self.index + 1) % len(self.all_scenes)
        self.all_scenes[self.index].start()

    def __previous_scene(self) -> None:
        self.all_scenes[self.index].stop()
        self.index = len(self.all_scenes) - 1 if self.index == 0 else self.index - 1
        self.all_scenes[self.index].start()


def main() -> None:
    w: Window = MainWindow()
    w.mainloop()


if __name__ == "__main__":
    main()
