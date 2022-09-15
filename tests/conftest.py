# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

import pytest

if TYPE_CHECKING:
    from threading import ExceptHookArgs

    from pytest_mock import MockerFixture


################################## Environment initialization ##################################
# Always hide support on pygame import
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Tell pygame that we do not have a graphic environment
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "disk"

# This is the default but we enforce the values for the tests
os.environ["PYDIAMOND_TEST_STRICT_FINAL"] = "0"
os.environ["PYDIAMOND_IMPORT_WARNINGS"] = "1"
os.environ.pop("PYDIAMOND_PATCH_DISABLE", None)

################################## Fixture-like functions ##################################


@contextmanager
def silently_ignore_systemexit_in_thread() -> Iterator[None]:
    """
    The default threading.excepthook ignores SystemExit exceptions.
    pytest overrides this hook at compile time and raise a warning for *ALL* exceptions...

    This function is not a fixture because fixtures are always called before the pytest wrapper,
    therefore we need to manually decorate the target function
    """

    import threading

    default_excepthook = threading.excepthook

    def patch_excepthook(args: ExceptHookArgs) -> Any:
        if args.exc_type is SystemExit:
            return
        return default_excepthook(args)

    setattr(threading, "excepthook", patch_excepthook)

    try:
        yield
    finally:
        setattr(threading, "excepthook", default_excepthook)


################################## fixtures plugins ##################################

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

################################## Auto used fixtures for all session test ##################################


@pytest.fixture(scope="session", autouse=True)
def __mock_window_object(session_mocker: MockerFixture) -> None:
    """
    Mock the Window's __new__ because it will not accept multiple instances
    """
    from pydiamond.window.display import Window

    session_mocker.patch.object(Window, "__new__", lambda cls, *args, **kwargs: super(Window, cls).__new__(cls))
