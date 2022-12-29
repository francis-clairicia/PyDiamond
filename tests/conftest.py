# -*- coding: Utf-8 -*-

from __future__ import annotations

import os
import pathlib
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


################################## Environment initialization ##################################
# Always hide support on pygame import
os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

# Tell pygame that we do not have a graphic environment
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "disk"

# Do not run any optional patch
os.environ["PYDIAMOND_PATCH_DISABLE"] = "all"


################################## fixtures ##################################

pytest_plugins = [
    # pygame modules plugins
    f"{__package__}.mock.pygame.display",
    f"{__package__}.mock.pygame.event",
    f"{__package__}.mock.pygame.freetype",
    f"{__package__}.mock.pygame.mixer",
    f"{__package__}.mock.pygame.mouse",
    f"{__package__}.mock.pygame.sysfont",
    # other plugins
    f"{__package__}.mock.sys",
    f"{__package__}.fixtures.monkeypatch",
]


@pytest.fixture(scope="session")
def pydiamond_rootdirs_list() -> list[pathlib.Path]:
    import importlib

    pydiamond_spec = importlib.import_module("pydiamond").__spec__
    assert pydiamond_spec is not None
    assert pydiamond_spec.submodule_search_locations is not None

    return [pathlib.Path(path) for path in pydiamond_spec.submodule_search_locations]


@pytest.fixture(scope="session")
def pydiamond_packages_paths(pydiamond_rootdirs_list: list[pathlib.Path]) -> list[pathlib.Path]:
    import importlib
    import pkgutil

    if TYPE_CHECKING:
        from typing import Iterator

    def get_packages_paths() -> Iterator[str]:
        for package_info in filter(
            lambda module_info: module_info.ispkg,
            pkgutil.walk_packages(map(os.fspath, pydiamond_rootdirs_list), prefix="pydiamond."),
        ):
            package_module = importlib.import_module(package_info.name)
            package_module_spec = package_module.__spec__
            assert package_module_spec is not None
            assert package_module_spec.submodule_search_locations is not None
            yield from package_module_spec.submodule_search_locations

    return [pathlib.Path(p) for p in get_packages_paths()]


################################## Auto used fixtures for all session test ##################################


@pytest.fixture(scope="session", autouse=True)
def __mock_window_object(session_mocker: MockerFixture) -> None:
    """
    Mock the Window's __new__ because it will not accept multiple instances
    """
    from pydiamond.window.display import Window

    session_mocker.patch.object(Window, "__new__", lambda cls, *args, **kwargs: super(Window, cls).__new__(cls))
