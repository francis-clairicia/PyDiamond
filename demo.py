#!/usr/bin/env -S python3 -W default
# -*- coding: Utf-8 -*-
# flake8: noqa

from __future__ import annotations

import gc
import weakref
from argparse import ArgumentParser
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Iterator, Literal, Mapping, Sequence

from py_diamond.audio.mixer import Mixer
from py_diamond.audio.music import Music, MusicStream
from py_diamond.audio.sound import Sound
from py_diamond.graphics.animation import AnimationInterpolatorPool, MoveAnimation, TransformAnimation
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
    Color,
)
from py_diamond.graphics.gradients import (
    HorizontalGradientShape,
    HorizontalMultiColorShape,
    MultiColorShape,
    RadialGradientShape,
    SquaredGradientShape,
    VerticalGradientShape,
    VerticalMultiColorShape,
)
from py_diamond.graphics.image import Image
from py_diamond.graphics.progress import ProgressBar
from py_diamond.graphics.shape import CircleShape, DiagonalCrossShape, PlusCrossShape, PolygonShape, RectangleShape
from py_diamond.graphics.sprite import AnimatedSprite, Sprite, SpriteGroup
from py_diamond.graphics.surface import Surface, SurfaceRenderer
from py_diamond.graphics.text import Text, TextImage
from py_diamond.gui.scene import GUIScene
from py_diamond.gui.widgets.abc import AbstractWidget
from py_diamond.gui.widgets.button import Button, ImageButton
from py_diamond.gui.widgets.checkbox import CheckBox
from py_diamond.gui.widgets.entry import Entry
from py_diamond.gui.widgets.form import Form
from py_diamond.gui.widgets.grid import Grid
from py_diamond.gui.widgets.scale import ScaleBar
from py_diamond.gui.widgets.scroll import ScrollArea, ScrollBar
from py_diamond.resource.loader import FontLoader, ImageLoader, MusicLoader, SoundLoader
from py_diamond.resource.manager import ResourceManager
from py_diamond.system.clock import Clock
from py_diamond.system.time import Time
from py_diamond.window.display import Window, WindowCallback
from py_diamond.window.draggable import Draggable
from py_diamond.window.event import (
    Event,
    KeyDownEvent,
    KeyUpEvent,
    MouseButtonDownEvent,
    MouseButtonEvent,
    MouseButtonUpEvent,
    MusicEndEvent,
    ScreenshotEvent,
)
from py_diamond.window.keyboard import Key, Keyboard
from py_diamond.window.mouse import Mouse, MouseButton
from py_diamond.window.scene import (
    AbstractAutoLayeredDrawableScene,
    MainScene,
    RenderedLayeredScene,
    Scene,
    SceneTransition,
    SceneWindow,
)
from py_diamond.window.scene.dialog import PopupDialog

if TYPE_CHECKING:
    from _typeshed import Self


class ShapeScene(MainScene, busy_loop=True):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.__r: RectangleShape = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        self.__p: PolygonShape = PolygonShape(WHITE, outline=3, outline_color=RED)
        self.__c: CircleShape = CircleShape(30, WHITE, outline=4, outline_color=RED)
        self.__x: DiagonalCrossShape = DiagonalCrossShape(
            50,
            50,
            color=RED,
            outline=3,
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
        self.__shape_copy: PolygonShape = PolygonShape(TRANSPARENT, outline_color=WHITE, outline=2)
        self.__r.center = self.window.center
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

        self.__interpolator_pool = AnimationInterpolatorPool(
            self.__r,
            self.__p,
            self.__x,
            self.__c,
        )

    def fixed_update(self) -> None:
        degrees: float = 30 * Time.fixed_delta()

        with self.__interpolator_pool.fixed_update():
            self.__r.rotate(degrees)
            self.__p.rotate_around_point(-degrees, pivot=self.__r.center)
            self.__p.rotate(degrees * 3)
            self.__x.rotate_around_point(degrees, pivot=self.__r.center)
            self.__x.rotate(-degrees * 3)
            self.__c.rotate_around_point(-degrees, pivot=self.__r.center)
            self.__scale += 1 * self.__scale_growth * Time.fixed_delta()
            if self.__scale >= 2:
                self.__scale_growth = -1
            elif self.__scale <= 0.2:
                self.__scale_growth = 1
            # self.__r.scale = self.__scale
            self.__p.scale = (self.__scale, self.__scale)
            self.__x.scale = (self.__scale, self.__scale)
            self.__c.scale = (self.__scale, self.__scale)

    def interpolation_update(self, interpolation: float) -> None:
        self.__interpolator_pool.update(interpolation)

    def update(self) -> None:
        self.__x_center.center = self.__x.center
        self.__c_center.center = self.__c.center
        self.__shape_copy.set_points(self.__c.get_edges())

    def render(self) -> None:
        self.window.draw(
            self.__c,
            self.__c_center,
            self.__c_trajectory,
            self.__x,
            self.__x_center,
            self.__x_trajectory,
            self.__p,
            self.__r,
            self.__shape_copy,
        )


class AnimationScene(MainScene, busy_loop=True):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.rectangle = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        self.animation = TransformAnimation(self.rectangle)
        self.event.bind_key_release(Key.K_RETURN, lambda _: self.__handle_return_event())

    def on_start_loop_before_transition(self) -> None:
        window: Window = self.window
        self.rectangle.angle = 0
        self.rectangle.scale = (1, 1)
        self.rectangle.midleft = window.midleft

    def on_start_loop(self) -> None:
        window: Window = self.window
        self.animation.clear()
        self.animation.smooth_set_position(center=window.center, speed=370)
        self.animation.smooth_rotation_around_point(360, window.center, speed=200)
        self.animation.smooth_rotation(360 * 2, speed=410)
        self.animation.on_stop(self.__move_to_left)
        self.animation.start()

    def fixed_update(self) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.animation.update(interpolation)

    def render(self) -> None:
        self.window.draw(self.rectangle)

    def __move_to_left(self) -> None:
        self.animation.smooth_set_angle(270, speed=500)
        self.animation.smooth_translation((-self.window.centerx / 2, -50), speed=500)
        self.animation.smooth_scale_to_width(100)
        self.animation.wait_until_finish(self)

    def __handle_return_event(self) -> None:
        self.on_start_loop_before_transition()
        self.on_start_loop()


class AnimationStateFullScene(MainScene, busy_loop=True):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.rectangle = RectangleShape(50, 50, WHITE, outline=3, outline_color=RED)
        self.text = Text(font=(FontResources.cooperblack, 25), italic=True, color=WHITE, justify="center")
        self.use_interpolation = False
        self.event.bind_key_press(Key.K_UP, self.__increase_fixed_framerate)
        self.event.bind_key_press(Key.K_DOWN, self.__increase_fixed_framerate)
        self.event.bind_key_press(Key.K_RETURN, lambda _: self.__toggle_interpolation_use())
        self.fixed_framerate = 30

    def on_start_loop_before_transition(self) -> None:
        window: Window = self.window
        self.rectangle.angle = 0
        self.rectangle.scale = (1, 1)
        self.rectangle.center = (window.centerx / 2, window.centery)

    def on_start_loop(self) -> None:
        window: Window = self.window
        self.animation = TransformAnimation(self.rectangle)
        self.animation.clear()
        self.animation.infinite_rotation(speed=410, counter_clockwise=False)
        self.animation.infinite_rotation_around_point(pivot=window.center, speed=50, counter_clockwise=False)
        self.animation.start()
        self.use_interpolation = True
        Keyboard.set_repeat(100, 100)

    def on_quit(self) -> None:
        Keyboard.set_repeat(None)

    def fixed_update(self) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        if self.use_interpolation:
            self.animation.update(interpolation)

    def update(self) -> None:
        self.text.message = "\n".join(
            [
                f"Animation interpolation: {'On' if self.use_interpolation else 'Off'}",
                "Press Enter to switch",
                f"Fixed framerate: {self.window.used_fixed_framerate()}fps",
                "- Key up: +1",
                "- Key down: -1",
            ]
        )
        self.text.center = self.window.center

    def render(self) -> None:
        self.window.draw(self.rectangle, self.text)

    def use_fixed_framerate(self) -> int:
        return self.fixed_framerate

    def __increase_fixed_framerate(self, event: KeyDownEvent) -> None:
        match event.key:
            case Key.K_UP if self.fixed_framerate < self.window.used_framerate():
                self.fixed_framerate += 1
            case Key.K_DOWN if self.fixed_framerate > 1:
                self.fixed_framerate -= 1

    def __toggle_interpolation_use(self) -> None:
        self.use_interpolation = not self.use_interpolation


class ShapeTransformTestScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.shape = DiagonalCrossShape(50, 50, color=RED, outline_color=WHITE, outline=2)
        # self.shape = RectangleShape(50, 50, color=RED, outline_color=WHITE, outline=2, border_radius=5)
        # self.shape = CircleShape(25, color=RED, outline_color=BLACK, outline=2, draw_bottom_left=False)
        # self.shape = CircleShape(25, color=RED, outline_color=BLACK, outline=2)

    def on_start_loop(self) -> None:
        window_size = self.window.size
        polygon = self.shape

        # @self.every(10)
        # def _() -> Iterator[None]:
        #     while polygon.get_height() < window_size[1]:
        #         polygon.local_width += 2
        #         polygon.local_height += 2
        #         yield

        @self.every(20)
        def _() -> Iterator[None]:
            while polygon.height < window_size[1]:
                polygon.scale_x += 0.02
                polygon.scale_y += 0.02
                yield
            for angle in range(360):
                polygon.angle = angle + 1
                yield

    def update(self) -> None:
        self.shape.center = self.window.center

    def render(self) -> None:
        self.window.draw(self.shape)


class GradientScene(Scene):
    def awake(self, **kwargs: Any) -> None:
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


RAINBOW_COLORS: Final[tuple[Color, ...]] = tuple(
    c.with_brightness(75) for c in (RED, ORANGE, YELLOW, GREEN, CYAN, BLUE, MAGENTA, PURPLE, RED)
)


class HorizontalRainbow(HorizontalMultiColorShape):
    def __init__(self, width: float, height: float) -> None:
        super().__init__(width, height, RAINBOW_COLORS)


class VerticalRainbow(VerticalMultiColorShape):
    def __init__(self, width: float, height: float) -> None:
        super().__init__(width, height, RAINBOW_COLORS)


class RainbowScene(MainScene):
    window: MainWindow

    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.all_rainbows: list[MultiColorShape] = [HorizontalRainbow(*self.window.size), VerticalRainbow(*self.window.size)]
        self.rainbow: int = 0

        def key_handler(event: KeyUpEvent) -> None:
            self.rainbow += {Key.K_UP: -1, Key.K_DOWN: 1}[Key(event.key)]
            self.rainbow %= len(self.all_rainbows)

        self.event.bind_key_release(Key.K_UP, key_handler)
        self.event.bind_key_release(Key.K_DOWN, key_handler)

    def on_start_loop_before_transition(self) -> None:
        self.window.text_framerate.color = BLACK

    def on_quit(self) -> None:
        self.window.text_framerate.color = WHITE

    def render(self) -> None:
        self.window.draw(self.all_rainbows[self.rainbow])


class TextScene(Scene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text = Text(
            "I'm a text", font=(None, 300), italic=True, color=WHITE, shadow_x=-25, shadow_y=-25, wrap=5, justify="center"
        )

    def on_start_loop_before_transition(self) -> None:
        self.text.angle = 0
        self.text.center = self.window.center

    def on_start_loop(self) -> None:
        self.animation = TransformAnimation(self.text)
        self.animation.clear()
        self.animation.smooth_rotation(360, speed=5)
        self.animation.start()

    def fixed_update(self) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.animation.update(interpolation)

    def render(self) -> None:
        self.window.draw(self.text)


class ImagesResources(ResourceManager):
    cactus: Surface
    car: Sequence[Surface]
    cross: Mapping[str, Surface]
    autumn_tree: Surface
    __resource_loader__ = ImageLoader
    __resources_directory__ = "./demo_resources/img"
    __resources_files__ = {
        "cactus": "cactus.png",
        "car": [f"gameplay/voiture_7/{i + 1}.png" for i in range(10)],
        "cross": {
            "normal": "croix_rouge.png",
            "hover": "croix_rouge_over.png",
        },
        "autumn_tree": "arbre_automne.png",
    }


class FontResources(ResourceManager):
    cooperblack: str
    __resource_loader__ = FontLoader
    __resources_directory__ = "./demo_resources/fonts"
    __resources_files__ = {"cooperblack": "COOPBL.ttf"}


class ResourceScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.cactus = Sprite(image=ImagesResources.cactus)
        self.cactus.center = self.window.center
        self.text = Text("I'm a text", font=(FontResources.cooperblack, 300), italic=True, color=WHITE, wrap=5, justify="center")
        self.text.center = self.window.center

    def render(self) -> None:
        self.window.draw(self.cactus, self.text)


class SpriteMaskScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.sprite = Sprite(ImagesResources.autumn_tree)
        self.mask = Image()

    def on_start_loop_before_transition(self) -> None:
        self.set_positions()
        return super().on_start_loop_before_transition()

    def on_start_loop(self) -> None:
        self.sprite.animation.clear()
        self.sprite.animation.smooth_rotation(360)
        self.sprite.animation.start()
        return super().on_start_loop()

    def fixed_update(self) -> None:
        self.sprite.fixed_update()
        super().fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.sprite.interpolation_update(interpolation)
        return super().interpolation_update(interpolation)

    def update(self) -> None:
        self.sprite.update()
        self.mask.set(self.sprite.mask.to_surface(), copy=False)
        self.set_positions()
        return super().update()

    def set_positions(self) -> None:
        self.sprite.center = self.window.width / 4, self.window.centery
        self.mask.center = self.window.width * 3 / 4, self.window.centery

    def render(self) -> None:
        self.window.draw(self.sprite, self.mask)


class AnimatedSpriteScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.sprite: AnimatedSprite = AnimatedSprite(*ImagesResources.car)

    def on_start_loop_before_transition(self) -> None:
        self.sprite.angle = 0
        self.sprite.center = self.window.center

    def on_start_loop(self) -> None:
        self.sprite.ratio = 20
        self.sprite.start_sprite_animation(loop=True)
        self.sprite.animation.clear()
        self.sprite.animation.smooth_rotation(360, speed=200)
        self.sprite.animation.start()

    def fixed_update(self) -> None:
        self.sprite.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.sprite.interpolation_update(interpolation)

    def update(self) -> None:
        self.sprite.update()

    def render(self) -> None:
        self.window.draw(self.sprite)


class DraggableSprite(Sprite, Draggable):
    def __init__(
        self,
        master: Scene | Window,
        image: Surface | None = None,
        *,
        width: float | None = None,
        height: float | None = None,
    ) -> None:
        Sprite.__init__(self, image, width=width, height=height)
        Draggable.__init__(self, master=master)

    def invoke(self) -> None:
        pass

    def _mouse_in_hitbox(self, mouse_pos: tuple[float, float]) -> bool:
        return self.get_rect().collidepoint(mouse_pos)


class SpriteCollisionScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK

        self.car = DraggableSprite(self, ImagesResources.car[0])
        self.cactus = DraggableSprite(self, ImagesResources.cactus, height=200)
        self.cross = Image(ImagesResources.cross["normal"], width=30)

    def on_start_loop_before_transition(self) -> None:
        self.car.center = self.window.width / 4, self.window.centery
        self.cactus.center = self.window.width * 3 / 4, self.window.centery
        self.cross.hide()
        return super().on_start_loop_before_transition()

    def update(self) -> None:
        super().update()

        if intersection := self.car.is_mask_colliding(self.cactus):
            self.cross.show()
            self.cross.center = intersection
        else:
            self.cross.hide()

    def render(self) -> None:
        self.window.draw(self.car, self.cactus, self.cross)


class SpriteGroupCollisionScene(MainScene, framerate=60, fixed_framerate=50):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK

        self.car = DraggableSprite(self, ImagesResources.car[0])
        self.cacti = SpriteGroup()

    def on_start_loop_before_transition(self) -> None:
        self.car.center = self.window.center
        self.cacti.clear()
        return super().on_start_loop_before_transition()

    def on_start_loop(self) -> None:
        self.on_quit_exit_stack.callback(self.window.set_title, self.window.get_title())

        from random import Random

        random = Random()

        @self.every(200)
        def _() -> None:
            if len(self.cacti) >= 500:
                return
            cactus = Sprite(ImagesResources.cactus, height=200)

            cactus.left = random.randrange(0, int(self.window.right - cactus.width))
            cactus.top = random.randrange(0, int(self.window.bottom - cactus.height))

            self.cacti.add(cactus)

        return super().on_start_loop()

    def update(self) -> None:
        super().update()

        del list(self.cacti.sprite_collide(self.car, True))[:]

        self.window.set_title(f"{len(self.cacti)} {'cacti' if len(self.cacti) > 1 else 'cactus'}")

    def render(self) -> None:
        self.window.draw(self.cacti, self.car)


class MyCustomEvent(Event):
    def __init__(self, message: str) -> None:
        super().__init__()
        self.message: str = message

    @classmethod
    def from_dict(cls: type[Self], event_dict: Mapping[str, Any]) -> Self:
        return cls(**event_dict)

    def to_dict(self) -> dict[str, Any]:
        return dict(self.__dict__)


class EventScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.cross: PlusCrossShape = PlusCrossShape(50, 50, color=RED, outline_color=WHITE, outline=3)
        self.circle: CircleShape = CircleShape(3, color=YELLOW)
        self.event.bind_mouse_position(lambda pos: self.cross.set_position(center=pos))
        self.event.bind_mouse_button(MouseButton.LEFT, self.__switch_color)
        self.event.bind(MyCustomEvent, self.__update_window_title)

    def on_start_loop(self) -> None:
        Mouse.hide_cursor()
        self.on_quit_exit_stack.callback(Mouse.show_cursor)
        self.on_quit_exit_stack.callback(self.window.set_title, self.window.get_title())

    def update(self) -> None:
        self.circle.center = self.cross.center

    def render(self) -> None:
        self.window.draw(self.cross, self.circle)

    def __switch_color(self, event: MouseButtonEvent) -> None:
        match event:
            case MouseButtonDownEvent():
                self.cross.color = YELLOW
            case MouseButtonUpEvent():
                self.cross.color = RED
        self.window.post_event(MyCustomEvent(f"mouse_pos=({event.pos})"))

    def __update_window_title(self, event: MyCustomEvent) -> None:
        self.window.set_title(event.message)


class TextImageScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text: TextImage = TextImage(
            "I'm a text", img=ImagesResources.cactus, font=(None, 50), color=WHITE, shadow_x=-5, shadow_y=-5, wrap=5
        )
        self.text.img_scale_to_size((100, 100))
        self.text.center = self.window.center

    def on_start_loop_before_transition(self) -> None:
        self.text.angle = 0
        self.text.scale = (1, 1)

    def on_start_loop(self) -> None:
        self.animation = TransformAnimation(self.text)
        self.animation.clear()
        self.animation.smooth_rotation(360)
        self.animation.smooth_width_growth(100)
        self.animation.start()

    def fixed_update(self) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.animation.update(interpolation)

    def render(self) -> None:
        self.window.draw(self.text)


class ButtonScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
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

        self.cancel = ImageButton(
            self, img=ImagesResources.cross["normal"], active_img=ImagesResources.cross["hover"], callback=restart
        )
        self.cancel.center = self.window.center
        self.cancel.move(450, 0)

    def on_start_loop_before_transition(self) -> None:
        self.counter = 0
        self.button.text = "0"
        self.button.scale = (1, 1)
        self.button.angle = 0

    def on_start_loop(self) -> None:
        self.animation = TransformAnimation(self.button)
        self.animation.clear()
        self.animation.smooth_width_growth(100)
        self.animation.smooth_rotation(390, speed=300)
        self.animation.start()

    def fixed_update(self) -> None:
        self.animation.fixed_update()

    def interpolation_update(self, interpolation: float) -> None:
        self.animation.update(interpolation)

    def __increase_counter(self) -> None:
        self.counter += 1
        self.button.text = str(self.counter)

    def render(self) -> None:
        self.window.draw(self.button, self.cancel)


class CheckBoxScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
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
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.hprogress = hprogress = ProgressBar(500, 75, from_=10, to=90, orient="horizontal", outline=10)
        self.vprogress = vprogress = ProgressBar(125, 500, from_=10, to=90, orient="vertical")
        self.restart = restart = ImageButton(
            self,
            img=ImagesResources.cross["normal"],
            active_img=ImagesResources.cross["hover"],
            callback=self.__restart,
        )

        hprogress.show_label("Loading...", "top", font=(None, 60), color=WHITE)
        hprogress.show_percent("inside", font=(None, 60))
        hprogress.center = self.window.width / 4, self.window.centery
        vprogress.show_label("Loading...", "right", font=(None, 60), color=WHITE)
        vprogress.show_percent("inside", font=(None, 60))
        vprogress.center = self.window.width * 3 / 4, self.window.centery
        restart.midtop = self.window.centerx, self.window.height * 3 / 4

    def on_start_loop_before_transition(self) -> None:
        self.__restart()

    def on_start_loop(self) -> None:
        @self.every(20)
        def increment() -> None:
            self.hprogress.value += 1
            self.vprogress.value += 1

        self.callback = increment

    def on_quit(self) -> None:
        self.callback.kill()

    def render(self) -> None:
        self.window.draw(self.hprogress, self.vprogress, self.restart)

    def __restart(self) -> None:
        self.hprogress.percent = 0
        self.vprogress.percent = 0


class ScaleBarScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.text = text = Text(font=(FontResources.cooperblack, 40), color=WHITE, shadow_x=3, shadow_y=3)
        self.scale = scale = ScaleBar(
            self,
            500,
            75,
            from_=10,
            to=90,
            value_callback=lambda value: self.text.config(message=f"Value: {value}"),
            cursor_thickness=10,
        )
        self.vscale = vscale = ScaleBar(self, 75, 500, from_=10, to=90, orient="vertical", outline=10)

        scale.resolution = 0
        scale.center = self.window.width / 4, self.window.centery
        text.midtop = scale.centerx, scale.bottom + 20
        vscale.show_value("right", round_n=5, font=(FontResources.cooperblack, 40), color=WHITE, shadow_x=3, shadow_y=3)
        vscale.center = self.window.width * 3 / 4, self.window.centery

    def on_start_loop_before_transition(self) -> None:
        self.scale.value = self.scale.from_value
        self.vscale.value = self.vscale.from_value

    def render(self) -> None:
        self.window.draw(self.scale, self.vscale, self.text)


class EntryScene(MainScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.entry = entry = Entry(self, font=(None, 70), fg=BLUE, outline=5)
        entry.center = self.window.center

    def on_start_loop_before_transition(self) -> None:
        self.entry.clear()

    def render(self) -> None:
        self.window.draw(self.entry)


LOREM_IPSUM = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Proin euismod justo ac pharetra fermentum. Duis neque massa, commodo eu est vel, dignissim interdum eros. Nulla augue ex, blandit ac magna dapibus, dignissim venenatis massa. Donec tempus laoreet eros tristique rhoncus. Sed eget metus vitae purus ultricies semper. Suspendisse sodales rhoncus quam ac aliquam. Duis quis elit rhoncus, condimentum dolor nec, elementum lorem. Integer placerat dui orci, in ultricies nulla viverra ac. Morbi at justo eu libero rutrum dignissim a in velit. Suspendisse magna odio, fermentum vel tortor eget, condimentum sagittis ex. Vivamus tristique venenatis purus, at pharetra erat lobortis id. Pellentesque tincidunt bibendum erat, ac faucibus ligula semper vitae. Vestibulum ac quam in nulla tristique congue id quis lectus. Sed fermentum hendrerit velit."


class ScrollBarScene(RenderedLayeredScene, AbstractAutoLayeredDrawableScene, MainScene):
    window: MainWindow

    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.area = ScrollArea(master=self, width=self.window.width - 25, height=self.window.height - 25)
        self.hscroll = ScrollBar(self.area, self.window.width, 25, outline=3, orient="horizontal")
        self.hscroll.midbottom = self.window.midbottom
        next_button: Button = self.window.next_button
        self.vscroll = ScrollBar(
            self.area, 25, self.window.height - self.hscroll.height - (next_button.bottom + 10), outline=3, orient="vertical"
        )
        self.vscroll.bottomright = self.window.right, self.hscroll.top
        self.vscroll.border_radius = 25
        Text(LOREM_IPSUM, font=(None, 100), wrap=50, line_spacing=10).add_to_group(self.area)

    def on_start_loop(self) -> None:
        super().on_start_loop()
        ScrollArea.set_vertical_flip(True)
        ScrollArea.set_horizontal_flip(True)

    def on_quit(self) -> None:
        super().on_quit()
        ScrollArea.set_vertical_flip(False)
        ScrollArea.set_horizontal_flip(False)


class TestGUIScene(GUIScene, RenderedLayeredScene, AbstractAutoLayeredDrawableScene):
    @classmethod
    def __theme_init__(cls) -> None:
        super().__theme_init__()

        Button.set_default_theme("default")
        Button.set_theme(
            "default",
            {
                "border_top_left_radius": 30,
                "border_bottom_right_radius": 30,
            },
        )

    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        Button.set_default_focus_on_hover(True)

        self.text = Text(font=(FontResources.cooperblack, 40), color=WHITE, shadow_x=3, shadow_y=3)
        self.first = Button(self, "First", callback=lambda: self.text.config(message="First"))
        self.second = Button(self, "Second", callback=lambda: self.text.config(message="Second"))
        self.third = Button(self, "Third", callback=lambda: self.text.config(message="Third"))

        self.first.focus.set_obj_on_side(on_right=self.second)
        self.second.focus.set_obj_on_side(on_left=self.first, on_right=self.third)
        self.third.focus.set_obj_on_side(on_left=self.second)

        self.second.center = self.window.center
        self.first.midright = (self.second.left - 10, self.second.centery)
        self.third.midleft = (self.second.right + 10, self.second.centery)

        Button.set_default_focus_on_hover(None)

    def update(self) -> None:
        self.text.midtop = (self.second.centerx, self.second.bottom + 10)
        return super().update()


class GridScene(GUIScene, RenderedLayeredScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        Button.set_default_focus_on_hover(True)

        self.text = Text("None", font=(FontResources.cooperblack, 40), color=WHITE, shadow_x=3, shadow_y=3)
        self.grid = Grid(self, bg_color=YELLOW)

        self.grid.default_padding.x = 20
        self.grid.default_padding.y = 20

        def create_button(text: str) -> Button:
            return Button(self, text, callback=lambda: self.text.config(message=text))

        self.grid.place(create_button("First"), 0, 0)
        self.grid.place(create_button("Second"), 2, 1)
        self.grid.place(create_button("Third"), 1, 2)
        self.grid.place(create_button("Fourth"), 1, 1)

        # self.grid.place(create_button("First"), 1, 1)
        # self.grid.place(create_button("Second"), 7, 3)
        # self.grid.place(create_button("Third"), 4, 12)
        # self.grid.place(create_button("Fourth"), 4, 3)
        # print(list(self.grid.cells()))
        # self.grid.unify()
        # print(list(self.grid.cells()))

        self.grid.outline = 2
        self.grid.outline_color = PURPLE

        self.grid.center = self.window.center
        self.group.add(self.text, self.grid)

        Button.set_default_focus_on_hover(None)

    def on_start_loop_before_transition(self) -> None:
        self.set_text_position()
        return super().on_start_loop_before_transition()

    def update(self) -> None:
        self.set_text_position()
        super().update()

    def set_text_position(self) -> None:
        self.text.midtop = (self.grid.centerx, self.grid.bottom + 10)


class FormScene(GUIScene, RenderedLayeredScene, AbstractAutoLayeredDrawableScene):
    @classmethod
    def __theme_init__(cls) -> None:
        super().__theme_init__()

        Text.set_theme("text", {"font": (FontResources.cooperblack, 40), "color": WHITE, "shadow_x": 3, "shadow_y": 3})
        Text.set_theme("response", {"font": (FontResources.cooperblack, 50)})

        Entry.set_default_theme("default")
        Entry.set_theme("default", {"font": (None, 40), "highlight_color": YELLOW})

    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK

        self.form = Form(self, on_submit=self.on_form_submit)
        self.form.add_entry(
            "first_name", Entry(self, on_validate=lambda: last_name.focus.set()), Text("First name", theme="text")
        )
        last_name = self.form.add_entry(
            "last_name", Entry(self, on_validate=lambda: self.submit.focus.set()), Text("Last name", theme="text")
        )

        self.response = Text(theme=["text", "response"])
        self.submit = Button(self, "Submit", callback=self.form.submit)
        self.submit.focus.below(last_name)

    def on_start_loop_before_transition(self) -> None:
        super().on_start_loop_before_transition()
        self.response.message = ""
        self.response.topleft = (0, 0)
        self.form.center = self.window.width / 4, self.window.centery
        self.submit.midtop = (self.form.centerx, self.form.bottom + self.form.pady)

    def on_form_submit(self, data: Mapping[str, str]) -> None:
        self.response.message = "{first_name}\n{last_name}".format_map(data)
        self.response.center = self.window.width * 3 / 4, self.window.centery


class WidgetsScene(GUIScene):
    @classmethod
    def __theme_init__(cls) -> None:
        super().__theme_init__()

        Text.set_theme("text", {"font": (FontResources.cooperblack, 40), "color": WHITE, "shadow_x": 3, "shadow_y": 3})

        Entry.set_default_theme("text")
        Entry.set_theme("text", {"fg": BLACK, "shadow_x": 0, "shadow_y": 0})

        CheckBox.set_default_theme("default")
        CheckBox.set_theme("default", {"highlight_color": YELLOW})

    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)

        AbstractWidget.set_default_focus_on_hover(True)

        self.background_color = BLUE_DARK

        self.grid = grid = Grid(self, padx=10, pady=10)

        grid.place(Button(self, "Button"), 0, 0)
        grid.place(CheckBox(self, 50, 50, BLUE_LIGHT, on_value=10, off_value=0), 0, 1)
        grid.place(Entry(self), 1, 0)
        grid.place(ScaleBar(self, 100, 50, from_=0, to=100, cursor_thickness=1), 1, 1)
        grid.place(ImageButton(self, img=ImagesResources.cross["normal"], active_img=ImagesResources.cross["hover"]), 2, 2)

        AbstractWidget.set_default_focus_on_hover(False)

    def on_start_loop_before_transition(self) -> None:
        self.grid.center = self.window.center
        return super().on_start_loop_before_transition()

    def render(self) -> None:
        self.window.draw(self.grid)


class MusicManager(ResourceManager):
    menu: Music
    garage: Music
    gameplay: Music
    __resource_loader__ = MusicLoader
    __resources_directory__ = "./demo_resources/sounds"
    __resources_files__ = {"menu": "menu.wav", "garage": "garage.wav", "gameplay": "gameplay.wav"}


class SoundManager(ResourceManager):
    select: Sound
    validate: Sound
    block: Sound
    __resource_loader__ = SoundLoader
    __resources_directory__ = "./demo_resources/sounds"
    __resources_files__ = {"select": "sfx-menu-select.wav", "validate": "sfx-menu-validate.wav", "block": "sfx-menu-block.wav"}


class VolumeScaleBar(ScaleBar):
    def __init__(self, master: Scene | Window, width: float, height: float, *, theme: Any | None = None):
        super().__init__(
            master,
            width,
            height,
            from_=0,
            to=100,
            resolution=1,
            percent_default=MusicStream.get_volume(),
            percent_callback=MusicStream.set_volume,
            cursor_thickness=1,
            theme=theme,
        )


class AudioScene(MainScene):
    def __init__(self) -> None:
        super().__init__()
        self.event.bind(MusicEndEvent, print)
        self.event.bind_key_press(Key.K_F2, lambda _: MusicStream.fadeout(1000))

    @classmethod
    def __theme_init__(cls) -> None:
        super().__theme_init__()
        Text.set_default_theme("text")
        Text.set_theme("text", {"font": (FontResources.cooperblack, 40), "color": WHITE, "shadow_x": 3, "shadow_y": 3})
        Button.set_theme("text", {"fg": BLACK})

    def awake(self, **kwargs: Any) -> None:
        self.background_color = BLUE_DARK
        self.text = Text("Audio Scene")
        self.first = Button(
            self,
            "First",
            shadow_x=0,
            shadow_y=0,
            hover_sound=SoundManager.select,
            click_sound=SoundManager.validate,
            callback=self.on_start_loop,
        )
        self.scale = VolumeScaleBar(self, 500, 75)
        self.scale.show_label("Music volume", side="top")
        self.scale.show_percent("inside", shadow_x=0, shadow_y=0, color=BLACK)
        return super().awake(**kwargs)

    def on_start_loop_before_transition(self) -> None:
        self.update()
        return super().on_start_loop_before_transition()

    def on_start_loop(self) -> None:
        MusicManager.menu.play()
        MusicManager.garage.queue()
        MusicManager.gameplay.queue()
        return super().on_start_loop()

    def update(self) -> None:
        self.text.center = self.window.center
        self.first.midtop = (self.text.centerx, self.text.bottom + 10)
        self.scale.midbottom = (self.window.centerx, self.window.bottom - 10)
        return super().update()

    def render(self) -> None:
        self.window.draw(self.text, self.first, self.scale)

    def on_quit(self) -> None:
        MusicStream.stop()
        return super().on_quit()


class GUIAudioScene(GUIScene, RenderedLayeredScene, AbstractAutoLayeredDrawableScene, MainScene):
    @classmethod
    def __theme_init__(cls) -> None:
        super().__theme_init__()
        Text.set_default_theme("text")
        Text.set_theme("text", {"font": (FontResources.cooperblack, 40), "color": WHITE, "shadow_x": 3, "shadow_y": 3})

        Button.set_default_theme("button")
        Button.set_theme("text", {"fg": BLACK})
        Button.set_theme(
            "button",
            {
                "shadow_x": 0,
                "shadow_y": 0,
                "hover_sound": SoundManager.select,
                "click_sound": SoundManager.validate,
                "disabled_sound": SoundManager.block,
                "focus_on_hover": True,
            },
        )

    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK

        self.text = Text("None")
        self.grid = Grid(self, bg_color=YELLOW, padx=20, pady=20)

        def create_button(text: str, state: str = "normal") -> Button:
            return Button(self, text, callback=lambda: self.text.config(message=text), state=state)

        self.grid.place(create_button("First"), 0, 0)
        self.grid.place(create_button("Second"), 2, 1)
        self.grid.place(create_button("Third"), 1, 2)
        self.grid.place(create_button("Fourth", state="disabled"), 1, 1)

        self.grid.outline = 2
        self.grid.outline_color = PURPLE

        self.grid.center = self.window.center

        self.scale = VolumeScaleBar(self, 500, 75)
        self.scale.focus.take(False)
        self.scale.show_label("Music volume", side="top")
        self.scale.show_percent("inside", shadow_x=0, shadow_y=0, color=BLACK)

        self.scale.midbottom = (self.window.centerx, self.window.bottom - 10)

    def on_start_loop_before_transition(self) -> None:
        self.set_text_position()
        return super().on_start_loop_before_transition()

    def update(self) -> None:
        self.set_text_position()
        super().update()

    def set_text_position(self) -> None:
        self.text.midtop = (self.grid.centerx, self.grid.bottom + 10)

    def on_start_loop(self) -> None:
        MusicManager.menu.play(repeat=-1)
        return super().on_start_loop()

    def on_quit(self) -> None:
        MusicStream.stop()
        return super().on_quit()


class MyDialog(PopupDialog, GUIScene):
    @classmethod
    def __theme_init__(cls) -> None:
        super().__theme_init__()
        Text.set_theme("text", {"font": (FontResources.cooperblack, 40)})

    def awake(self, **kwargs: Any) -> None:
        print(kwargs)
        super().awake(border_radius=30, draggable=True, **kwargs)
        self.background_color = BLACK.with_alpha(200)
        self.event.bind_key_press(Key.K_ESCAPE, lambda _: self.stop())
        self.cancel = ImageButton(
            self if self.draggable_popup is None else self.draggable_popup,
            img=ImagesResources.cross["normal"],
            active_img=ImagesResources.cross["hover"],
            callback=self.stop,
        )
        self.text = Text("I'm a text", theme="text")

    def set_default_popup_position(self) -> None:
        self.popup.midbottom = self.window.midtop

    def run_start_transition(self) -> None:
        animation = MoveAnimation(self.popup)
        animation.smooth_set_position(center=self.window.center, speed=2000)
        animation.wait_until_finish(self)

    def run_quit_transition(self) -> None:
        animation = MoveAnimation(self.popup)
        animation.smooth_set_position(midtop=self.window.midbottom, speed=2000)
        animation.wait_until_finish(self)

    def update(self) -> None:
        self.cancel.topleft = (self.popup.left + 20, self.popup.top + 20)
        self.text.center = self.popup.center
        return super().update()

    def _render(self) -> None:
        self.window.draw(self.cancel, self.text)


class TestDialogScene(GUIScene, RenderedLayeredScene, AbstractAutoLayeredDrawableScene):
    def awake(self, **kwargs: Any) -> None:
        super().awake(**kwargs)
        self.background_color = BLUE_DARK
        self.button = Button(self, "Open dialog", callback=self.__open_dialog)

    def on_start_loop_before_transition(self) -> None:
        self.button.center = self.window.center
        return super().on_start_loop_before_transition()

    def __open_dialog(self) -> None:
        self.start(MyDialog, test=True)
        print("Dialog ended")


class SceneTransitionTranslation(SceneTransition):
    __slots__ = "__side"

    def __init__(self, side: Literal["left", "right"]) -> None:
        super().__init__()
        self.__side: Literal["left", "right"] = side

    def init(self, previous_scene_image: Surface, actual_scene_image: Surface) -> None:
        self.previous_scene = Image(previous_scene_image, copy=False)
        self.actual_scene = Image(actual_scene_image, copy=False)
        window_rect = self.window.get_rect()
        self.previous_scene.center = self.actual_scene.center = window_rect.center
        self.previous_scene.fill(BLACK.with_alpha(100))
        self.previous_scene_shown: Callable[[], bool]
        self.previous_scene_animation = TransformAnimation(self.previous_scene)
        if self.__side == "left":
            self.previous_scene_animation.infinite_translation((-1, 0), speed=3000)
            self.previous_scene_shown = lambda: self.previous_scene.right >= window_rect.left
        else:
            self.previous_scene_animation.infinite_translation((1, 0), speed=3000)
            self.previous_scene_shown = lambda: self.previous_scene.left <= window_rect.right
        self.previous_scene_animation.start()

    def fixed_update(self) -> None:
        self.previous_scene_animation.fixed_update()
        if not self.previous_scene_shown():
            self.stop()

    def interpolation_update(self, interpolation: float) -> None:
        self.previous_scene_animation.update(interpolation)

    def render(self) -> None:
        self.actual_scene.draw_onto(self.window)
        self.previous_scene.draw_onto(self.window)

    def destroy(self) -> None:
        self.__dict__.clear()


class TextFramerate(Text, no_theme=True):
    def __init__(self) -> None:
        super().__init__(color=WHITE)
        self.__refresh_rate: int = 200

    @property
    def refresh_rate(self) -> int:
        return self.__refresh_rate

    @refresh_rate.setter
    def refresh_rate(self, value: int) -> None:
        self.__refresh_rate = max(int(value), 0)


class MainWindow(SceneWindow):

    all_scenes: ClassVar[list[type[Scene]]] = [
        ShapeScene,
        AnimationScene,
        AnimationStateFullScene,
        ShapeTransformTestScene,
        GradientScene,
        RainbowScene,
        TextScene,
        ResourceScene,
        SpriteMaskScene,
        AnimatedSpriteScene,
        SpriteCollisionScene,
        SpriteGroupCollisionScene,
        EventScene,
        TextImageScene,
        ButtonScene,
        CheckBoxScene,
        ProgressScene,
        ScaleBarScene,
        EntryScene,
        ScrollBarScene,
        TestGUIScene,
        GridScene,
        FormScene,
        WidgetsScene,
        AudioScene,
        GUIAudioScene,
        TestDialogScene,
    ]

    def __init__(self) -> None:
        # super().__init__("my window", (0, 0))
        super().__init__("my window", (1366, 768), resizable=True)

    def __window_init__(self) -> None:
        super().__window_init__()
        # Text.set_default_font(FontResources.cooperblack)

        Button.set_default_theme("default")
        Button.set_theme("default", {"font": (FontResources.cooperblack, 20), "border_radius": 5})

        self.__framerate_update_clock: Clock = Clock(start=True)
        self.text_framerate: TextFramerate = TextFramerate()
        self.text_framerate.midtop = (self.centerx, self.top + 10)
        self.set_default_framerate(120)
        self.set_default_fixed_framerate(60)
        self.index: int = 0
        self.prev_button: Button = Button(self, "Previous", callback=self.__previous_scene)
        self.next_button: Button = Button(self, "Next", font=self.prev_button.text_font, callback=self.__next_scene)
        self.prev_button.topleft = self.left + 10, self.top + 10
        self.next_button.topright = self.right - 10, self.top + 10

        self.event.bind_key_press(Key.K_F5, lambda _: gc.collect())
        self.event.bind_key_release(Key.K_F11, lambda _: self.screenshot())
        self.event.bind(ScreenshotEvent, self.__show_screenshot)
        self.screenshot_image: Image | None = None
        self.screenshot_callback: WindowCallback | None = None

    def __window_quit__(self) -> None:
        super().__window_quit__()
        try:
            del self.prev_button, self.next_button, self.text_framerate
        except AttributeError:
            pass

    def mainloop(self, index: int = 0) -> None:
        self.index = index % len(self.all_scenes)
        self.run(self.all_scenes[self.index])

    def render_scene(self) -> None:
        super().render_scene()
        self.draw(self.prev_button, self.next_button)

    def _system_display(self) -> None:
        super()._system_display()
        text_framerate: TextFramerate = self.text_framerate
        if text_framerate.is_shown():
            if not text_framerate.message or self.__framerate_update_clock.elapsed_time(text_framerate.refresh_rate):
                text_framerate.message = f"{round(self.framerate)} FPS"
            text_framerate.draw_onto(self.renderer)
        if screenshot_img := self.screenshot_image:
            screenshot_img.draw_onto(self.renderer)

    def __next_scene(self) -> None:
        self.index = (self.index + 1) % len(self.all_scenes)
        self.start_scene(self.all_scenes[self.index], remove_actual=True, transition=SceneTransitionTranslation("left"))

    def __previous_scene(self) -> None:
        self.index = (self.index - 1) % len(self.all_scenes)
        self.start_scene(self.all_scenes[self.index], remove_actual=True, transition=SceneTransitionTranslation("right"))

    def __show_screenshot(self, event: ScreenshotEvent) -> None:
        if self.screenshot_callback is not None:
            self.screenshot_callback.kill()
        SurfaceRenderer(event.screen).draw_rect(WHITE, event.screen.get_rect(), width=3)
        self.screenshot_image = img = Image(event.screen, width=self.width * 0.2, height=self.height * 0.2)
        img.topright = (self.right - 20, self.top + 20)

        @self.after(3000)
        def screenshot_alive() -> None:
            self.screenshot_image = None
            self.screenshot_callback = None

        self.screenshot_callback = screenshot_alive


def main() -> None:
    parser = ArgumentParser()
    parser.add_argument("-i", "--index", type=int, default=0)
    parser.add_argument("-s", "--scenes", action="store_true")
    parser.add_argument("-d", "--debug", action="store_true")
    args = parser.parse_args()

    if args.scenes:
        import json

        print(json.dumps({i: s.__name__ for i, s in enumerate(MainWindow.all_scenes)}, indent=4))
        return

    if args.debug:
        gc.set_debug(gc.DEBUG_STATS | gc.DEBUG_LEAK)

    with Mixer.init(), MainWindow() as window:
        weakref.finalize(window, print, "Window dead")
        MusicStream.set_volume(0)
        window.mainloop(args.index)
    # Ensure there is no remaining reference to window
    del window
    print("end of main()")


if __name__ == "__main__":
    main()
