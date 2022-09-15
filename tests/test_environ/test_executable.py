# -*- coding: Utf-8 -*-

from __future__ import annotations

import os.path
from typing import TYPE_CHECKING

from pydiamond.environ.executable import get_executable_path, get_main_script_path, is_frozen_executable

import pytest

from ..mock.sys import mock_module

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.fixture
def mock_main_module(mocker: MockerFixture) -> MagicMock:
    return mock_module("__main__", mocker=mocker)


def test__get_main_script_path__returns_main_module_path_from_spec(mock_main_module: MagicMock) -> None:
    # Arrange
    expected_path = os.path.abspath("path/to/main/script.py")
    mock_main_module.__spec__.origin = expected_path

    # Act
    returned_path = get_main_script_path()

    # Assert
    assert returned_path == expected_path


def test__get_main_script_path__returns_main_module_path_from_dunder_file_attribute(mock_main_module: MagicMock) -> None:
    # Arrange
    expected_path = os.path.abspath("path/to/main/script.py")
    mock_main_module.__spec__.origin = None
    mock_main_module.__file__ = expected_path

    # Act
    returned_path = get_main_script_path()

    # Assert
    assert returned_path == expected_path


def test__get_main_script_path__returns_main_module_path_from_dunder_file_attribute_2(mock_main_module: MagicMock) -> None:
    # Arrange
    expected_path = os.path.abspath("path/to/main/script.py")
    mock_main_module.__spec__ = None
    mock_main_module.__file__ = expected_path

    # Act
    returned_path = get_main_script_path()

    # Assert
    assert returned_path == expected_path


def test__get_main_script_path__fallback_to_argv(mock_main_module: MagicMock, mocker: MockerFixture) -> None:
    # Arrange
    expected_path = os.path.abspath("path/to/main/script.py")
    mock_main_module.__spec__ = None
    mock_main_module.__file__ = None
    mocker.patch("sys.argv", [expected_path])

    # Act
    returned_path = get_main_script_path()

    # Assert
    assert returned_path == expected_path


def test__get_main_script__returns_empty_string_if_undefined(mock_main_module: MagicMock, mocker: MockerFixture) -> None:
    # Arrange
    mock_main_module.__spec__ = None
    mock_main_module.__file__ = None
    mocker.patch("sys.argv", [""])

    # Act
    returned_path = get_main_script_path()

    # Assert
    assert returned_path == ""


def test__get_main_script_path__the_impossible_became_true(monkeypatch: MonkeyPatch) -> None:
    # Arrange
    import sys

    monkeypatch.delitem(sys.modules, "__main__")

    # Act & Assert
    with pytest.raises(RuntimeError):
        _ = get_main_script_path()


class TestIsFrozenExecutable:
    def test__sys__has_frozen_attribute_to_True(self, mocker: MockerFixture) -> None:
        # Arrange
        mocker.patch("sys.frozen", True, create=True)

        # Act
        frozen = is_frozen_executable()

        # Assert
        assert frozen is True

    def test__sys__has_frozen_attribute_to_False(self, mocker: MockerFixture) -> None:
        # Arrange
        mocker.patch("sys.frozen", False, create=True)

        # Act
        frozen = is_frozen_executable()

        # Assert
        assert frozen is False

    def test__sys__does_not_have_frozen_attribute(self, monkeypatch: MonkeyPatch) -> None:
        # Arrange
        import sys

        monkeypatch.delattr(sys, "frozen", raising=False)

        # Act
        frozen = is_frozen_executable()

        # Assert
        assert frozen is False


def test__get_executable_path__returns_sys_executable_if_frozen(mocker: MockerFixture) -> None:
    # Arrange
    mocker.patch("sys.executable", mocker.sentinel.sys_executable)
    mock_get_main_script_path = mocker.patch("pydiamond.environ.executable.get_main_script_path", autospec=True)
    mock_is_frozen_executable = mocker.patch("pydiamond.environ.executable.is_frozen_executable", autospec=True)
    mock_is_frozen_executable.return_value = True

    # Act
    returned_path = get_executable_path()

    # Assert
    assert returned_path is mocker.sentinel.sys_executable
    mock_get_main_script_path.assert_not_called()


def test__get_executable_path__returns_main_script_path_if_not_frozen(mocker: MockerFixture) -> None:
    # Arrange
    mock_get_main_script_path = mocker.patch("pydiamond.environ.executable.get_main_script_path", autospec=True)
    mock_is_frozen_executable = mocker.patch("pydiamond.environ.executable.is_frozen_executable", autospec=True)
    mock_get_main_script_path.return_value = mocker.sentinel.script_path
    mock_is_frozen_executable.return_value = False

    # Act
    returned_path = get_executable_path()

    # Assert
    assert returned_path is mocker.sentinel.script_path
