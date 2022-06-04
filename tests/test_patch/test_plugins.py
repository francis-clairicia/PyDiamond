# -*- coding: Utf-8 -*-

from __future__ import annotations

import importlib
from functools import cached_property, partialmethod
from typing import TYPE_CHECKING, Any, Callable, Iterator, TypeVar
from unittest.mock import sentinel

import pytest

from ..mock.sys import MockVersionInfo, unload_module

if TYPE_CHECKING:
    from types import ModuleType
    from unittest.mock import MagicMock

    from py_diamond._patch._base import BasePatch
    from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch
    from py_diamond._patch.plugins.fix_typing import OverrideFinalFunctionsPatch

    from pytest_mock import MockerFixture


_T = TypeVar("_T")


@pytest.fixture(scope="module", autouse=True)
def disable_auto_patch_run(monkeypatch_module: pytest.MonkeyPatch) -> None:
    # Import py_diamond will automatically apply patches, so we silently disable all the patches
    from _pytest.monkeypatch import MonkeyPatch

    unload_module("py_diamond", include_submodules=True, monkeypatch=monkeypatch_module)
    with MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("PYDIAMOND_PATCH_DISABLE", "all")
        # The we import the package
        importlib.import_module("py_diamond")


@pytest.mark.unit
class TestPatchEnvDisable:
    @pytest.mark.parametrize(
        ["module_path", "patch_name"],
        [
            pytest.param(
                "py_diamond._patch.plugins.fix_enum",
                "IntEnumMonkeyPatch",
                id="fix_enum.IntEnumMonkeyPatch",
            ),
            pytest.param(
                "py_diamond._patch.plugins.fix_typing",
                "OverrideFinalFunctionsPatch",
                id="fix_typing.OverrideFinalFunctionsPatch",
            ),
        ],
    )
    def test__patch__must_not_be_run_if_disabled_from_env(
        self,
        module_path: str,
        patch_name: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        import importlib

        patch_cls: type[BasePatch] = getattr(importlib.import_module(module_path), patch_name)

        monkeypatch.setenv("PYDIAMOND_PATCH_DISABLE", patch_name)

        patch = patch_cls()

        # Act
        must_be_run = patch.must_be_run()

        # Assert
        assert not must_be_run

    @pytest.mark.parametrize(
        ["module_path", "patch_name"],
        [
            pytest.param(
                "py_diamond._patch.plugins.fix_enum",
                "IntEnumMonkeyPatch",
                id="fix_enum.IntEnumMonkeyPatch",
            ),
            pytest.param(
                "py_diamond._patch.plugins.fix_typing",
                "OverrideFinalFunctionsPatch",
                id="fix_typing.OverrideFinalFunctionsPatch",
            ),
        ],
    )
    def test__patch__must_not_be_run_if_disabled_from_env_using_all(
        self,
        module_path: str,
        patch_name: str,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        # Arrange
        import importlib

        patch_cls: type[BasePatch] = getattr(importlib.import_module(module_path), patch_name)

        monkeypatch.setenv("PYDIAMOND_PATCH_DISABLE", "all")

        patch = patch_cls()

        # Act
        must_be_run = patch.must_be_run()

        # Assert
        assert not must_be_run


@pytest.mark.unit
class TestFixIntEnum:
    @pytest.fixture
    @staticmethod
    def intenum_monkeypatch() -> Iterator[IntEnumMonkeyPatch]:
        from py_diamond._patch.plugins.fix_enum import IntEnumMonkeyPatch

        patch = IntEnumMonkeyPatch()
        patch.setup()
        yield patch
        patch.teardown()

    def test__patch__context(self, intenum_monkeypatch: IntEnumMonkeyPatch) -> None:
        # Arrange
        from py_diamond._patch import PatchContext

        expected_context = PatchContext.BEFORE_ALL

        # Act
        context = intenum_monkeypatch.get_context()

        # Assert
        assert isinstance(context, PatchContext)
        assert context == expected_context

    @pytest.mark.parametrize(
        ["method_name"],
        [
            pytest.param("__repr__"),
            pytest.param("__str__"),
            pytest.param("__format__"),
        ],
    )
    def test__patch__replace_IntEnum_method(
        self,
        method_name: str,
        intenum_monkeypatch: IntEnumMonkeyPatch,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        from enum import IntEnum

        ## Create unique object so we ensure the method is replaced
        intenum_method = sentinel.intenum_method
        mocker.patch.object(IntEnum, method_name, intenum_method)
        assert getattr(IntEnum, method_name) is intenum_method

        # Act
        intenum_monkeypatch.run()

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
    def test__patch__must_be_run(
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

        intenum_monkeypatch = IntEnumMonkeyPatch()

        # Act
        must_be_run = intenum_monkeypatch.must_be_run()

        # Assert
        assert must_be_run == expected_result


@pytest.mark.unit
class TestFixTypingFinal:
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
    def final_monkeypatch(mock_default_final: MagicMock) -> Iterator[OverrideFinalFunctionsPatch]:
        from py_diamond._patch.plugins.fix_typing import OverrideFinalFunctionsPatch

        patch = OverrideFinalFunctionsPatch()
        patch.setup()
        yield patch
        patch.teardown()

    def test__patch__context(self, final_monkeypatch: OverrideFinalFunctionsPatch) -> None:
        # Arrange
        from py_diamond._patch import PatchContext

        expected_context = PatchContext.BEFORE_ALL

        # Act
        context = final_monkeypatch.get_context()

        # Assert
        assert isinstance(context, PatchContext)
        assert context == expected_context

    def test__patch__wrap_default_final(
        self,
        final_monkeypatch: OverrideFinalFunctionsPatch,
        typing_module: ModuleType,
        mock_default_final: MagicMock,
    ) -> None:
        # Arrange
        ## Verify we don't lie
        assert getattr(typing_module, "final") is mock_default_final

        # Act
        final_monkeypatch.run()
        final: Any = getattr(typing_module, "final")

        # Assert
        assert final is not mock_default_final
        assert getattr(final, "__wrapped__") is mock_default_final

    def test__patch__will_not_apply_wrapper_twice(
        self,
        final_monkeypatch: OverrideFinalFunctionsPatch,
        typing_module: ModuleType,
    ) -> None:
        # Arrange
        final_monkeypatch.run()
        expected_final: Any = getattr(typing_module, "final")

        # Act
        final_monkeypatch.run()

        # Assert
        assert getattr(typing_module, "final") is expected_final

    def test__patch__apply_for_both_typing_and_typing_extensions_modules(
        self,
        final_monkeypatch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
    ) -> None:
        # Arrange
        import typing

        import typing_extensions

        default_typing_final = typing.final
        default_typing_extensions_final = typing_extensions.final

        # Act
        final_monkeypatch.run()

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
        final_monkeypatch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
    ) -> None:
        # Arrange
        typing_module = importlib.import_module(typing_module_name)
        final_monkeypatch.run()
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
        final_monkeypatch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        typing_module = importlib.import_module(typing_module_name)
        final_monkeypatch.run()
        final: Callable[[_T], _T] = getattr(typing_module, "final")

        def fget(self: Any) -> Any:
            return sentinel.property_get

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
        final_monkeypatch: OverrideFinalFunctionsPatch,
        mock_default_final: MagicMock,
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        typing_module = importlib.import_module(typing_module_name)
        final_monkeypatch.run()
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
