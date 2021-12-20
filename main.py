#!/usr/bin/env python3
# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, Callable, List, Literal, Optional, Tuple, Type
from py_diamond.graphics.button import Button, ImageButton
from py_diamond.graphics.checkbox import CheckBox
from py_diamond.graphics.color import (
    BLACK,
    BLUE,
    BLUE_DARK,
    BLUE_LIGHT,
    CYAN,
    GREEN,
    MAGENTA,
    ORANGE,
    PURPLE,
    RED,
    TRANSPARENT,
    WHITE,
    YELLOW,
    set_brightness,
    set_color_alpha,
)
from py_diamond.graphics.entry import Entry
from py_diamond.graphics.gradients import (
    HorizontalGradientShape,
    RadialGradientShape,
    SquaredGradientShape,
    VerticalGradientShape,
)
from py_diamond.graphics.image import Image
from py_diamond.graphics.progress import ProgressBar
from py_diamond.graphics.renderer import Renderer, SurfaceRenderer
from py_diamond.graphics.scale import Scale
from py_diamond.graphics.shape import AbstractRectangleShape, CircleShape, CrossShape, PolygonShape, RectangleShape
from py_diamond.graphics.sprite import AnimatedSprite, Sprite
from py_diamond.graphics.surface import Surface
from py_diamond.graphics.text import Text, TextImage
from py_diamond.resource.loader import FontLoader, ImageLoader
from py_diamond.resource.manager import ResourceManager
from py_diamond.system.configuration import initializer
from py_diamond.system.time import Time
from py_diamond.window.display import Window
from py_diamond.window.event import Event, MouseButtonEvent
from py_diamond.window.mouse import Mouse
from py_diamond.window.scene import MainScene, Scene, SceneTransition, SceneTransitionCoroutine, SceneWindow


class ShapeScene(MainScene, busy_loop=True):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
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
        self.__r.center = self.window.center
        self.__r.set_position(center=self.window.center)
        self.__p.center = self.__r.centerx - self.window.centery / 4, self.window.centery
        self.__x.center = self.__r.centerx - self.window.centery / 2, self.window.centery
        # self.__x.topleft = (50, 50)
        self.__c.center = self.__r.centerx - self.window.centery * 3 / 4, self.window.centery

        self.__x_trajectory: CircleShape = CircleShape(
            abs(self.__x.centerx - self.__r.centerx), TRANSPARENT, outline_color=YELLOW, outline=1
        )
        self.__x_trajectory.center = self.__r.center
        self.__x_center: CircleShape = CircleShape(5, YELLOW, outline=0)
        self.__x_center.center = self.__x.center

        self.__c_trajectory: CircleShape = CircleShape(
            abs(self.__c.centerx - self.__r.centerx), TRANSPARENT, outline_color=YELLOW, outline=2
        )
        self.__c_trajectory.center = self.__r.center
        self.__c_center: CircleShape = CircleShape(5, YELLOW, outline=0)
        self.__c_center.center = self.__c.center

        self.__scale: float = 1
        self.__scale_growth: int = 1
        self.__shape_copy.center = self.window.width / 4, self.window.height * 3 / 4
        # self.__r.hide()
        # self.window.after(3000, self.window.close)

    def fixed_update(self) -> None:
        degrees: float = 30 * Time.fixed_delta()

        self.__r.rotate(degrees)
        self.__p.rotate_around_point(-degrees, pivot=self.__r.center)
        self.__p.rotate(degrees * 3)
        self.__x.rotate_around_point(degrees, pivot=self.__r.center)
        self.__x.rotate(-degrees * 3)
        self.__c.rotate_around_point(-degrees, pivot=self.__r.center)
        # self.__scale += 0.02 * self.__scale_growth
        # if self.__scale >= 2:
        #     self.__scale_growth = -1
        # elif self.__scale <= 0.2:
        #     self.__scale_growth = 1
        # # self.__r.scale = self.__scale
        # self.__p.scale = self.__scale
        # self.__x.scale = self.__scale
        # self.__c.scale = self.__scale
        self.__x_center.center = self.__x.center
        self.__c_center.center = self.__c.center
        # self.__shape_copy.set_points(self.__c.get_vertices())

    def render(self) -> None:
        self.window.draw(
            self.__r,
            self.__p,
            self.__c,
            self.__c_center,
            self.__c_trajectory,
            self.__x,
            # self.__shape_copy,
            self.__x_center,
            self.__x_trajectory,
        )


class AnimationScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.rectangle = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        self.animation = self.rectangle.animation

    def on_start_loop_before_transition(self) -> None:
        window: Window = self.window
        self.rectangle.angle = 0
        self.rectangle.scale = 1
        self.rectangle.midleft = window.midleft
        self.animation.smooth_set_position(center=window.center, speed=370)
        self.animation.smooth_rotation_around_point(360, window.center, speed=200)
        self.animation.smooth_rotation(360 * 2, speed=410)
        self.animation.on_stop(self.move_to_left)

    def fixed_update(self, /) -> None:
        self.animation.fixed_update(use_of_linear_interpolation=True)

    def update_alpha(self, /, interpolation: float) -> None:
        self.animation.set_interpolation(interpolation)

    def render(self) -> None:
        self.window.draw(self.rectangle)

    def move_to_left(self) -> None:
        self.animation.smooth_set_angle(270, speed=500)
        self.animation.smooth_translation((-self.window.centerx / 2, -50), speed=500)
        self.animation.smooth_scale_to_width(100)
        self.animation.wait_until_finish(self)


class GradientScene(Scene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.horizontal: HorizontalGradientShape = HorizontalGradientShape(100, 100, RED, YELLOW)
        self.vertical: VerticalGradientShape = VerticalGradientShape(100, 100, RED, YELLOW)
        self.squared: SquaredGradientShape = SquaredGradientShape(100, RED, YELLOW)
        self.radial: RadialGradientShape = RadialGradientShape(50, RED, YELLOW)

    def on_start_loop_before_transition(self) -> None:
        self.horizontal.midleft = self.window.midleft
        self.vertical.midright = self.window.midright
        self.radial.center = self.window.center
        self.squared.midbottom = self.window.midbottom

    def render(self) -> None:
        self.window.draw(self.horizontal, self.vertical, self.squared, self.radial)


class Rainbow(AbstractRectangleShape):
    @initializer
    def __init__(self, width: float, height: float) -> None:
        super().__init__(width=width, height=height)
        self.__colors: List[HorizontalGradientShape] = [
            HorizontalGradientShape(0, 0, RED, ORANGE),
            HorizontalGradientShape(0, 0, ORANGE, YELLOW),
            HorizontalGradientShape(0, 0, YELLOW, GREEN),
            HorizontalGradientShape(0, 0, GREEN, CYAN),
            HorizontalGradientShape(0, 0, CYAN, BLUE),
            HorizontalGradientShape(0, 0, BLUE, MAGENTA),
            HorizontalGradientShape(0, 0, MAGENTA, PURPLE),
            HorizontalGradientShape(0, 0, PURPLE, RED),
        ]
        brightness: int = 75
        for shape in self.__colors:
            shape.first_color = set_brightness(shape.first_color, brightness)
            shape.second_color = set_brightness(shape.second_color, brightness)

    def _make(self) -> Surface:
        width, height = self.local_size
        gradient_width: float = round(width / len(self.__colors))
        gradient_height: float = height
        renderer: SurfaceRenderer = SurfaceRenderer((width, height))
        for i, gradient in enumerate(self.__colors):
            gradient.local_size = (gradient_width, gradient_height)
            gradient.topleft = (gradient_width * i, 0)
            gradient.draw_onto(renderer)
        return renderer.surface


class RainbowScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.rainbow = Rainbow(*self.window.size)

    def on_start_loop_before_transition(self) -> None:
        self.window.text_framerate.color = BLACK

    def on_quit(self) -> None:
        self.window.text_framerate.color = WHITE

    def render(self) -> None:
        self.window.draw(self.rainbow)


class TextScene(Scene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text = Text(
            "I'm a text", font=(None, 300), italic=True, color=WHITE, shadow_x=-25, shadow_y=-25, wrap=5, justify="center"
        )

    def on_start_loop_before_transition(self) -> None:
        self.text.angle = 0
        self.text.center = self.window.center

    def on_start_loop(self, /) -> None:
        self.text.animation.smooth_rotation(360, speed=5)

    def fixed_update(self, /) -> None:
        self.text.animation.fixed_update(use_of_linear_interpolation=True)

    def update_alpha(self, /, interpolation: float) -> None:
        self.text.animation.set_interpolation(interpolation)

    def render(self) -> None:
        self.window.draw(self.text)


class ImagesResources(ResourceManager):
    cactus: Surface
    car: Tuple[Surface, ...]
    cross: Surface
    cross_hover: Surface
    __resource_loader__ = ImageLoader
    __resources_directory__ = "./files/img"
    __resources_files__ = {
        "cactus": "cactus.png",
        "car": [f"gameplay/voiture_7/{i + 1}.png" for i in range(10)],
        "cross": "croix_rouge.png",
        "cross_hover": "croix_rouge_over.png",
    }


class FontResources(ResourceManager):
    cooperblack: str
    __resource_loader__ = FontLoader
    __resources_directory__ = "./files/fonts"
    __resources_files__ = {"cooperblack": "COOPBL.ttf"}


class ResourceScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.cactus = Sprite(image=ImagesResources.cactus)
        self.cactus.size = 100, 100
        self.cactus.topleft = 20, 20
        self.text = Text("I'm a text", font=(FontResources.cooperblack, 300), italic=True, color=WHITE, wrap=5, justify="center")
        self.text.center = self.window.center

    def render(self) -> None:
        self.window.draw(self.cactus, self.text)


class AnimatedSpriteScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.sprite: AnimatedSprite = AnimatedSprite(*ImagesResources.car)

    def on_start_loop_before_transition(self) -> None:
        self.sprite.angle = 0
        self.sprite.center = self.window.center

    def on_start_loop(self, /) -> None:
        self.sprite.ratio = 20
        self.sprite.start_sprite_animation(loop=True)
        self.sprite.animation.smooth_rotation(360, speed=200)

    def fixed_update(self) -> None:
        self.sprite.animation.fixed_update(use_of_linear_interpolation=True)
        self.sprite.update()

    def update_alpha(self, /, interpolation: float) -> None:
        self.sprite.animation.set_interpolation(interpolation)

    def render(self) -> None:
        self.window.draw(self.sprite)


class EventScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.cross: CrossShape = CrossShape(50, 50, type="diagonal", color=RED, outline_color=WHITE, outline=3)
        self.circle: CircleShape = CircleShape(4, color=YELLOW)
        self.event.bind_mouse_position(lambda pos: self.cross.set_position(center=pos))
        self.event.bind_mouse_button(Mouse.Button.LEFT, self.__switch_color)

    def on_start_loop(self) -> None:
        Mouse.hide_cursor()

    def on_quit(self) -> None:
        Mouse.show_cursor()

    def update(self) -> None:
        self.circle.center = self.cross.center

    def render(self) -> None:
        self.window.draw(self.cross, self.circle)

    def __switch_color(self, event: MouseButtonEvent) -> None:
        if event.type == Event.Type.MOUSEBUTTONDOWN:
            self.cross.color = YELLOW
        elif event.type == Event.Type.MOUSEBUTTONUP:
            self.cross.color = RED


class TextImageScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text: TextImage = TextImage(
            "I'm a text", img=ImagesResources.cactus, font=(None, 50), color=WHITE, shadow_x=-5, shadow_y=-5, wrap=5
        )
        self.text.img_scale_to_size((100, 100))
        self.text.center = self.window.center

    def on_start_loop_before_transition(self) -> None:
        self.text.angle = 0
        self.text.scale = 1

    def on_start_loop(self, /) -> None:
        self.text.animation.smooth_rotation(360)
        self.text.animation.smooth_width_growth(100)

    def fixed_update(self, /) -> None:
        self.text.animation.fixed_update(use_of_linear_interpolation=True)

    def update_alpha(self, /, interpolation: float) -> None:
        self.text.animation.set_interpolation(interpolation)

    def render(self) -> None:
        self.window.draw(self.text)


class ButtonScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.button = Button(
            self,
            font=(None, 80),
            img=ImagesResources.cactus,
            callback=self.__increase_counter,
            text_offset=(2, 2),
            text_hover_offset=(0, -3),
        )
        self.button.img_scale_to_size((100, 100))
        self.button.center = self.window.center

        def restart() -> None:
            self.on_start_loop_before_transition()
            self.on_start_loop()

        self.cancel = ImageButton(self, img=ImagesResources.cross, active_img=ImagesResources.cross_hover, callback=restart)
        self.cancel.center = self.window.center
        self.cancel.move(450, 0)

    def on_start_loop_before_transition(self) -> None:
        self.counter = 0
        self.button.text = "0"
        self.button.scale = 1
        self.button.angle = 0

    def on_start_loop(self, /) -> None:
        self.button.animation.smooth_width_growth(100)
        self.button.animation.smooth_rotation(390, speed=300)

    def fixed_update(self, /) -> None:
        self.button.animation.fixed_update(use_of_linear_interpolation=True)

    def update_alpha(self, /, interpolation: float) -> None:
        self.button.animation.set_interpolation(interpolation)

    def __increase_counter(self) -> None:
        self.counter += 1
        self.button.text = str(self.counter)

    def render(self) -> None:
        self.window.draw(self.button, self.cancel)


class CheckBoxScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text = Text(font=(FontResources.cooperblack, 40), color=WHITE, shadow_x=3, shadow_y=3)
        self.box: CheckBox[int, int] = CheckBox(
            self, 50, 50, BLUE_LIGHT, off_value=0, on_value=10, callback=self.__set_text, callback_at_init=False
        )

    def on_start_loop_before_transition(self) -> None:
        self.box.center = self.window.center
        self.box.value = self.box.off_value
        self.__set_text(self.box.value)

    def render(self) -> None:
        self.window.draw(self.box, self.text)

    def __set_text(self, value: int) -> None:
        self.text.message = f"Value: {value}"
        self.text.midtop = (self.box.centerx, self.box.bottom + 10)


class ProgressScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.progress = progress = ProgressBar(500, 75, from_=10, to=90)
        self.restart = restart = ImageButton(
            self,
            img=ImagesResources.cross,
            active_img=ImagesResources.cross_hover,
            callback=lambda: progress.config.set("percent", 0),
        )

        progress.show_label("Loading...", "top", font=(None, 60), color=WHITE)
        progress.show_percent("inside", font=(None, 60))
        progress.center = self.window.center
        restart.midtop = progress.centerx, progress.bottom + 20

    def on_start_loop_before_transition(self, /) -> None:
        self.progress.percent = 0

    def on_start_loop(self) -> None:
        self.callback = self.every(20, lambda: self.progress.config(value=self.progress.value + 1))

    def on_quit(self, /) -> None:
        self.callback.kill()

    def render(self) -> None:
        self.window.draw(self.progress, self.restart)


class ScaleScene(MainScene):
    def awake(self, /, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text = text = Text(font=(FontResources.cooperblack, 40), color=WHITE, shadow_x=3, shadow_y=3)
        self.scale = scale = Scale(
            self, 500, 75, from_=10, to=90, value_callback=lambda value: self.text.config(message=f"Value: {value:.2f}")
        )

        scale.center = self.window.center
        text.midtop = scale.centerx, scale.bottom + 20

    def on_start_loop_before_transition(self) -> None:
        self.scale.value = self.scale.from_value

    def render(self) -> None:
        self.window.draw(self.scale, self.text)


class EntryScene(MainScene):
    def awake(self, /, *args: Any, **kwargs: Any) -> None:
        super().awake(*args, **kwargs)
        self.background_color = BLUE_DARK
        self.entry = entry = Entry(self, font=(None, 70))
        entry.center = self.window.center

    def on_start_loop_before_transition(self) -> None:
        self.entry.clear()

    def render(self) -> None:
        self.window.draw(self.entry)


class SceneTransitionTranslation(SceneTransition):
    def __init__(self, /, side: Literal["left", "right"]) -> None:
        super().__init__()
        self.__side: Literal["left", "right"] = side

    def show_new_scene(
        self, /, target: Renderer, previous_scene_image: Surface, actual_scene_image: Surface
    ) -> SceneTransitionCoroutine:
        previous_scene = Image(previous_scene_image)
        actual_scene = Image(actual_scene_image)
        target_rect = target.get_rect()
        previous_scene.center = actual_scene.center = target_rect.center
        previous_scene.fill(set_color_alpha(BLACK, 100))
        previous_scene_hidden: Callable[[], bool]
        if self.__side == "left":
            previous_scene.animation.infinite_translation((-1, 0), speed=3000)
            previous_scene_hidden = lambda: previous_scene.right >= target_rect.left
        else:
            previous_scene.animation.infinite_translation((1, 0), speed=3000)
            previous_scene_hidden = lambda: previous_scene.left <= target_rect.right
        while previous_scene_hidden():
            interpolation: Optional[float] = yield
            if interpolation is None:
                previous_scene.animation.fixed_update(use_of_linear_interpolation=True)
                continue
            previous_scene.animation.set_interpolation(interpolation)
            actual_scene.draw_onto(target)
            previous_scene.draw_onto(target)


class MainWindow(SceneWindow):

    all_scenes: List[Type[Scene]] = [
        ShapeScene,
        AnimationScene,
        GradientScene,
        RainbowScene,
        TextScene,
        ResourceScene,
        AnimatedSpriteScene,
        EventScene,
        TextImageScene,
        ButtonScene,
        CheckBoxScene,
        ProgressScene,
        ScaleScene,
        EntryScene,
    ]

    def __init__(self) -> None:
        # super().__init__("my window", (0, 0))
        super().__init__("my window", (1366, 768))

        # Text.set_default_font(FontResources.cooperblack)

        Button.set_default_theme("default")
        Button.set_theme("default", {"font": (FontResources.cooperblack, 20), "border_radius": 5})

    def __window_init__(self) -> None:
        super().__window_init__()
        self.text_framerate.show()
        self.set_default_framerate(120)
        self.set_default_fixed_framerate(100)
        self.index: int = 0
        self.prev_button: Button = Button(self, "Previous", callback=self.__previous_scene)
        self.next_button: Button = Button(self, "Next", callback=self.__next_scene)
        self.prev_button.topleft = self.left + 10, self.top + 10
        self.next_button.topright = self.right - 10, self.top + 10

    def __window_quit__(self, /) -> None:
        super().__window_quit__()
        del self.prev_button, self.next_button

    def mainloop(self) -> None:
        self.run(self.all_scenes[self.index])

    def render_scene(self) -> None:
        super().render_scene()
        self.draw(self.prev_button, self.next_button)

    def __next_scene(self) -> None:
        self.index = (self.index + 1) % len(self.all_scenes)
        self.start_scene(self.all_scenes[self.index], remove_actual=True, transition=SceneTransitionTranslation("left"))

    def __previous_scene(self) -> None:
        self.index = len(self.all_scenes) - 1 if self.index == 0 else self.index - 1
        self.start_scene(self.all_scenes[self.index], remove_actual=True, transition=SceneTransitionTranslation("right"))


def main() -> None:
    with MainWindow().open() as window:
        window.mainloop()


if __name__ == "__main__":
    main()
