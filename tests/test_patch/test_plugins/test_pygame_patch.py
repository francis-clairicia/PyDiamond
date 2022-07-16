# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterator

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from py_diamond._patch.plugins.pygame_patch import PyDiamondEventPatch, PygamePatch

    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestPygamePatch:
    @pytest.fixture
    @staticmethod
    def mock_pygame_event_module(mocker: MockerFixture) -> MagicMock:
        ## Do not use the default mock_pygame_event_module as this fixture mock individually each function defined
        return mocker.patch("pygame.event")

    @pytest.fixture
    @staticmethod
    def mock_pygame_mixer_music_module(mocker: MockerFixture) -> MagicMock:
        ## Do not use the default mock_pygame_mixer_music_module as this fixture mock individually each function defined
        return mocker.patch("pygame.mixer.music")

    @pytest.fixture
    @staticmethod
    def patch(mock_pygame_event_module: Any, mock_pygame_mixer_music_module: Any) -> Iterator[PygamePatch]:
        from py_diamond._patch.plugins.pygame_patch import PygamePatch

        patch = PygamePatch()
        patch.setup()
        assert patch.event is mock_pygame_event_module  # type: ignore[misc]  # mypy think it's an assignment ??
        assert patch.music is mock_pygame_mixer_music_module  # type: ignore[misc]
        assert not patch._event_name_patched()
        assert not patch._event_set_blocked_patched()
        assert not patch._music_set_endevent_patched()
        yield patch
        patch.teardown()

    def test__run__apply_wrapper_to_pygame_functions(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
        mock_pygame_mixer_music_module: MagicMock,
    ) -> None:
        # Arrange
        import pygame

        mock_pygame_event_event_name: Any = mock_pygame_event_module.event_name
        mock_pygame_event_set_blocked: Any = mock_pygame_event_module.set_blocked
        mock_pygame_mixer_music_set_endevent: Any = mock_pygame_mixer_music_module.set_endevent

        # Act
        patch.run()

        # Assert
        assert pygame.mixer.music.set_endevent is not mock_pygame_mixer_music_set_endevent
        assert getattr(pygame.mixer.music.set_endevent, "__wrapped__") is mock_pygame_mixer_music_set_endevent

        assert pygame.event.event_name is not mock_pygame_event_event_name
        assert getattr(pygame.event.event_name, "__wrapped__") is mock_pygame_event_event_name

        assert pygame.event.set_blocked is not mock_pygame_event_set_blocked
        assert getattr(pygame.event.set_blocked, "__wrapped__") is mock_pygame_event_set_blocked

    def test__run__replace_music_end_event_by_a_custom_type_and_forbid_further_calls_to_set_endevent(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
        mock_pygame_mixer_music_module: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import pygame

        mock_pygame_event_custom_type: MagicMock = mock_pygame_event_module.custom_type

        sentinel_event_type = getattr(mocker.sentinel, "MusicEvent__custom_type")
        mock_pygame_event_custom_type.return_value = sentinel_event_type

        mock_pygame_mixer_music_set_endevent: MagicMock = mock_pygame_mixer_music_module.set_endevent
        mock_pygame_mixer_music_set_endevent.__qualname__ = "pygame.mixer.music.set_endevent"

        # Act
        patch.run()

        # Assert
        mock_pygame_event_custom_type.assert_called_once()
        mock_pygame_mixer_music_set_endevent.assert_called_once_with(sentinel_event_type)

        with pytest.raises(TypeError, match=r"Call to function pygame.mixer.music.set_endevent is forbidden"):
            pygame.mixer.music.set_endevent(sentinel_event_type)

    def test__run__make_pygame_event_event_name_customizable(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import pygame

        sentinel_default_value = getattr(mocker.sentinel, "pygame_event_default_value")
        sentinel_custom_value = getattr(mocker.sentinel, "pygame_event_custom_name")

        mock_pygame_event_event_name: MagicMock = mock_pygame_event_module.event_name
        mock_pygame_event_event_name.return_value = sentinel_default_value

        # Act
        patch.run()

        # Assert
        dispatch_table: dict[int, str] = getattr(pygame.event.event_name, "__event_name_dispatch_table__")
        assert isinstance(dispatch_table, dict)
        assert not dispatch_table  # by default, the dict must be empty

        assert pygame.event.event_name(12000) is sentinel_default_value
        dispatch_table[12000] = "Overriden value"
        assert pygame.event.event_name(12000) == "Overriden value"
        dispatch_table[12000] = sentinel_custom_value
        assert pygame.event.event_name(12000) is sentinel_custom_value
        dispatch_table[12000] = ""
        assert pygame.event.event_name(12000) is sentinel_default_value

    def test__run__forbids_a_list_of_events_to_be_blocked(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
        mock_pygame_mixer_music_module: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import pygame

        mock_pygame_event_event_name: MagicMock = mock_pygame_event_module.event_name

        def _pygame_event_event_name_side_effect(event_type: int) -> str:
            match event_type:
                case pygame.QUIT:
                    return "Quit"
                case pygame.VIDEORESIZE:
                    return "VideoResize"
                case mocker.sentinel.MusicEndEvent:
                    return "MusicEnd"
                case _:
                    raise SystemError("Unexpected value")

        mock_pygame_event_event_name.side_effect = _pygame_event_event_name_side_effect

        mock_pygame_event_custom_type: MagicMock = mock_pygame_event_module.custom_type
        mock_pygame_event_set_blocked: MagicMock = mock_pygame_event_module.set_blocked

        sentinel_event_type = getattr(mocker.sentinel, "MusicEndEvent")
        mock_pygame_event_custom_type.return_value = sentinel_event_type

        ## the set_blocked() wrapper will try to convert received values to int, as the real function declares to take
        ## 'SupportsInt' argument
        ## But try int(_SentinelObject) will raise a TypeError, so we replace the class for the tests
        mocker.patch("py_diamond._patch.plugins.pygame_patch.int", lambda obj: obj)

        mock_pygame_mixer_music_get_endevent: MagicMock = mock_pygame_mixer_music_module.get_endevent
        mock_pygame_mixer_music_set_endevent: MagicMock = mock_pygame_mixer_music_module.set_endevent

        mock_pygame_mixer_music_set_endevent.side_effect = lambda event_type: mock_pygame_mixer_music_get_endevent.configure_mock(
            return_value=event_type
        )
        expected_forbidden_events = (pygame.QUIT, pygame.VIDEORESIZE, sentinel_event_type)

        # Act
        patch.run()

        # Assert
        assert getattr(pygame.event.set_blocked, "__forbidden_events__") == expected_forbidden_events

        ## Single event type
        pygame.event.set_blocked(pygame.KEYDOWN)
        mock_pygame_event_set_blocked.assert_called_with(pygame.KEYDOWN)
        pygame.event.set_blocked(pygame.MOUSEBUTTONUP)
        mock_pygame_event_set_blocked.assert_called_with(pygame.MOUSEBUTTONUP)

        with pytest.raises(ValueError, match=r"Quit must always be allowed"):
            pygame.event.set_blocked(pygame.QUIT)
        mock_pygame_event_event_name.assert_called_with(pygame.QUIT)
        with pytest.raises(ValueError, match=r"VideoResize must always be allowed"):
            pygame.event.set_blocked(pygame.VIDEORESIZE)
        mock_pygame_event_event_name.assert_called_with(pygame.VIDEORESIZE)
        with pytest.raises(ValueError, match=r"MusicEnd must always be allowed"):
            pygame.event.set_blocked(sentinel_event_type)
        mock_pygame_event_event_name.assert_called_with(sentinel_event_type)

        ## Sequence of event types
        pygame.event.set_blocked((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        mock_pygame_event_set_blocked.assert_called_with((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        pygame.event.set_blocked([pygame.KEYDOWN, pygame.KEYUP])
        mock_pygame_event_set_blocked.assert_called_with((pygame.KEYDOWN, pygame.KEYUP))  # implicitly converted to tuple

        mock_pygame_event_set_blocked.reset_mock()  # needed to use assert_not_called() later
        with pytest.raises(ValueError, match=r"Quit, VideoResize must always be allowed"):
            pygame.event.set_blocked([pygame.KEYDOWN, pygame.QUIT, pygame.KEYUP, pygame.VIDEORESIZE])
        mock_pygame_event_set_blocked.assert_not_called()

        ## 'None' (which means all events)
        mock_pygame_event_set_blocked.reset_mock()  # needed to use assert_not_called() later
        with pytest.raises(ValueError, match=r"Quit, VideoResize, MusicEnd must always be allowed"):
            pygame.event.set_blocked(None)
        mock_pygame_event_set_blocked.assert_not_called()


@pytest.mark.functional
class TestPyDiamondEventPatch:
    @pytest.fixture
    @staticmethod
    def patch() -> Iterator[PyDiamondEventPatch]:
        from py_diamond._patch.plugins.pygame_patch import PyDiamondEventPatch

        patch = PyDiamondEventPatch()
        yield patch
        patch.teardown()

    def test__run__set_custom_name_to_event_name_dispatch_table(
        self,
        patch: PyDiamondEventPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        from py_diamond.window.event import BuiltinEventType

        import pygame

        mock_dispatch_table: MagicMock = mocker.patch.object(
            pygame.event.event_name,
            "__event_name_dispatch_table__",
            create=True,
            spec={},
        )
        assert isinstance(mock_dispatch_table, dict)

        mock_dispatch_table_setitem: MagicMock = getattr(mock_dispatch_table, "__setitem__")

        patch.setup()

        # Act
        patch.run()

        # Assert
        assert mock_dispatch_table_setitem.mock_calls == [
            mocker.call(BuiltinEventType.MUSICEND, "MusicEnd"),
            mocker.call(BuiltinEventType.SCREENSHOT, "Screenshot"),
        ]
