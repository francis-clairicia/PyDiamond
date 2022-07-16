# -*- coding: Utf-8 -*-

from __future__ import annotations

from enum import IntEnum, IntFlag
from typing import TYPE_CHECKING, Any, Iterator

import pytest

if TYPE_CHECKING:
    from enum import Enum

    from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

    from pytest_mock import MockerFixture


@pytest.mark.functional
class TestFixIntEnum:
    @pytest.fixture(params=[IntEnum, IntFlag])
    @staticmethod
    def enum_cls(request: Any) -> type[Enum]:
        enum_cls: type[Enum] = request.param
        return enum_cls

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
            "__str__",
            "__format__",
        ],
    )
    def test__run__replace_method(
        self,
        enum_cls: type[Enum],
        method_name: str,
        patch: IntEnumMonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange

        ## Create unique object so we ensure the method is replaced
        intenum_method = mocker.sentinel.intenum_method
        mocker.patch.object(enum_cls, method_name, intenum_method)
        assert getattr(enum_cls, method_name) is intenum_method

        # Act
        patch.run()

        # Assert
        assert getattr(enum_cls, method_name) is not intenum_method
        assert getattr(enum_cls, method_name) is getattr(int, method_name)
