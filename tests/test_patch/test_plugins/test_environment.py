# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator, MutableMapping

import pytest

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from py_diamond._patch.plugins.environment import ArrangePygameEnvironmentBeforeImport

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


@pytest.fixture(scope="module", autouse=True)
def fake_environ(monkeypatch_module: MonkeyPatch) -> MutableMapping[str, str]:
    import os

    fake_env = dict(os.environ)
    monkeypatch_module.setattr(os, "environ", fake_env)
    return fake_env


# @pytest.mark.functional
# def test__fake_environment__fixture_works(fake_environ: MutableMapping[str, str], monkeypatch: MonkeyPatch) -> None:
#     import os

#     assert os.environ is fake_environ

#     monkeypatch.setenv("__TEST_ENV__", "true")
#     assert fake_environ["__TEST_ENV__"] == "true"


@pytest.mark.functional
class TestArrangePygameEnvironment:
    @pytest.fixture
    @staticmethod
    def patch(fake_environ: MutableMapping[str, str]) -> Iterator[ArrangePygameEnvironmentBeforeImport]:
        from py_diamond._patch.plugins.environment import ArrangePygameEnvironmentBeforeImport

        patch = ArrangePygameEnvironmentBeforeImport()
        patch.setup()
        assert patch.environ is fake_environ
        yield patch
        patch.teardown()

    @pytest.fixture
    @staticmethod
    def mock_check_booleans(mocker: MockerFixture) -> MagicMock:
        return mocker.patch("py_diamond._patch.plugins.environment.check_booleans")

    def test__context__good_context(self, patch: ArrangePygameEnvironmentBeforeImport) -> None:
        # Arrange
        from py_diamond._patch import PatchContext

        expected_contexts = [PatchContext.BEFORE_ALL, PatchContext.BEFORE_IMPORTING_PYGAME]

        # Act
        context = patch.get_required_context()

        # Assert
        assert isinstance(context, PatchContext)
        assert context in expected_contexts

    # @pytest.mark.usefixtures("mock_check_booleans")
    # def test__run__(self) -> None:
    #     pass
