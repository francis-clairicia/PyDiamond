# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING, Any, Callable, NamedTuple

from pydiamond.audio.mixer import AllowedAudioChanges, AudioFormat
from pydiamond.graphics.font import FontStyle
from pydiamond.graphics.renderer import BlendMode
from pydiamond.network.socket import AddressFamily, ShutdownFlag
from pydiamond.window.controller import ControllerAxis, ControllerButton
from pydiamond.window.cursor import SystemCursor
from pydiamond.window.event import BuiltinEventType
from pydiamond.window.keyboard import Key, KeyModifiers
from pydiamond.window.mouse import MouseButton

import pytest
from pygame.constants import NOEVENT, USEREVENT

if TYPE_CHECKING:
    from enum import Enum


class EnumConstantSample(NamedTuple):
    enum: type[Enum]
    name: str
    constant_name: str
    module: str

    @property
    def value(self) -> Any:
        return self.enum[self.name].value

    @property
    def constant_value(self) -> Any:
        module = importlib.import_module(self.module)
        return getattr(module, self.constant_name)


def enum_sample(
    enum: type[Enum],
    constant_name: dict[str, str] | Callable[[str], str] | None = None,
    module: str = "pygame.constants",
    predicate: Callable[[EnumConstantSample], bool] = lambda _: True,
) -> list[EnumConstantSample]:
    if constant_name is None:
        constant_name = lambda name: name
    elif not callable(constant_name):
        _associations = constant_name
        constant_name = lambda name: _associations.get(name, name)
    return list(
        filter(predicate, (EnumConstantSample(enum, member, constant_name(member), module) for member in enum.__members__))
    )


@pytest.mark.parametrize(
    "sample",
    [
        # pydiamond.audio
        *enum_sample(AudioFormat),
        *enum_sample(AllowedAudioChanges, constant_name=lambda name: f"AUDIO_ALLOW_{name}_CHANGE"),
        # pydiamond.graphics
        *enum_sample(FontStyle, constant_name=lambda name: f"STYLE_{name}", module="pygame.freetype"),
        *enum_sample(BlendMode, constant_name=lambda name: f"BLEND_{name}", predicate=lambda sample: sample.name != "NONE"),
        # pydiamond.network
        *enum_sample(AddressFamily, module="socket"),
        *enum_sample(ShutdownFlag, module="socket"),
        # pydiamond.window
        *enum_sample(ControllerAxis, constant_name=lambda name: f"CONTROLLER_AXIS_{name.replace('_', '')}"),
        *enum_sample(ControllerButton, constant_name=lambda name: f"CONTROLLER_BUTTON_{name.removeprefix('BUTTON_')}"),
        *enum_sample(SystemCursor, constant_name=lambda name: f"SYSTEM_CURSOR_{name}"),
        *enum_sample(BuiltinEventType, predicate=lambda sample: NOEVENT < sample.value < USEREVENT),
        *enum_sample(Key),
        *enum_sample(KeyModifiers),
        *enum_sample(MouseButton, constant_name=lambda name: f"BUTTON_{name}"),
    ],
    ids=lambda sample: f"{sample.enum.__name__}.{sample.name}=={sample.module}.{sample.constant_name}",
)
def test____enum_member____value_from_constant(sample: EnumConstantSample) -> None:
    # Arrange
    expected_value = sample.constant_value

    # Act
    actual_value: Any = sample.value

    # Assert
    assert actual_value == expected_value
