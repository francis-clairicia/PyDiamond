# -*- coding: Utf-8 -*

from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, NamedTuple, TypeVar

import pytest

from .mock.pygame.display import MockDisplayModule, PatchedDisplayModule
from .mock.pygame.event import MockEventModule, PatchedEventModule
from .mock.pygame.surface import MockSurface

if TYPE_CHECKING:
    from threading import ExceptHookArgs

    from pytest_mock import MockerFixture


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


################################## pygame modules fixtures ##################################

#### Mocks ####


@pytest.fixture
def mock_display_module() -> MockDisplayModule:
    return MockDisplayModule()


@pytest.fixture
def mock_event_module(mock_display_module: MockDisplayModule) -> MockEventModule:
    return MockEventModule(mock_display_module)


#### Patches ####

_N = TypeVar("_N", bound=NamedTuple)


def _patch_generator(module: str, mock: Any, patch_type: type[_N], mocker: MockerFixture) -> _N:
    return patch_type._make(mocker.patch(f"{module}.{field}", side_effect=getattr(mock, field)) for field in patch_type._fields)


@pytest.fixture
def patch_display_module(mocker: MockerFixture, mock_display_module: MockDisplayModule) -> PatchedDisplayModule:
    return _patch_generator("pygame.display", mock_display_module, PatchedDisplayModule, mocker)


@pytest.fixture
def patch_event_module(mocker: MockerFixture, mock_event_module: MockEventModule) -> PatchedEventModule:
    return _patch_generator("pygame.event", mock_event_module, PatchedEventModule, mocker)


################################## Auto used fixtures for all session test ##################################


@pytest.fixture(autouse=True)
def __mock_surface(mocker: MockerFixture) -> None:
    """
    Mock the Surface object in order not to call real Surface.convert()
    """

    classes_to_mock: tuple[str, ...] = (
        "pygame.Surface",
        "pygame.surface.Surface",
        "py_diamond.graphics.Surface",
        "py_diamond.graphics.button.Surface",
        "py_diamond.graphics.checkbox.Surface",
        "py_diamond.graphics.entry.Surface",
        "py_diamond.graphics.font.Surface",
        "py_diamond.graphics.gradients.Surface",
        "py_diamond.graphics.image.Surface",
        "py_diamond.graphics.renderer.Surface",
        "py_diamond.graphics.shape.Surface",
        "py_diamond.graphics.sprite.Surface",
        "py_diamond.graphics.surface.Surface",
        "py_diamond.graphics.text.Surface",
        "py_diamond.resource.loader.Surface",
        "py_diamond.window.cursor.Surface",
        "py_diamond.window.display.Surface",
        "py_diamond.window.scene.Surface",
    )

    for cls in classes_to_mock:
        mocker.patch(cls, MockSurface)


@pytest.fixture(autouse=True)
def __mock_window_object(mocker: MockerFixture) -> None:
    """
    Mock the Window's __new__ because it will not accept multiple instances
    """
    from py_diamond.window.display import Window

    mocker.patch.object(Window, "__new__", side_effect=lambda cls, *args, **kwargs: super(Window, cls).__new__(cls))
