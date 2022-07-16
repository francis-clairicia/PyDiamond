# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Iterator

import pytest

if TYPE_CHECKING:
    from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestFixIntEnum:
    @pytest.fixture
    @staticmethod
    def patch() -> Iterator[IntEnumMonkeyPatch]:
        from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

        patch = IntEnumMonkeyPatch()
        patch.setup()
        yield patch
        patch.teardown()

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
