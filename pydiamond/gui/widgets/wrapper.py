# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""WidgetWrapper module"""

from __future__ import annotations

__all__ = ["WidgetWrappedElement", "WidgetWrapper"]

from abc import abstractmethod
from typing import TYPE_CHECKING, Any, Generic, Literal, Protocol, TypeVar, runtime_checkable

from ...graphics.drawable import SupportsDrawableGroups
from .abc import AbstractWidget, WidgetsManager

if TYPE_CHECKING:
    from ...graphics.drawable import BaseDrawableGroup
    from ...graphics.renderer import AbstractRenderer


@runtime_checkable
class WidgetWrappedElement(SupportsDrawableGroups, Protocol):
    @abstractmethod
    def get_size(self) -> tuple[float, float]:
        raise NotImplementedError

    @abstractmethod
    def get_position(self, __anchor: Literal["x", "y"], /) -> float:
        raise NotImplementedError

    @abstractmethod
    def set_position(self, *, x: float, y: float) -> None:
        raise NotImplementedError


_E = TypeVar("_E", bound=WidgetWrappedElement)


class WidgetWrapper(AbstractWidget, Generic[_E]):
    def __init__(self, master: AbstractWidget | WidgetsManager, wrapped: _E, **kwargs: Any) -> None:
        assert isinstance(wrapped, WidgetWrappedElement)
        self.__ref: _E = wrapped
        super().__init__(master=master, **kwargs)

    def draw_onto(self, target: AbstractRenderer) -> None:
        ref = self.__ref
        x = ref.get_position("x")
        y = ref.get_position("y")
        self.topleft = (x, y)
        return ref.draw_onto(target)

    def get_size(self) -> tuple[float, float]:
        return self.__ref.get_size()

    def add_to_group(self, *groups: BaseDrawableGroup[Any]) -> None:
        return self.__ref.add_to_group(*groups)

    def remove_from_group(self, *groups: BaseDrawableGroup[Any]) -> None:
        return self.__ref.remove_from_group(*groups)

    def has_group(self, group: BaseDrawableGroup[Any]) -> bool:
        return self.__ref.has_group(group)

    def get_groups(self) -> frozenset[BaseDrawableGroup[Any]]:
        return self.__ref.get_groups()

    def _on_move(self) -> None:
        x, y = self.topleft
        self.__ref.set_position(x=x, y=y)
        return super()._on_move()

    @property
    def ref(self) -> _E:
        return self.__ref
