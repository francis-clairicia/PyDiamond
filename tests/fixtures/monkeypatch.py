# -*- coding: Utf-8 -*-
"""Experimental (https://github.com/pytest-dev/pytest/issues/363)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

import pytest

if TYPE_CHECKING:
    from pytest import MonkeyPatch


def _monkeypatch() -> Iterator[MonkeyPatch]:
    from _pytest.monkeypatch import MonkeyPatch

    mpatch = MonkeyPatch()
    yield mpatch
    mpatch.undo()


@pytest.fixture(scope="session")
def monkeypatch_session() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()


@pytest.fixture(scope="package")
def monkeypatch_package() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()


@pytest.fixture(scope="module")
def monkeypatch_module() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()


@pytest.fixture(scope="class")
def monkeypatch_class() -> Iterator[MonkeyPatch]:
    yield from _monkeypatch()
