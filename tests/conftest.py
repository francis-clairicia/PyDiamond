# -*- coding: Utf-8 -*-

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

import pytest

if TYPE_CHECKING:
    from threading import ExceptHookArgs

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


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
    # other plugins
    f"{__package__}.mock.sys",
    f"{__package__}.fixtures.monkeypatch",
]

################################## Auto used fixtures for all session test ##################################


@pytest.fixture(scope="session", autouse=True)
def __patch_pygame_display_environment(monkeypatch_session: MonkeyPatch) -> None:
    """
    Tell pygame that we do not have a graphic environment
    """

    monkeypatch_session.setenv("SDL_VIDEODRIVER", "dummy")


@pytest.fixture(scope="session", autouse=True)
def __mock_window_object(session_mocker: MockerFixture) -> None:
    """
    Mock the Window's __new__ because it will not accept multiple instances
    """
    from py_diamond.window.display import Window

    session_mocker.patch.object(Window, "__new__", lambda cls, *args, **kwargs: super(Window, cls).__new__(cls))
