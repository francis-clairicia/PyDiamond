# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    import pathlib

    from pytest_mock import MockerFixture


################################## Environment initialization ##################################
# Always hide support on pygame import
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Tell pygame that we do not have a graphic environment
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "disk"

# This is the default but we enforce the values for the tests
os.environ["PYDIAMOND_TEST_STRICT_FINAL"] = "0"
os.environ.pop("PYDIAMOND_PATCH_DISABLE", None)


################################## fixtures ##################################

pytest_plugins = [
    # pygame modules plugins
    f"{__package__}.mock.pygame.display",
    f"{__package__}.mock.pygame.event",
    f"{__package__}.mock.pygame.mixer",
    f"{__package__}.mock.pygame.mouse",
    # other plugins
    f"{__package__}.mock.sys",
    f"{__package__}.fixtures.monkeypatch",
    f"{__package__}.fixtures.sentinel",
]


@pytest.fixture(scope="session")
def pydiamond_rootdir(pytestconfig: pytest.Config) -> pathlib.Path:
    return pytestconfig.rootpath / "pydiamond"


################################## Auto used fixtures for all session test ##################################


@pytest.fixture(scope="session", autouse=True)
def __mock_window_object(session_mocker: MockerFixture) -> None:
    """
    Mock the Window's __new__ because it will not accept multiple instances
    """
    from pydiamond.window.display import Window

    session_mocker.patch.object(Window, "__new__", lambda cls, *args, **kwargs: super(Window, cls).__new__(cls))
