# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta, abstractmethod
from typing import Callable, Dict, Iterator, List, Optional, TYPE_CHECKING, Tuple, Union

from pygame.math import Vector2
from .clock import Clock

from .scene import Scene

if TYPE_CHECKING:
    from .drawable import Drawable
    from .window import Window, WindowCallback


class _AbstractAnimationClass(metaclass=ABCMeta):
    def __init__(self, drawable: Drawable, milliseconds: float):
        self.__drawable: Drawable = drawable
        self.__clock: Clock = Clock()
        self.__milliseconds: float = max(milliseconds, 0)
        self.__animation_started: bool = True

    def started(self) -> bool:
        return self.__milliseconds > 0 and self.__animation_started

    def stop(self) -> None:
        self.__animation_started = False
        self.default()

    def ready(self) -> bool:
        if not self.started():
            return False
        return self.__clock.elapsed_time(self.__milliseconds)

    @abstractmethod
    def __call__(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def default(self) -> None:
        raise NotImplementedError

    @property
    def drawable(self) -> Drawable:
        return self.__drawable

    @property
    def milliseconds(self) -> float:
        return self.__milliseconds


class _AnimationSetPosition(_AbstractAnimationClass):
    def __init__(
        self, drawable: Drawable, milliseconds: float, speed: float, **position: Union[float, Tuple[float, float]]
    ) -> None:
        super().__init__(drawable, milliseconds)
        self.__position: Dict[str, Union[float, Tuple[float, float]]] = position
        self.__speed: float = speed

    def started(self) -> bool:
        return super().started() and self.__speed > 0

    def __call__(self) -> None:
        if not self.ready():
            return
        projection = self.drawable.get_rect(**self.__position)
        direction = Vector2(projection.center) - Vector2(self.drawable.center)
        length = direction.length()
        if length > 0 and length > self.__speed:
            direction.scale_to_length(self.__speed)
            self.drawable.translate(direction)
        else:
            self.stop()

    def default(self) -> None:
        self.drawable.set_position(**self.__position)


class _AnimationMove(_AbstractAnimationClass):
    def __init__(
        self, drawable: Drawable, translation: Union[Vector2, Tuple[float, float]], milliseconds: float, speed: float
    ) -> None:
        super().__init__(drawable, milliseconds)
        self.__vector: Vector2 = Vector2(translation)
        self.__speed: float = speed
        self.__traveled: float = 0

    def started(self) -> bool:
        return super().started() and self.__speed > 0 and self.__vector != Vector2(0, 0)

    def __call__(self) -> None:
        if not self.ready():
            return
        direction = self.__vector.xy
        if direction.length() > self.__traveled + self.__speed:
            self.__traveled += self.__speed
            direction.scale_to_length(self.__speed)
            self.drawable.translate(direction)
        else:
            self.stop()

    def default(self) -> None:
        if self.__vector != Vector2(0, 0):
            self.__vector.scale_to_length(abs(self.__vector.length() - self.__traveled))
            self.drawable.translate(self.__vector)
            self.__vector = Vector2(0, 0)


class _AnimationRotation(_AbstractAnimationClass):
    def __init__(
        self,
        drawable: Drawable,
        milliseconds: float,
        angle: float,
        offset: float,
        point: Union[Vector2, Tuple[float, float], str, None],
    ):
        super().__init__(drawable, milliseconds)
        self.__angle: float = abs(angle)
        self.__sign: int = int(angle // abs(angle)) if angle != 0 and offset > 0 else 0
        self.__offset: float = offset * self.__sign if offset > 0 else 0
        self.__actual_angle: float = 0
        self.__pivot: Union[Vector2, Tuple[float, float], str, None] = point

    def started(self) -> bool:
        return super().started() and self.__angle != 0 and self.__offset != 0

    def __call__(self) -> None:
        if not self.ready():
            return
        if self.__actual_angle + abs(self.__offset) < self.__angle:
            self.__actual_angle += abs(self.__offset)
            self.drawable.rotate(self.__offset, self.__pivot)
        else:
            self.stop()

    def default(self) -> None:
        if self.__actual_angle != self.__angle:
            self.drawable.rotate(abs(self.__angle - self.__actual_angle) * self.__sign, self.__pivot)
            self.__actual_angle = self.__angle


class _AnimationScaleSize(_AbstractAnimationClass):
    def __init__(self, drawable: Drawable, milliseconds: float, field: str, size: float, offset: float):
        super().__init__(drawable, milliseconds)
        self.__size: float = max(size, 0)
        self.__field: str = field
        self.__offset: float
        self.__sign: int
        self.__actual_size = self.get_drawable_size()
        size_offset = self.__size - self.__actual_size
        if offset == 0 or size_offset == 0:
            self.__offset = self.__sign = 0
        else:
            self.__sign = int(size_offset // abs(size_offset))
            self.__offset = abs(offset) * self.__sign

    def started(self) -> bool:
        return super().started() and self.__offset != 0

    def __call__(self) -> None:
        if not self.ready():
            return
        self.__actual_size += self.__offset
        if (self.__offset < 0 and self.__actual_size > self.__size) or (self.__offset > 0 and self.__actual_size < self.__size):
            self.set_drawable_size(self.__actual_size)
        else:
            self.stop()

    def get_drawable_size(self) -> float:
        return float(getattr(self.drawable, self.__field))

    def set_drawable_size(self, value: float) -> None:
        setattr(self.drawable, self.__field, value)

    def default(self) -> None:
        self.set_drawable_size(self.__size)


class _AnimationScaleWidth(_AnimationScaleSize):
    def __init__(self, drawable: Drawable, milliseconds: float, width: float, offset: float) -> None:
        super().__init__(drawable, milliseconds, "width", width, offset)


class _AnimationScaleHeight(_AnimationScaleSize):
    def __init__(self, drawable: Drawable, milliseconds: float, height: float, offset: float) -> None:
        super().__init__(drawable, milliseconds, "height", height, offset)


class Animation:
    def __init__(self, drawable: Drawable):
        self.__drawable: Drawable = drawable
        self.__animations_order: List[str] = ["scale_width", "scale_height", "rotate", "rotate_point", "move"]
        self.__animations: Dict[str, Optional[_AbstractAnimationClass]] = dict.fromkeys(self.__animations_order)
        self.__window_callback: Optional[WindowCallback] = None
        self.__save_window_callback: Optional[WindowCallback] = None
        self.__save_animations: Optional[Dict[str, Optional[_AbstractAnimationClass]]] = None

    def register_position(
        self, speed: float = 1, milliseconds: float = 10, **position: Union[float, Tuple[float, float]]
    ) -> Animation:
        self.stop_background()
        self.__animations["move"] = _AnimationSetPosition(self.__drawable, milliseconds, speed, **position)
        return self

    def register_translation(
        self, translation: Union[Vector2, Tuple[float, float]], speed: float = 1, milliseconds: float = 10
    ) -> Animation:
        self.stop_background()
        self.__animations["move"] = _AnimationMove(self.__drawable, translation, milliseconds, speed)
        return self

    def register_rotation(
        self,
        angle: float,
        offset: float = 1,
        point: Optional[Union[Vector2, Tuple[float, float], str]] = None,
        milliseconds: float = 10,
    ) -> Animation:
        self.stop_background()
        animation = "rotate" if point is None else "rotate_point"
        self.__animations[animation] = _AnimationRotation(self.__drawable, milliseconds, angle, offset, point)
        return self

    def register_rotation_set(
        self,
        angle: float,
        offset: float = 1,
        point: Optional[Union[Vector2, Tuple[float, float], str]] = None,
        milliseconds: float = 10,
    ) -> Animation:
        angle %= 360
        if angle < 0:
            angle += 360
        if offset != 0:
            if self.__drawable.angle > angle:
                if offset > 0:
                    angle += 360
            else:
                if offset < 0:
                    angle -= 360
            angle -= self.__drawable.angle
        return self.register_rotation(angle, abs(offset), point, milliseconds)

    def register_width_offset(self, width_offset: float, step: float = 1, milliseconds: float = 10) -> Animation:
        width: float = self.__drawable.width + width_offset
        return self.register_width_set(width, max(step, 0), milliseconds)

    def register_width_set(self, width: float, offset: float = 1, milliseconds: float = 10) -> Animation:
        self.stop_background()
        self.__animations.pop("scale_height", None)
        self.__animations["scale_width"] = _AnimationScaleWidth(self.__drawable, milliseconds, width, offset)
        return self

    def register_height_offset(self, height_offset: float, step: float = 1, milliseconds: float = 10) -> Animation:
        height: float = self.__drawable.height + height_offset
        return self.register_height_set(height, max(step, 0), milliseconds)

    def register_height_set(self, height: float, offset: float = 1, milliseconds: float = 10) -> Animation:
        self.stop_background()
        self.__animations.pop("scale_width", None)
        self.__animations["scale_height"] = _AnimationScaleHeight(self.__drawable, milliseconds, height, offset)
        return self

    def start(self, master: Union[Window, Scene], at_every_frame: Optional[Callable[..., None]] = None) -> None:
        if isinstance(master, Scene):
            if master.window.scenes.top() is not master:
                return
            master = master.window
        while self.started():
            self.__animate(at_every_frame)
            master.handle_events(only_close_event=True)
            master.draw_and_refresh()
        self.__animate(at_every_frame)
        master.draw_and_refresh()
        self.__clear()

    def start_in_background(
        self,
        master: Union[Window, Scene],
        at_every_frame: Optional[Callable[..., None]] = None,
        after_animation: Optional[Callable[..., None]] = None,
    ) -> None:
        self.__start_window_callback(master, at_every_frame, after_animation)

    def started(self) -> bool:
        return any(animation.started() for animation in self.__iter_animations())

    def stop_background(self) -> None:
        if self.__window_callback is not None:
            self.__window_callback.kill()
            self.__save_window_callback = self.__window_callback
            self.__window_callback = None
            self.__save_animations = self.__animations.copy()
            self.__clear()

    def restart_background(self) -> None:
        if self.__window_callback is None and self.__save_window_callback is not None:
            if self.__save_animations is not None:
                self.__animations = self.__save_animations.copy()
            self.__save_window_callback()
            self.__save_window_callback = None

    def is_set(self, animation: str) -> bool:
        return self.__animations.get(animation) is not None

    def __iter_animations(self) -> Iterator[_AbstractAnimationClass]:
        for animation_name in self.__animations_order:
            animation: Optional[_AbstractAnimationClass] = self.__animations.get(animation_name)
            if animation is not None:
                yield animation

    def __clear(self) -> None:
        for key in self.__animations:
            self.__animations[key] = None

    def __animate(self, at_every_frame: Optional[Callable[..., None]]) -> None:
        for animation in self.__iter_animations():
            if animation.started():
                animation()
            else:
                animation.default()
        if callable(at_every_frame):
            at_every_frame()

    def __start_window_callback(
        self,
        master: Union[Window, Scene],
        at_every_frame: Optional[Callable[..., None]],
        after_animation: Optional[Callable[..., None]],
    ) -> None:
        window: Window
        scene: Optional[Scene]
        if isinstance(master, Scene):
            window = master.window
            scene = master
        else:
            window = master
            scene = None
        self.__animate(at_every_frame)
        if self.started():
            self.__window_callback = window.after(
                0,
                self.__start_window_callback,
                master=master,
                at_every_frame=at_every_frame,
                after_animation=after_animation,
                scene=scene,
            )
        else:
            self.__animate(at_every_frame)
            self.__clear()
            self.__save_animations = self.__save_window_callback = None
            if callable(after_animation):
                after_animation()
