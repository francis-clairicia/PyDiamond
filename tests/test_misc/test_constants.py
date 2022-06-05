# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from py_diamond.audio.mixer import AllowedAudioChanges, AudioFormat

import pygame.constants
import pytest

if TYPE_CHECKING:
    from enum import Enum


class EnumConstantSample(NamedTuple):
    enum: type[Enum]
    name: str
    constant_name: str


def enum_sample(enum: type[Enum], constant_name: dict[str, str] | Callable[[str], str] | None = None) -> list[EnumConstantSample]:
    if constant_name is None:
        constant_name = lambda name: name
    elif not callable(constant_name):
        _associations = constant_name
        constant_name = lambda name: _associations.get(name, name)
    return [EnumConstantSample(enum, member, constant_name(member)) for member in enum.__members__]


@pytest.mark.unit
@pytest.mark.parametrize(
    "sample",
    [
        *enum_sample(AudioFormat),
        *enum_sample(AllowedAudioChanges, constant_name=lambda name: f"AUDIO_ALLOW_{name}_CHANGE"),
    ],
    ids=lambda sample: f"{sample.enum.__name__}.{sample.name}==pygame.constants.{sample.constant_name}",
)
def test__enum_member__value_from_pygame_constants(sample: EnumConstantSample) -> None:
    # Arrange
    expected_value: int = getattr(pygame.constants, sample.constant_name)

    # Act
    actual_value: Any = sample.enum[sample.name]

    # Assert
    assert isinstance(actual_value, int)
    assert actual_value == expected_value
