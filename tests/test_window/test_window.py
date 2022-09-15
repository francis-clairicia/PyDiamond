# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

from pydiamond.window.display import Window, WindowError

import pygame
import pytest

from ..mock.pygame.display import MockDisplayModule

if TYPE_CHECKING:
    from pygame.surface import Surface
    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.mark.usefixtures("mock_pygame_event_module", "mock_pygame_mouse_module")
class TestWindow:
    @pytest.fixture(scope="class", autouse=True)
    @staticmethod
    def init_pygame_display_module() -> Iterator[Surface]:
        """Needed for Surface.convert, and mock it is too hard"""
        pygame.display.init()
        screen = pygame.display.set_mode()
        yield screen
        pygame.display.quit()

    @pytest.fixture(autouse=True)
    @staticmethod
    def set_mode_return_value(init_pygame_display_module: Surface, mock_pygame_display_module: MockDisplayModule) -> None:
        def set_mode(*args: Any, **kwargs: Any) -> Surface:
            mock_pygame_display_module.get_surface.return_value = init_pygame_display_module
            return init_pygame_display_module

        mock_pygame_display_module.set_mode.side_effect = set_mode
        mock_pygame_display_module.get_surface.return_value = None

    def test__init__default_arguments(self, monkeypatch: MonkeyPatch, mock_pygame_display_module: MockDisplayModule) -> None:
        # Arrange
        monkeypatch.setattr(Window, "DEFAULT_TITLE", "A beautiful title")

        # Act
        window = Window()

        # Assert
        mock_pygame_display_module.set_caption.assert_called_with("A beautiful title")
        assert window.size == (0, 0)
        assert not window.resizable
        assert not window.fullscreen
        assert not window.vsync

    def test__init__with_arguments(self, mock_pygame_display_module: MockDisplayModule) -> None:
        # Arrange
        from pydiamond.window.display import Window

        # Act
        window = Window(title="A very beautiful title", size=(1920, 1080))

        # Assert
        mock_pygame_display_module.set_caption.assert_called_with("A very beautiful title")
        assert window.size == (0, 0)  # Window not initialized so this must be true

    def test__init__resizable_window(self) -> None:
        # Arrange

        # Act
        window = Window(resizable=True)

        # Assert
        assert window.resizable

    def test__init__fullscreen_window(self) -> None:
        # Arrange

        # Act
        window = Window(fullscreen=True)

        # Assert
        assert window.fullscreen

    def test__init__vertical_sync_enabled(self) -> None:
        # Arrange

        # Act
        window = Window(vsync=True)

        # Assert
        assert window.vsync

    def test__init__mutually_exclusive_resizable_and_fullscreen(self) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(WindowError, match=r"Choose between resizable or fullscreen window, both cannot exist"):
            _ = Window(resizable=True, fullscreen=True)

    def test__init__mutually_exclusive_size_and_fullscreen(self) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(WindowError, match=r"'size' parameter must not be given if 'fullscreen' is set"):
            _ = Window(size=(640, 480), fullscreen=True)

    def test__open__pygame_display_init_and_quit(self, mock_pygame_display_module: MockDisplayModule) -> None:
        # Arrange

        window = Window()

        # Act & Assert
        with window.open():

            mock_pygame_display_module.init.assert_called()
            mock_pygame_display_module.quit.assert_not_called()

        mock_pygame_display_module.init.assert_called_once()
        mock_pygame_display_module.quit.assert_called_once()

    @pytest.mark.parametrize(
        ("size", "resizable", "fullscreen", "vsync", "expected_flags"),
        [
            pytest.param(None, False, False, False, 0, id="None, False, False, False, NOFLAGS"),
            pytest.param(None, True, False, False, pygame.RESIZABLE, id="None, True, False, False, RESIZABLE"),
            pytest.param(None, False, True, False, pygame.FULLSCREEN, id="None, False, True, False, FULLSCREEN"),
            pytest.param(None, False, False, True, 0, id="None, False, False, True, NOFLAGS"),
            pytest.param(None, True, False, True, pygame.RESIZABLE, id="None, True, False, True, RESIZABLE"),
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
        size: tuple[int, int] | None,
        resizable: bool,
        fullscreen: bool,
        vsync: bool,
        expected_flags: int,
        mock_pygame_display_module: MockDisplayModule,
    ) -> None:
        # Arrange
        if size is None:
            expected_size = (0, 0) if fullscreen else Window.DEFAULT_SIZE
        else:
            expected_size = size

        window = Window(size=size, resizable=resizable, fullscreen=fullscreen, vsync=vsync)

        # Act & Assert
        with window.open():

            mock_pygame_display_module.set_mode.assert_called_once_with(expected_size, flags=expected_flags, vsync=int(vsync))

    def test__enter__context_manager_return_reference_to_window(self) -> None:
        # Arrange

        window = Window()

        # Act & Assert
        with window as window_ref:

            assert window_ref is window

    def test__enter__calls_window_open(self, mocker: MockerFixture) -> None:
        # Arrange
        window = Window()
        mock_window_open = mocker.patch.object(window, "open")

        # Act
        with window:
            pass

        # Assert
        mock_window_open.assert_called_once()

    @pytest.mark.parametrize("error", [pytest.param(pygame.error, id="pygame.error"), ValueError, KeyError, ZeroDivisionError])
    def test__open__do_not_call_pygame_display_quit_on_init_error(
        self, error: type[Exception], mock_pygame_display_module: MockDisplayModule
    ) -> None:
        # Arrange

        mock_pygame_display_module.init.side_effect = error

        window = Window()

        # Act
        with pytest.raises(error):
            with window.open():
                pass

        # Assert
        mock_pygame_display_module.quit.assert_not_called()

    @pytest.mark.parametrize("error", ["set_mode failed", "window_init failed"])
    def test__open__always_call_pygame_display_quit_on_internal_setup_error(
        self, error: str, mocker: MockerFixture, mock_pygame_display_module: MockDisplayModule
    ) -> None:
        # Arrange

        window = Window()

        match error:
            case "set_mode failed":
                mock_pygame_display_module.set_mode.side_effect = pygame.error(error)
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

        window = Window()
        mock_window_init = mocker.patch.object(window, "__window_init__")
        mock_window_quit = mocker.patch.object(window, "__window_quit__")

        # Act & Assert
        with window.open():

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
