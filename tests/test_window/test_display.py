# -*- coding: Utf-8 -*

from __future__ import annotations

from typing import TYPE_CHECKING

import pygame
import pytest

from ..mock.pygame.display import MockDisplayModule

if TYPE_CHECKING:
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.mark.unit
class TestWindowUnit:
    def test__init__default_arguments(self, monkeypatch: MonkeyPatch) -> None:
        # Arrange
        from py_diamond.window.display import Window

        monkeypatch.setattr(Window, "DEFAULT_TITLE", "A beautiful title")

        # Act
        window = Window()

        # Assert
        assert window.get_title() == "A beautiful title"
        assert window.size == (0, 0)
        assert not window.resizable
        assert not window.fullscreen
        assert not window.vsync

    def test__init__with_arguments(self) -> None:
        # Arrange
        from py_diamond.window.display import Window

        # Act
        window = Window(title="A very beautiful title", size=(1920, 1080))

        # Assert
        assert window.get_title() == "A very beautiful title"
        assert window.size == (0, 0)  # Window not initialized so this must be true

    def test__init__resizable_window(self) -> None:
        # Arrange
        from py_diamond.window.display import Window

        # Act
        window = Window(resizable=True)

        # Assert
        assert window.resizable

    def test__init__fullscreen_window(self) -> None:
        # Arrange
        from py_diamond.window.display import Window

        # Act
        window = Window(fullscreen=True)

        # Assert
        assert window.fullscreen

    def test__init__vertical_sync_enabled(self) -> None:
        # Arrange
        from py_diamond.window.display import Window

        # Act
        window = Window(vsync=True)

        # Assert
        assert window.vsync

    def test__init__mutually_exclusive_resizable_and_fullscreen(self) -> None:
        # Arrange
        from py_diamond.window.display import Window, WindowError

        # Act/Assert
        with pytest.raises(WindowError, match=r"Choose between resizable or fullscreen window, both cannot exist"):
            _ = Window(resizable=True, fullscreen=True)

    def test__init__mutually_exclusive_size_and_fullscreen(self) -> None:
        # Arrange
        from py_diamond.window.display import Window, WindowError

        # Act/Assert
        with pytest.raises(WindowError, match=r"'size' parameter must not be given if 'fullscreen' is set"):
            _ = Window(size=(640, 480), fullscreen=True)

    def test__open__pygame_display_init_and_quit(self, mock_pygame_display_module: MockDisplayModule) -> None:
        # Arrange
        from py_diamond.window.display import Window

        window = Window()

        # Act
        with window.open():

            # Assert
            mock_pygame_display_module.init.assert_called()
            mock_pygame_display_module.quit.assert_not_called()

        mock_pygame_display_module.init.assert_called_once()
        mock_pygame_display_module.quit.assert_called_once()

    @pytest.mark.parametrize(
        ("size", "resizable", "fullscreen", "vsync", "expected_flags"),
        [
            pytest.param((0, 0), False, False, False, 0, id="(0, 0), False, False, False, NOFLAGS"),
            pytest.param((0, 0), True, False, False, pygame.RESIZABLE, id="(0, 0), True, False, False, RESIZABLE"),
            pytest.param((0, 0), False, True, False, pygame.FULLSCREEN, id="(0, 0), False, True, False, FULLSCREEN"),
            pytest.param((0, 0), False, False, True, 0, id="(0, 0), False, False, True, NOFLAGS"),
            pytest.param((0, 0), True, False, True, pygame.RESIZABLE, id="(0, 0), True, False, True, RESIZABLE"),
            pytest.param((640, 480), False, False, False, 0, id="(640, 480), False, False, False, NOFLAGS"),
            pytest.param((640, 480), True, False, False, pygame.RESIZABLE, id="(640, 480), True, False, False, RESIZABLE"),
            pytest.param((640, 480), False, False, True, 0, id="(640, 480), False, False, True, NOFLAGS"),
            pytest.param((640, 480), True, False, True, pygame.RESIZABLE, id="(640, 480), True, False, True, RESIZABLE"),
            pytest.param((1920, 1080), False, False, False, 0, id="(1920, 1080), False, False, False, NOFLAGS"),
            pytest.param((1920, 1080), True, False, False, pygame.RESIZABLE, id="(1920, 1080), True, False, False, RESIZABLE"),
            pytest.param((1920, 1080), False, False, True, 0, id="(1920, 1080), False, False, True, NOFLAGS"),
            pytest.param((1920, 1080), True, False, True, pygame.RESIZABLE, id="(1920, 1080), True, False, True, RESIZABLE"),
        ],
    )
    def test__open__specific_mode(
        self,
        size: tuple[int, int],
        resizable: bool,
        fullscreen: bool,
        vsync: bool,
        expected_flags: int,
        mock_pygame_display_module: MockDisplayModule,
    ) -> None:
        # Arrange
        from py_diamond.window.display import Window

        window = Window(size=size, resizable=resizable, fullscreen=fullscreen, vsync=vsync)

        # Act
        with window.open():

            # Assert
            mock_pygame_display_module.set_mode.assert_called_once_with(size, flags=expected_flags, vsync=int(vsync))

    def test__open__context_manager_return_reference_to_window(self) -> None:
        # Arrange
        from py_diamond.window.display import Window

        window = Window()

        # Act
        with window.open() as window_ref:

            # Assert
            assert window_ref is window

    @pytest.mark.parametrize("error", [pytest.param(pygame.error, id="pygame.error"), ValueError, KeyError, ZeroDivisionError])
    def test__open__do_not_call_pygame_display_quit_on_init_error(
        self, error: type[Exception], mock_pygame_display_module: MockDisplayModule
    ) -> None:
        # Arrange
        from py_diamond.window.display import Window

        mock_pygame_display_module.init.side_effect = error

        window = Window()

        # Act
        with pytest.raises(error):
            with window.open():
                pass

        # Assert
        mock_pygame_display_module.quit.assert_not_called()

    @pytest.mark.parametrize("error", ["set_mode failed", "create_surface failed", "window_init failed"])
    def test__open__always_call_pygame_display_quit_on_internal_setup_error(
        self, error: str, mocker: MockerFixture, mock_pygame_display_module: MockDisplayModule
    ) -> None:
        # Arrange
        from py_diamond.window.display import Window

        window = Window()

        match error:
            case "set_mode failed":
                mock_pygame_display_module.set_mode.side_effect = pygame.error(error)
            case "create_surface failed":
                mocker.patch("py_diamond.window.display.create_surface", side_effect=pygame.error(error))
            case "window_init failed":
                mocker.patch.object(window, "__window_init__", side_effect=pygame.error(error))
            case _:
                raise SystemError("Invalid test setup")

        # Act
        with pytest.raises(pygame.error, match=error):
            with window.open():
                pass

        # Assert
        mock_pygame_display_module.quit.assert_called()

    def test__open__call_dunder_window_init_and_quit(self, mocker: MockerFixture) -> None:
        # Arrange
        from py_diamond.window.display import Window

        window = Window()
        mock_window_init = mocker.patch.object(window, "__window_init__")
        mock_window_quit = mocker.patch.object(window, "__window_quit__")

        # Act
        with window.open():

            # Assert
            mock_window_init.assert_called()
            mock_window_quit.assert_not_called()

        mock_window_init.assert_called_once()
        mock_window_quit.assert_called_once()

    def test__open__do_not_call_window_init_if_set_mode_failed(
        self,
        mocker: MockerFixture,
        mock_pygame_display_module: MockDisplayModule,
    ) -> None:
        # Arrange
        from py_diamond.window.display import Window

        window = Window()
        mock_pygame_display_module.set_mode.side_effect = pygame.error("Something happened")
        mock_window_init = mocker.patch.object(window, "__window_init__")
        mock_window_quit = mocker.patch.object(window, "__window_quit__")

        # Act
        with pytest.raises(pygame.error, match=r"Something happened"):
            with window.open():
                pass

        # Assert
        mock_window_init.assert_not_called()
        mock_window_quit.assert_not_called()