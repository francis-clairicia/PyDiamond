# -*- coding: Utf-8 -*-

from __future__ import annotations

import random
from typing import TYPE_CHECKING, Any, Iterator, MutableMapping, Sequence

from pydiamond._patch.plugins.environment import check_booleans

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pydiamond._patch.plugins.environment import ArrangePygameEnvironmentBeforeImport, VerifyBooleanEnvironmentVariables

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.fixture(autouse=True)
def fake_environ(monkeypatch: MonkeyPatch) -> MutableMapping[str, str]:
    import os

    fake_env = dict(os.environ)
    monkeypatch.setattr(os, "environ", fake_env)
    return fake_env


@pytest.fixture
def mock_check_booleans(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("pydiamond._patch.plugins.environment.check_booleans")


@pytest.mark.functional
class TestArrangePygameEnvironment:
    @pytest.fixture
    @staticmethod
    def patch(fake_environ: MutableMapping[str, str]) -> Iterator[ArrangePygameEnvironmentBeforeImport]:
        from pydiamond._patch.plugins.environment import ArrangePygameEnvironmentBeforeImport

        patch = ArrangePygameEnvironmentBeforeImport()
        patch.setup()
        assert patch.environ is fake_environ
        yield patch
        patch.teardown()

    @pytest.mark.parametrize(
        "environ_var_value",
        [
            ("PYGAME_HIDE_SUPPORT_PROMPT", "1"),
            ("SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS", "1"),
            ("PYGAME_FREETYPE", "1"),
        ],
        ids=lambda t: "{0}={1}".format(*t),
    )
    @pytest.mark.usefixtures("mock_check_booleans")
    def test__run__set_default_values_in_environ(
        self,
        environ_var_value: tuple[str, str],
        patch: ArrangePygameEnvironmentBeforeImport,
    ) -> None:
        # Arrange
        import os

        env_var, env_value = environ_var_value
        os.environ.pop(env_var, None)

        # Act
        patch.run()

        # Assert
        assert env_var in os.environ
        assert os.environ[env_var] == env_value

    @pytest.mark.parametrize(
        "environ_var_value",
        [
            ("PYGAME_HIDE_SUPPORT_PROMPT", False),
            ("SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS", False),
            ("PYGAME_FREETYPE", True),
        ],
        ids=lambda t: "{0}={1}".format(*t),
    )
    @pytest.mark.usefixtures("mock_check_booleans")
    def test__run__overrides_user_value(
        self,
        environ_var_value: tuple[str, bool],
        patch: ArrangePygameEnvironmentBeforeImport,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        import os

        env_var, must_override = environ_var_value
        sentinel: Any = getattr(mocker.sentinel, f"ENV_{env_var}")
        os.environ[env_var] = sentinel

        # Act
        patch.run()

        # Assert
        if must_override:
            assert os.environ[env_var] is not sentinel
        else:
            assert os.environ[env_var] is sentinel

    def test__run__calls_check_booleans_for_overridden_values(
        self,
        patch: ArrangePygameEnvironmentBeforeImport,
        mock_check_booleans: MagicMock,
    ) -> None:
        # Arrange
        import os

        # Act
        patch.run()

        # Assert
        mock_check_booleans.assert_called_once_with(
            os.environ,
            only=[
                "PYGAME_HIDE_SUPPORT_PROMPT",
                "PYGAME_FREETYPE",
                "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
            ],
        )


@pytest.mark.functional
class TestVerifyBooleanEnvironmentVariables:
    @pytest.fixture
    @staticmethod
    def patch(fake_environ: MutableMapping[str, str]) -> Iterator[VerifyBooleanEnvironmentVariables]:
        from pydiamond._patch.plugins.environment import VerifyBooleanEnvironmentVariables

        patch = VerifyBooleanEnvironmentVariables()
        patch.setup()
        assert patch.environ is fake_environ
        yield patch
        patch.teardown()

    def test__run__calls_check_booleans_excluding_already_checked(
        self,
        patch: ArrangePygameEnvironmentBeforeImport,
        mock_check_booleans: MagicMock,
    ) -> None:
        # Arrange
        import os

        # Act
        patch.run()

        # Assert
        mock_check_booleans.assert_called_once_with(
            os.environ,
            exclude=[
                "PYGAME_HIDE_SUPPORT_PROMPT",
                "PYGAME_FREETYPE",
                "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
            ],
        )


BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES: list[str] = [  # Copied from environment.py plugin
    "PYGAME_BLEND_ALPHA_SDL2",
    "PYGAME_FREETYPE",
    "PYGAME_HIDE_SUPPORT_PROMPT",
    "SDL_HINT_JOYSTICK_ALLOW_BACKGROUND_EVENTS",
    "SDL_VIDEO_CENTERED",
    "SDL_VIDEO_ALLOW_SCREENSAVER",
]


class TestCheckBooleanEnvironmentVariables:
    @pytest.fixture(scope="class", params=BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES)
    @staticmethod
    def env_var(request: pytest.FixtureRequest) -> str:
        return str(getattr(request, "param"))

    @pytest.fixture
    @staticmethod
    def true_boolean() -> str:
        return "1"

    @pytest.fixture
    @staticmethod
    def false_boolean() -> str:
        return "0"

    @pytest.fixture(params=["0", "1"], ids=repr)
    @staticmethod
    def valid_boolean(request: pytest.FixtureRequest) -> str:
        return str(getattr(request, "param"))

    @pytest.fixture(params=["5", "Really not a boolean value", "00", "11", " 0 ", " 1 ", ""], ids=repr)
    @staticmethod
    def invalid_boolean(request: pytest.FixtureRequest) -> str:
        return str(getattr(request, "param"))

    def test__check_booleans__does_nothing_for_true_value(self, env_var: str, true_boolean: str) -> None:
        # Arrange
        environ: dict[str, str] = {env_var: true_boolean}

        # Act
        check_booleans(environ)

        # Assert
        assert env_var in environ
        assert environ[env_var] == true_boolean

    def test__check_booleans__remove_var_from_mapping_for_false_value(self, env_var: str, false_boolean: str) -> None:
        # Arrange
        environ: dict[str, str] = {env_var: false_boolean}

        # Act
        check_booleans(environ)

        # Assert
        assert env_var not in environ

    def test__check_booleans__raise_error_for_other_value(self, env_var: str, invalid_boolean: str) -> None:
        # Arrange
        environ: dict[str, str] = {env_var: invalid_boolean}

        # Act & Assert
        with pytest.raises(ValueError, match=f"Invalid value for {env_var!r} environment variable: {invalid_boolean}"):
            check_booleans(environ)

    @pytest.mark.parametrize(
        "sequence",
        list(
            random.sample(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES, k=k + 1) for k in range(len(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES))
        ),
    )
    def test__check_booleans__check_only_for_specific_environment_variables(
        self,
        sequence: Sequence[str],
        invalid_boolean: str,
        valid_boolean: str,
    ) -> None:
        # Arrange
        other_env_values = set(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES) - set(sequence)
        environ: dict[str, str] = {v: valid_boolean for v in sequence} | {v: invalid_boolean for v in other_env_values}

        # Act
        check_booleans(environ, only=sequence)

        # Assert
        # There is no raise ? Success !

    def test__check_booleans__raise_error_if_only_argument_is_empty(self) -> None:
        # Arrange
        environ: dict[str, str] = {}

        # Act & Assert
        with pytest.raises(ValueError, match=r"'only' argument: Empty sequence"):
            check_booleans(environ, only=())

    @pytest.mark.parametrize(
        "sequence",
        list(
            random.sample(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES, k=k + 1) for k in range(len(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES))
        ),
    )
    def test__check_booleans__do_not_check_for_excluded_environment_variables(
        self,
        sequence: Sequence[str],
        invalid_boolean: str,
        valid_boolean: str,
    ) -> None:
        # Arrange
        other_env_values = set(BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES) - set(sequence)
        environ: dict[str, str] = {v: invalid_boolean for v in sequence} | {v: valid_boolean for v in other_env_values}

        # Act
        check_booleans(environ, exclude=sequence)

        # Assert
        # There is no raise ? Success !

    def test__check_booleans__mutually_exclusive_parameters(self) -> None:
        # Arrange
        environ: dict[str, str] = {}

        # Act & Assert
        with pytest.raises(TypeError, match=r"Invalid parameters"):
            check_booleans(environ, only=BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES, exclude=BOOLEAN_PYGAME_ENVIRONMENT_VARIABLES)  # type: ignore[call-overload]
