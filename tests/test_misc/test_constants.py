# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from pydiamond.audio.mixer import AllowedAudioChanges, AudioFormat
from pydiamond.graphics.font import FontStyle

import pytest

if TYPE_CHECKING:
    from enum import Enum


class EnumConstantSample(NamedTuple):
    enum: type[Enum]
    name: str
    constant_name: str
    module: str


def enum_sample(
    enum: type[Enum],
    constant_name: dict[str, str] | Callable[[str], str] | None = None,
    module: str = "pygame.constants",
) -> list[EnumConstantSample]:
    if constant_name is None:
        constant_name = lambda name: name
    elif not callable(constant_name):
        _associations = constant_name
        constant_name = lambda name: _associations.get(name, name)
    return [EnumConstantSample(enum, member, constant_name(member), module) for member in enum.__members__]


@pytest.mark.parametrize(
    "sample",
    [
        *enum_sample(AudioFormat),
        *enum_sample(AllowedAudioChanges, constant_name=lambda name: f"AUDIO_ALLOW_{name}_CHANGE"),
        *enum_sample(FontStyle, constant_name=lambda name: f"STYLE_{name}", module="pygame.freetype"),
    ],
    ids=lambda sample: f"{sample.enum.__name__}.{sample.name}=={sample.module}.{sample.constant_name}",
)
def test__enum_member__value_from_pygame_constants(sample: EnumConstantSample) -> None:
    # Arrange
    module = importlib.import_module(sample.module)
    expected_value: int = getattr(module, sample.constant_name)
    assert isinstance(expected_value, int)

    # Act
    actual_value: Any = sample.enum[sample.name].value

    # Assert
    assert isinstance(actual_value, int)
    assert actual_value == expected_value
