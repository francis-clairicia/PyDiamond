# -*- coding: Utf-8 -*

from __future__ import annotations

__all__ = ["Drawable", "TDrawable", "MetaDrawable", "MetaTDrawable"]

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional, Tuple

from ..system.utils import wraps
from .rect import Rect
from .transformable import MetaTransformable, Transformable

if TYPE_CHECKING:
    from .renderer import Renderer


def _draw_decorator(func: Callable[[Drawable, Renderer], None], /) -> Callable[[Drawable, Renderer], None]:
    @wraps(func)
    def wrapper(self: Drawable, /, target: Renderer) -> None:
        if self.is_shown():
            func(self, target)

    return wrapper


class MetaDrawable(ABCMeta):
    def __new__(metacls, /, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwargs: Any) -> MetaDrawable:
        if "Drawable" in globals() and not any(issubclass(cls, Drawable) for cls in bases):
            raise TypeError(
                f"{name!r} must be inherits from a {Drawable.__name__} class in order to use {MetaDrawable.__name__} metaclass"
            )

        draw_method: Optional[Callable[[Drawable, Renderer], None]] = namespace.get("draw_onto")
        if callable(draw_method):
            namespace["draw_onto"] = _draw_decorator(draw_method)

        return super().__new__(metacls, name, bases, namespace, **kwargs)


class Drawable(metaclass=MetaDrawable):
    def __init__(self, /) -> None:
        self.__shown: bool = True

    @abstractmethod
    def draw_onto(self, /, target: Renderer) -> None:
        raise NotImplementedError

    def show(self, /) -> None:
        self.set_visibility(True)

    def hide(self, /) -> None:
        self.set_visibility(False)

    def set_visibility(self, /, status: bool) -> None:
        self.__shown = bool(status)

    def is_shown(self, /) -> bool:
        return self.__shown


class MetaTDrawable(MetaDrawable, MetaTransformable):
    pass


class TDrawable(Drawable, Transformable, metaclass=MetaTDrawable):
    def __init__(self, /) -> None:
        Drawable.__init__(self)
        Transformable.__init__(self)

    angle: float
    scale: float
    rect: Rect
    x: float
    y: float
    size: Tuple[float, float]
    width: float
    height: float
    left: float
    right: float
    top: float
    bottom: float
    center: Tuple[float, float]
    centerx: float
    centery: float
    topleft: Tuple[float, float]
    topright: Tuple[float, float]
    bottomleft: Tuple[float, float]
    bottomright: Tuple[float, float]
    midtop: Tuple[float, float]
    midbottom: Tuple[float, float]
    midleft: Tuple[float, float]
    midright: Tuple[float, float]
