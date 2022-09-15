# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Callable

from pydiamond.audio.mixer import Mixer, MixerParams

import pygame
import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

    from ..mock.pygame.mixer import MockMixerModule


class TestMixer:
    @pytest.fixture(scope="class", autouse=True)
    @staticmethod
    def accept_setattr_on_mixer(class_mocker: MockerFixture) -> None:
        class_mocker.patch.object(type(Mixer), "__setattr__", type.__setattr__)

    @pytest.fixture
    @staticmethod
    def mixer_init_default_side_effect(mock_pygame_mixer_module: MockMixerModule) -> None:
        # Mixer.init() will first check if pygame.mixer is initialized, then return the used params
        mock_pygame_mixer_module.get_init.side_effect = [None, (0, 0, 0)]

    @pytest.fixture(autouse=True)
    @staticmethod
    def mock_music_stream(mocker: MockerFixture) -> MagicMock:
        return mocker.patch("pydiamond.audio.music.MusicStream", autospec=True)

    @pytest.mark.usefixtures("mixer_init_default_side_effect")
    def test__init__pygame_mixer_init_and_quit(self, mock_pygame_mixer_module: MockMixerModule) -> None:
        # Arrange

        # Act & Assert
        with Mixer.init():

            mock_pygame_mixer_module.init.assert_called()
            mock_pygame_mixer_module.quit.assert_not_called()

        mock_pygame_mixer_module.init.assert_called_once()
        mock_pygame_mixer_module.quit.assert_called_once()

    @pytest.mark.usefixtures("mixer_init_default_side_effect")
    def test__init__pygame_mixer_init_params(self, mock_pygame_mixer_module: MockMixerModule) -> None:
        # Arrange

        ## We do not check for every combination as pygame itself do not do it
        ## See https://github.com/pygame/pygame/blob/58c4d07434df5d6c6362c8a73609e2b4149ec7ae/test/mixer_test.py#L30
        CONFIG = {"frequency": 44100, "size": 32, "channels": 2, "allowedchanges": 0}

        # Act
        with Mixer.init(**CONFIG):
            pass

        # Assert
        mock_pygame_mixer_module.init.assert_called_once_with(**CONFIG)

    @pytest.mark.usefixtures("mixer_init_default_side_effect")
    def test__init__yields_output_from_Mixer_get_init(self, mocker: MockerFixture, sentinel: Any) -> None:
        # Arrange
        mocker.patch.object(Mixer, "get_init", return_value=sentinel.Mixer_get_init)

        # Act
        with Mixer.init() as mixer_params:
            pass

        # Assert
        assert mixer_params is sentinel.Mixer_get_init

    def test__init__raises_pygame_error_if_already_initialized(self, mock_pygame_mixer_module: MockMixerModule) -> None:
        # Arrange
        mock_pygame_mixer_module.get_init.return_value = (44100, -16, 2)  # Simulate default initialization

        # Act & Assert
        with pytest.raises(pygame.error, match=r"Mixer module already initialized"):
            with Mixer.init():
                pass

    @pytest.mark.parametrize(
        "error",
        [
            pytest.param(pygame.error, id="pygame.error"),
            ValueError,
            KeyError,
            ZeroDivisionError,
        ],
    )
    @pytest.mark.usefixtures("mixer_init_default_side_effect")
    def test__init__do_not_call_pygame_mixer_quit_on_init_error(
        self, error: type[Exception], mock_pygame_mixer_module: MockMixerModule
    ) -> None:
        # Arrange
        mock_pygame_mixer_module.init.side_effect = error

        # Act
        with pytest.raises(error):
            with Mixer.init():
                pass

        # Assert
        mock_pygame_mixer_module.quit.assert_not_called()

    def test__get_init__return_mixer_params(self, mock_pygame_mixer_module: MockMixerModule, sentinel: Any) -> None:
        # Arrange
        mock_pygame_mixer_module.get_init.return_value = (
            sentinel.Mixer_get_init_frequency,
            sentinel.Mixer_get_init_size,
            sentinel.Mixer_get_init_channels,
        )

        # Act
        mixer_params = Mixer.get_init()

        # Assert
        assert mixer_params is not None
        assert isinstance(mixer_params, MixerParams)
        assert mixer_params.frequency is sentinel.Mixer_get_init_frequency
        assert mixer_params.size is sentinel.Mixer_get_init_size
        assert mixer_params.channels is sentinel.Mixer_get_init_channels

    def test__get_init__return_None_if_mixer_not_initialized(self, mock_pygame_mixer_module: MockMixerModule) -> None:
        # Arrange
        mock_pygame_mixer_module.get_init.return_value = None

        # Act
        mixer_params = Mixer.get_init()

        # Assert
        assert mixer_params is None

    @pytest.mark.parametrize(
        ["mixer_cls_method_name", "pygame_mixer_function_name", "args"],
        [
            pytest.param("is_busy", "get_busy", None, id="is_busy"),
            pytest.param("stop_all_sounds", "stop", None, id="stop"),
            pytest.param("pause_all_sounds", "pause", None, id="pause"),
            pytest.param("unpause_all_sounds", "unpause", None, id="unpause"),
            pytest.param("fadeout_all_sounds", "fadeout", (5,), id="fadeout(5)"),
            pytest.param("set_num_channels", "set_num_channels", (12,), id="set_num_channels(12)"),
            pytest.param("get_num_channels", "get_num_channels", None, id="get_num_channels"),
            pytest.param("find_channel", "find_channel", (False,), id="find_channel(False)"),
            pytest.param("find_channel", "find_channel", (True,), id="find_channel(True)"),
        ],
    )
    def test__method__pass_through(
        self,
        mixer_cls_method_name: str,
        pygame_mixer_function_name: str,
        args: tuple[Any, ...] | None,
        mock_pygame_mixer_module: MockMixerModule,
        sentinel: Any,
    ) -> None:
        # Arrange
        mock_func: MagicMock = getattr(mock_pygame_mixer_module, pygame_mixer_function_name)
        sentinel_value: Any = getattr(sentinel, f"Mixer_{mixer_cls_method_name}")
        mock_func.return_value = sentinel_value
        mixer_cls_method: Callable[..., Any] = getattr(Mixer, mixer_cls_method_name)
        if args is None:
            args = ()

        # Act
        actual_value: Any = mixer_cls_method(*args)

        # Assert
        mock_func.assert_called_once_with(*args)
        assert actual_value is sentinel_value

    @pytest.mark.parametrize("num_channels", [0, 1, 2, 8, 32])
    def test__get_channels__list_Channel_objects_up_to_get_num_channels(
        self,
        num_channels: int,
        mock_pygame_mixer_module: MockMixerModule,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        mock_channel = mocker.patch("pydiamond.audio.mixer.Channel")
        mock_pygame_mixer_module.get_num_channels.return_value = num_channels

        # Act
        channels = Mixer.get_channels()

        # Assert
        assert mock_channel.mock_calls == list(map(mocker.call, range(0, num_channels)))
        assert len(channels) == num_channels
