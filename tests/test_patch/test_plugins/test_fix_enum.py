# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

import pytest

from ...mock.sys import MockVersionInfo

if TYPE_CHECKING:
    from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestFixIntEnum:
    @pytest.fixture
    @staticmethod
    def patch() -> Iterator[IntEnumMonkeyPatch]:
        from py_diamond._patch import PatchContext
        from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

        patch = IntEnumMonkeyPatch()
        patch.run_context = PatchContext.BEFORE_ALL
        patch.setup()
        yield patch
        patch.teardown()

    def test__context__good_context(self) -> None:
        # Arrange
        from py_diamond._patch import PatchContext
        from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

        expected_context = PatchContext.BEFORE_ALL

        # Act
        context = IntEnumMonkeyPatch.get_required_context()

        # Assert
        assert isinstance(context, PatchContext)
        assert context == expected_context

    @pytest.mark.parametrize(
        "method_name",
        [
            "__repr__",
            "__str__",
            "__format__",
        ],
    )
    def test__run__replace_IntEnum_method(
        self,
        method_name: str,
        patch: IntEnumMonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        from enum import IntEnum

        ## Create unique object so we ensure the method is replaced
        intenum_method = mocker.sentinel.intenum_method
        mocker.patch.object(IntEnum, method_name, intenum_method)
        assert getattr(IntEnum, method_name) is intenum_method

        # Act
        patch.run()

        # Assert
        assert getattr(IntEnum, method_name) is not intenum_method
        assert getattr(IntEnum, method_name) is getattr(int, method_name)

    @pytest.mark.parametrize(
        ["python_version", "expected_result"],
        [
            pytest.param(MockVersionInfo(3, 10, 4, "final", 0), True),
            pytest.param(MockVersionInfo(3, 10, 12, "final", 0), True),
            pytest.param(MockVersionInfo(3, 11, 0, "alpha", 5), False),
            pytest.param(MockVersionInfo(3, 11, 2, "final", 0), False),
            pytest.param(MockVersionInfo(3, 12, 0, "final", 0), False),
        ],
        ids=str,
    )
    def test__must_be_run__according_to_python_version(
        self,
        python_version: MockVersionInfo,
        expected_result: bool,
        monkeypatch: pytest.MonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

        monkeypatch.delenv("PYDIAMOND_PATCH_DISABLE", raising=False)
        mocker.patch("sys.version_info", python_version)

        patch = IntEnumMonkeyPatch()

        # Act
        must_be_run = patch.must_be_run()

        # Assert
        assert must_be_run == expected_result
