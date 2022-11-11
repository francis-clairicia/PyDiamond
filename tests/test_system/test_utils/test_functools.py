# -*- coding: Utf-8 -*-

from __future__ import annotations

from types import MethodType
from typing import TYPE_CHECKING, Any, Callable, Literal
from weakref import WeakMethod

from pydiamond.system.utils.functools import make_callback

import pytest
from typing_extensions import assert_never

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture


class Dummy:
    pass


@pytest.fixture
def callback_stub(mocker: MockerFixture) -> MagicMock:
    return mocker.stub(name="Callback stub")


@pytest.fixture
def weakref_callback_stub(mocker: MockerFixture) -> MagicMock:
    return mocker.stub(name="weakref stub")


class TestMakeCallback:
    ### Classic functions

    def test__make_callback__default(self, callback_stub: MagicMock) -> None:
        # Arrange

        # Act
        callback: Callable[..., Any] = make_callback(callback_stub)

        # Assert
        assert callback is callback_stub

    def test__make_callback__weakref_object(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()

        # Act
        callback: Callable[..., Any] = make_callback(callback_stub, dummy)
        callback(a=5, b=12)

        # Assert
        callback_stub.assert_called_once_with(dummy, a=5, b=12)

    def test__make_callback__weakref_object_deadref_callback(
        self, callback_stub: MagicMock, weakref_callback_stub: MagicMock
    ) -> None:
        # Arrange
        dummy = Dummy()
        _ = make_callback(callback_stub, dummy, weakref_callback=weakref_callback_stub)

        # Act
        del dummy

        # Assert
        weakref_callback_stub.assert_called_once()

    def test__make_callback__weakref_object_deadref_default(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()
        callback: Callable[..., Any] = make_callback(callback_stub, dummy)

        # Act & Assert
        del dummy
        with pytest.raises(ReferenceError):
            callback(a=5, b=12)
        callback_stub.assert_not_called()

    def test__make_callback__weakref_object_deadref_exception(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()

        class MyCustomException(Exception):
            pass

        callback: Callable[..., Any] = make_callback(callback_stub, dummy, deadref_value_return=MyCustomException)

        # Act & Assert
        del dummy
        with pytest.raises(MyCustomException):
            callback(a=5, b=12)
        callback_stub.assert_not_called()

    def test__make_callback__weakref_object_deadref_value_return(self, callback_stub: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        dummy = Dummy()
        deadred_return_value = mocker.sentinel.deadref_return_value

        callback: Callable[..., Any] = make_callback(callback_stub, dummy, deadref_value_return=deadred_return_value)

        # Act
        del dummy
        output = callback(a=5, b=12)

        # Assert
        callback_stub.assert_not_called()
        assert output is deadred_return_value

    ### Weak methods

    def test__make_callback__weak_method__default(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))

        # Act
        callback: Callable[..., Any] = make_callback(weak_method)
        callback(432, a=5, b=12)

        # Assert
        callback_stub.assert_called_once_with(dummy, 432, a=5, b=12)

    def test__make_callback__weak_method__default_deadref_weakref_callback_ignored(
        self, callback_stub: MagicMock, weakref_callback_stub: MagicMock
    ) -> None:
        # Arrange
        dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        _ = make_callback(weak_method, weakref_callback=weakref_callback_stub)

        # Act
        del dummy

        # Assert
        weakref_callback_stub.assert_not_called()

    def test__make_callback__weak_method__default_deadref(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        callback: Callable[..., Any] = make_callback(weak_method)

        # Act & Assert
        del dummy
        with pytest.raises(ReferenceError):
            callback(432, a=5, b=12)
        callback_stub.assert_not_called()

    def test__make_callback__weak_method__deadref_exception(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))

        class MyCustomException(Exception):
            pass

        callback: Callable[..., Any] = make_callback(weak_method, deadref_value_return=MyCustomException)

        # Act & Assert
        del dummy
        with pytest.raises(MyCustomException):
            callback(a=5, b=12)
        callback_stub.assert_not_called()

    def test__make_callback__weak_method__deadref_value_return(self, callback_stub: MagicMock, mocker: MockerFixture) -> None:
        # Arrange
        dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        deadred_return_value = mocker.sentinel.deadref_return_value

        callback: Callable[..., Any] = make_callback(weak_method, deadref_value_return=deadred_return_value)

        # Act
        del dummy
        output = callback(a=5, b=12)

        # Assert
        callback_stub.assert_not_called()
        assert output is deadred_return_value

    def test__make_callback__weak_method__weakref_object(self, callback_stub: MagicMock) -> None:
        # Arrange
        dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        other_dummy = Dummy()

        # Act
        callback: Callable[..., Any] = make_callback(weak_method, other_dummy)
        callback(432, a=5, b=12)

        # Assert
        callback_stub.assert_called_once_with(dummy, other_dummy, 432, a=5, b=12)

    def test__make_callback__weak_method__weakref_object_deadref_callback(
        self, callback_stub: MagicMock, weakref_callback_stub: MagicMock
    ) -> None:
        # Arrange
        dummy = Dummy()
        other_dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        _ = make_callback(weak_method, other_dummy, weakref_callback=weakref_callback_stub)

        # Act
        del dummy, other_dummy

        # Assert
        weakref_callback_stub.assert_called_once()

    @pytest.mark.parametrize("to_del", ["weakmethod_object_ref", "bound_object_ref", "both"], ids=lambda n: f"to_del=={n}")
    def test__make_callback__weak_method__weakref_object_deadref(
        self, callback_stub: MagicMock, to_del: Literal["weakmethod_object_ref", "bound_object_ref", "both"]
    ) -> None:
        # Arrange
        dummy = Dummy()
        other_dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        callback: Callable[..., Any] = make_callback(weak_method, other_dummy)

        # Act & Assert
        match to_del:
            case "weakmethod_object_ref":
                del dummy
            case "bound_object_ref":
                del other_dummy
            case "both":
                del dummy, other_dummy  # noqa: F821
            case _:
                assert_never(to_del)

        with pytest.raises(ReferenceError):
            callback(432, a=5, b=12)
        callback_stub.assert_not_called()

    @pytest.mark.parametrize("to_del", ["weakmethod_object_ref", "bound_object_ref", "both"], ids=lambda n: f"to_del=={n}")
    def test__make_callback__weak_method__weakref_object_deadref_exception(
        self, callback_stub: MagicMock, to_del: Literal["weakmethod_object_ref", "bound_object_ref", "both"]
    ) -> None:
        # Arrange
        dummy = Dummy()
        other_dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))

        class MyCustomException(Exception):
            pass

        callback: Callable[..., Any] = make_callback(weak_method, other_dummy, deadref_value_return=MyCustomException)

        # Act & Assert
        match to_del:
            case "weakmethod_object_ref":
                del dummy
            case "bound_object_ref":
                del other_dummy
            case "both":
                del dummy, other_dummy  # noqa: F821
            case _:
                assert_never(to_del)
        with pytest.raises(MyCustomException):
            callback(a=5, b=12)
        callback_stub.assert_not_called()

    @pytest.mark.parametrize("to_del", ["weakmethod_object_ref", "bound_object_ref", "both"], ids=lambda n: f"to_del=={n}")
    def test__make_callback__weak_method__weakref_object_deadref_value_return(
        self,
        callback_stub: MagicMock,
        to_del: Literal["weakmethod_object_ref", "bound_object_ref", "both"],
        mocker: MockerFixture,
    ) -> None:
        # Arrange
        dummy = Dummy()
        other_dummy = Dummy()
        weak_method = WeakMethod(MethodType(callback_stub, dummy))
        deadred_return_value = mocker.sentinel.deadref_return_value

        callback: Callable[..., Any] = make_callback(weak_method, other_dummy, deadref_value_return=deadred_return_value)

        # Act
        match to_del:
            case "weakmethod_object_ref":
                del dummy
            case "bound_object_ref":
                del other_dummy
            case "both":
                del dummy, other_dummy  # noqa: F821
            case _:
                assert_never(to_del)
        output = callback(a=5, b=12)

        # Assert
        callback_stub.assert_not_called()
        assert output is deadred_return_value
