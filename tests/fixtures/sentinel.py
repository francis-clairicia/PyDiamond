# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    from pytest_mock import MockerFixture


@pytest.fixture(scope="session")
def session_sentinel(session_mocker: MockerFixture) -> Any:
    return session_mocker.sentinel


@pytest.fixture(scope="package")
def package_sentinel(package_mocker: MockerFixture) -> Any:
    return package_mocker.sentinel


@pytest.fixture(scope="module")
def module_sentinel(module_mocker: MockerFixture) -> Any:
    return module_mocker.sentinel


@pytest.fixture(scope="class")
def class_sentinel(class_mocker: MockerFixture) -> Any:
    return class_mocker.sentinel


@pytest.fixture
def sentinel(mocker: MockerFixture) -> Any:
    return mocker.sentinel
