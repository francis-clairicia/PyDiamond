from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any

from pydiamond._patch.plugins.pygame_patch import PygamePatch

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestPygamePatch:
    @pytest.fixture
    def mock_pygame_event_module(self, mocker: MockerFixture) -> MagicMock:
        ## Do not use the default mock_pygame_event_module as this fixture mock individually each function defined
        from pygame.event import Event

        self.Event = Event
        return mocker.patch("pygame.event")

    @pytest.fixture
    @staticmethod
    def patch(mock_pygame_event_module: Any) -> Iterator[PygamePatch]:
        patch = PygamePatch()
        patch.setup()
        assert patch.event is mock_pygame_event_module
        assert not patch._event_name_patched()
        assert not patch._event_set_blocked_patched()
        assert not patch._event_post_patched()
        yield patch
        patch.teardown()

    def test____run____apply_wrapper_to_pygame_functions(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
    ) -> None:
        # Arrange
        import pygame

        mock_pygame_event_event_name: Any = mock_pygame_event_module.event_name
        mock_pygame_event_set_blocked: Any = mock_pygame_event_module.set_blocked
        mock_pygame_event_post: Any = mock_pygame_event_module.post

        # Act
        patch.run()

        # Assert
        assert pygame.event.event_name is not mock_pygame_event_event_name
        assert getattr(pygame.event.event_name, "__wrapped__") is mock_pygame_event_event_name

        assert pygame.event.set_blocked is not mock_pygame_event_set_blocked
        assert getattr(pygame.event.set_blocked, "__wrapped__") is mock_pygame_event_set_blocked

        assert pygame.event.post is not mock_pygame_event_post
        assert getattr(pygame.event.post, "__wrapped__") is mock_pygame_event_post

    def test____run____make_pygame_event_event_name_customizable(
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

    def test____run____forbids_a_list_of_events_to_be_blocked(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import pygame

        mock_pygame_event_event_name: MagicMock = mock_pygame_event_module.event_name

        def _pygame_event_event_name_side_effect(event_type: int) -> str:
            match event_type:
                case pygame.WINDOWCLOSE:
                    return "WindowClose"
                case pygame.VIDEORESIZE:
                    return "VideoResize"
                case _:
                    raise SystemError("Unexpected value")

        mock_pygame_event_event_name.side_effect = _pygame_event_event_name_side_effect

        mock_pygame_event_set_blocked: MagicMock = mock_pygame_event_module.set_blocked

        ## the set_blocked() wrapper will try to convert received values to int, as the real function declares to take
        ## 'SupportsInt' argument
        ## But try int(_SentinelObject) will raise a TypeError, so we replace the class for the tests
        mocker.patch("pydiamond._patch.plugins.pygame_patch.int", lambda obj: obj)

        expected_forbidden_events = (pygame.WINDOWCLOSE,)

        # Act
        patch.run()

        # Assert
        assert getattr(pygame.event.set_blocked, "__get_forbidden_events__")() == expected_forbidden_events

        ## Single event type
        pygame.event.set_blocked(pygame.KEYDOWN)
        mock_pygame_event_set_blocked.assert_called_with(pygame.KEYDOWN)
        pygame.event.set_blocked(pygame.MOUSEBUTTONUP)
        mock_pygame_event_set_blocked.assert_called_with(pygame.MOUSEBUTTONUP)

        mock_pygame_event_set_blocked.reset_mock()  # needed to use assert_not_called() later
        with pytest.raises(ValueError, match=r"WindowClose must always be allowed"):
            pygame.event.set_blocked(pygame.WINDOWCLOSE)
        mock_pygame_event_set_blocked.assert_not_called()
        mock_pygame_event_event_name.assert_called_with(pygame.WINDOWCLOSE)
        mock_pygame_event_set_blocked.assert_not_called()

        ## Sequence of event types
        pygame.event.set_blocked((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        mock_pygame_event_set_blocked.assert_called_with((pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP))
        pygame.event.set_blocked([pygame.KEYDOWN, pygame.KEYUP])
        mock_pygame_event_set_blocked.assert_called_with((pygame.KEYDOWN, pygame.KEYUP))  # implicitly converted to tuple

        mock_pygame_event_set_blocked.reset_mock()  # needed to use assert_not_called() later
        with pytest.raises(ValueError, match=r"WindowClose must always be allowed"):
            pygame.event.set_blocked([pygame.KEYDOWN, pygame.WINDOWCLOSE, pygame.KEYUP])
        mock_pygame_event_set_blocked.assert_not_called()

        ## 'None' (which means all events)
        mock_pygame_event_set_blocked.reset_mock()  # needed to use assert_not_called() later
        with pytest.raises(ValueError, match=r"WindowClose must always be allowed"):
            pygame.event.set_blocked(None)
        mock_pygame_event_set_blocked.assert_not_called()

    def test____run____forbids_a_list_of_events_to_be_posted(
        self,
        patch: PygamePatch,
        mock_pygame_event_module: MagicMock,
        mock_pygame_mixer_music_module: MagicMock,
    ) -> None:
        # Arrange
        import pygame

        Event = self.Event

        mock_pygame_event_event_name: MagicMock = mock_pygame_event_module.event_name

        def _pygame_event_event_name_side_effect(event_type: int) -> str:
            match event_type:
                case pygame.WINDOWCLOSE:
                    return "WindowClose"
                case _:
                    raise SystemError("Unexpected value")

        mock_pygame_event_event_name.side_effect = _pygame_event_event_name_side_effect

        mock_pygame_event_post: MagicMock = mock_pygame_event_module.post

        expected_forbidden_events = (pygame.WINDOWCLOSE,)

        # Act
        patch.run()

        # Assert
        assert getattr(pygame.event.post, "__forbidden_events__") == expected_forbidden_events

        pygame.event.post(Event(pygame.KEYDOWN, validated=True))
        mock_pygame_event_post.assert_called_with(Event(pygame.KEYDOWN, validated=True))
        pygame.event.post(Event(pygame.MOUSEBUTTONUP, pos=(-1, -1)))
        mock_pygame_event_post.assert_called_with(Event(pygame.MOUSEBUTTONUP, pos=(-1, -1)))

        mock_pygame_event_post.reset_mock()  # needed to use assert_not_called() later
        with pytest.raises(ValueError, match=r"WindowClose cannot be added externally"):
            pygame.event.post(Event(pygame.WINDOWCLOSE))
        mock_pygame_event_post.assert_not_called()
        mock_pygame_event_event_name.assert_called_with(pygame.WINDOWCLOSE)
