"""Experimental (https://github.com/pytest-dev/pytest/issues/363)."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from pytest import MonkeyPatch


def _monkeypatch() -> Iterator[MonkeyPatch]:
    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def session_monkeypatch() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()


@pytest.fixture(scope="package")
def package_monkeypatch() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()


@pytest.fixture(scope="module")
def module_monkeypatch() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()


@pytest.fixture(scope="class")
def class_monkeypatch() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()
