# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from functools import cached_property, partialmethod
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar

import pytest

from ...mock.sys import MockVersionInfo, unload_module

if TYPE_CHECKING:
    from types import ModuleType
    from unittest.mock import MagicMock

    from pydiamond._patch.plugins.fix_typing import OverrideFinalFunctionsPatch

    from pytest_mock import MockerFixture


_T = TypeVar("_T")


@pytest.mark.functional
class TestFixTypingFinal:
    @pytest.fixture(autouse=True)
    @staticmethod
    def arrange_environment(monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("PYDIAMOND_TEST_STRICT_FINAL", "0")

    @pytest.fixture(scope="class", params=[MockVersionInfo(3, 10, 4, "final", 0), MockVersionInfo(3, 11, 0, "beta", 5)], ids=str)
    @staticmethod
    def python_version(request: pytest.FixtureRequest, class_mocker: MockerFixture) -> MockVersionInfo:
        python_version: MockVersionInfo = getattr(request, "param")
        class_mocker.patch("sys.version_info", python_version)
        return python_version

    @pytest.fixture
    @staticmethod
    def typing_module(python_version: MockVersionInfo, monkeypatch: pytest.MonkeyPatch) -> ModuleType:
        # Unload the modules first
        unload_module("typing_extensions", True, monkeypatch)
        unload_module("typing", True, monkeypatch)

        used_typing_module: ModuleType
        if python_version < (3, 11):
            used_typing_module = importlib.import_module("typing_extensions")
        else:
            used_typing_module = importlib.import_module("typing")
        return used_typing_module

    @pytest.fixture(autouse=True)
    @staticmethod
    def mock_default_final(typing_module: ModuleType, mocker: MockerFixture) -> MagicMock:
        def final(f: Any) -> Any:
            # Reproduced final behavior, in order not to depend of the standard module implementation
            # Must be changed if there is a modification in the standard library
            try:
                f.__final__ = True
            except (AttributeError, TypeError):
                pass
            return f

        return mocker.patch.object(typing_module, "final", side_effect=final)

    @pytest.fixture
    @staticmethod
    def patch(mock_default_final: MagicMock) -> Iterator[OverrideFinalFunctionsPatch]:
        from pydiamond._patch.plugins.fix_typing import OverrideFinalFunctionsPatch

        patch = OverrideFinalFunctionsPatch()
        patch.setup()
        yield patch
        patch.teardown()

    def test__patch__wrap_default_final(
        self,
        patch: OverrideFinalFunctionsPatch,
        typing_module: ModuleType,
        mock_default_final: MagicMock,
    ) -> None:
        # Arrange
        ## Verify we don't lie
        assert getattr(typing_module, "final") is mock_default_final

        # Act
        patch.run()
        final: Any = getattr(typing_module, "final")

        # Assert
        assert final is not mock_default_final
        assert getattr(final, "__wrapped__") is mock_default_final

    def test__patch__will_not_apply_wrapper_twice(
        self,
        patch: OverrideFinalFunctionsPatch,
        typing_module: ModuleType,
    ) -> None:
        # Arrange
        patch.run()
        expected_final: Any = getattr(typing_module, "final")

        # Act
        patch.run()

        # Assert
        assert getattr(typing_module, "final") is expected_final

    def test__patch__apply_for_both_typing_and_typing_extensions_modules(
        self,
        patch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
    ) -> None:
        # Arrange
        import typing

        import typing_extensions

        default_typing_final = typing.final
        default_typing_extensions_final = typing_extensions.final

        # Act
        patch.run()

        # Assert
        assert typing.final is not default_typing_final
        assert getattr(typing.final, "__wrapped__") is default_typing_final
        assert getattr(typing.final, "__default_final__") is mock_default_final

        assert typing_extensions.final is not default_typing_extensions_final
        assert getattr(typing_extensions.final, "__wrapped__") is default_typing_extensions_final
        assert getattr(typing_extensions.final, "__default_final__") is mock_default_final

    @pytest.mark.parametrize(
        ["typing_module_name"],
        [
            pytest.param("typing"),
            pytest.param("typing_extensions"),
        ],
    )
    def test__final_wrapper__default_behavior_works(
        self,
        typing_module_name: str,
        patch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
    ) -> None:
        # Arrange
        typing_module = importlib.import_module(typing_module_name)
        patch.run()
        final: Callable[[_T], _T] = getattr(typing_module, "final")

        def func() -> None:
            pass

        # Act
        final_func = final(func)

        # Assert
        mock_default_final.assert_called_with(func)
        assert final_func is func  # If this test fails, checkout the side effect of 'mock_default_final'
        assert getattr(func, "__final__") is True  # If this test fails, checkout the side effect of 'mock_default_final"

    @pytest.mark.parametrize(
        ["typing_module_name"],
        [
            pytest.param("typing"),
            pytest.param("typing_extensions"),
        ],
    )
    def test__final_wrapper__works_for_properties(
        self,
        typing_module_name: str,
        patch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        typing_module = importlib.import_module(typing_module_name)
        patch.run()
        final: Callable[[_T], _T] = getattr(typing_module, "final")

        def fget(self: Any) -> Any:
            return mocker.sentinel.property_get

        fset = lambda self, val: None

        p = property(fget=fget, fset=fset, fdel=None)

        # Act
        final_p = final(p)

        # Assert
        assert mock_default_final.mock_calls == [mocker.call(fget), mocker.call(fset), mocker.call(p)]
        assert final_p is p

        ## The wrapper should not replace the functions
        assert p.fget is fget
        assert p.fset is fset

    @pytest.mark.parametrize(
        ["typing_module_name"],
        [
            pytest.param("typing"),
            pytest.param("typing_extensions"),
        ],
    )
    @pytest.mark.parametrize(
        ["method_descriptor", "function_attribute_name"],
        [
            pytest.param(classmethod, "__func__", id="classmethod"),
            pytest.param(staticmethod, "__func__", id="staticmethod"),
            pytest.param(cached_property, "func", id="cached_property"),
            pytest.param(partialmethod, "func", id="partialmethod"),
        ],
    )
    def test__final_wrapper__works_for_standard_method_descriptor(
        self,
        typing_module_name: str,
        method_descriptor: Callable[[Any], Callable[..., Any]],
        function_attribute_name: str,
        patch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        typing_module = importlib.import_module(typing_module_name)
        patch.run()
        final: Callable[[_T], _T] = getattr(typing_module, "final")

        def method() -> None:
            pass

        descriptor = method_descriptor(method)

        # Act
        final_descriptor = final(descriptor)

        # Assert
        assert mock_default_final.mock_calls == [mocker.call(method), mocker.call(descriptor)]
        assert final_descriptor is descriptor

        ## The wrapper should not replace the functions
        assert getattr(descriptor, function_attribute_name) is method
