# -*- coding: Utf-8 -*-

from __future__ import annotations

import pickle
from dataclasses import FrozenInstanceError
from itertools import combinations

from pydiamond.graphics.color import Color, ImmutableColor

import pytest


class TestColor:
    @pytest.mark.parametrize(
        ["attr", "hsva_index"],
        [
            pytest.param("h", 0),
            pytest.param("s", 1),
            pytest.param("v", 2),
        ],
    )
    def test__property__shorthand_to_Color_hsva(self, attr: str, hsva_index: int) -> None:
        # Arrange
        color = Color(123, 123, 123)

        # Act & Assert
        assert getattr(color, attr) == color.hsva[hsva_index]
        assert getattr(color, attr) == color.hsla[hsva_index]

    def test__instance__picklable(self) -> None:
        # Arrange
        color = Color(123, 123, 123)

        # Act
        reconstructed_color = pickle.loads(pickle.dumps(color))

        # Assert
        assert type(reconstructed_color) is type(color)
        assert reconstructed_color == color


class TestImmutableColor:
    @pytest.mark.parametrize(
        "attr",
        [
            "r",
            "g",
            "b",
            "a",
            "h",
            "s",
            "v",
            "hsva",
            "hsla",
            "cmy",
            "i1i2i3",
        ],
    )
    def test__setattr__frozen_attribute(self, attr: str) -> None:
        # Arrange
        color = ImmutableColor(0, 0, 0)

        # Act & Assert
        with pytest.raises(FrozenInstanceError):
            setattr(color, attr, None)

    @pytest.mark.slow
    def test__hash__returns_the_same_for_all_equal_colors(self) -> None:
        # Arrange

        # Act & Assert
        # This test will iterate around 160K times
        # It is enough to ensure the hash works I think
        for color_tuple in combinations(range(100), 3):
            lhs_color = ImmutableColor(color_tuple)
            rhs_color = ImmutableColor(color_tuple)

            assert hash(lhs_color) == hash(rhs_color)
