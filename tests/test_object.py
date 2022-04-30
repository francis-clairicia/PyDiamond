# -*- coding: Utf-8 -*

import pytest
from typing_extensions import final

from py_diamond.system.object import Object, override

# pyright: reportUnusedClass=false


def test_object_final_subclass() -> None:
    class A(Object):
        pass

    assert A.__finalmethods__ == frozenset()

    @final
    class B(Object):
        pass

    assert getattr(B, "__final__", False)
    assert B.__finalmethods__ == frozenset()

    with pytest.raises(TypeError, match=f"Base classes marked as final class: {B.__qualname__}"):

        class C(A, B):  # type: ignore[misc]
            pass


def test_object_multiple_final_subclass() -> None:
    class A(Object):
        pass

    @final
    class B(Object):
        pass

    @final
    class C(Object):
        pass

    with pytest.raises(TypeError, match=f"Base classes marked as final class: {B.__qualname__}, {C.__qualname__}"):

        class D(A, B, C):  # type: ignore[misc]
            pass


def test_object_override_method() -> None:
    class A(Object):
        def method(self) -> None:
            pass

    class B(A):
        @override
        def method(self) -> None:
            return super().method()

        assert getattr(method, "__mustoverride__")
        assert hasattr(method, "__final__")
        assert not getattr(method, "__final__")

    class C(B):
        @override(final=True)
        def method(self) -> None:
            return super().method()

        assert getattr(method, "__mustoverride__")
        assert getattr(method, "__final__")

    class D(B):
        @final
        @override
        def method(self) -> None:
            return super().method()

        assert getattr(method, "__mustoverride__")
        assert getattr(method, "__final__")

    assert C.__finalmethods__ == frozenset({"method"})


def test_object_override_missing_in_bases() -> None:
    with pytest.raises(TypeError, match=r"These methods will not override base method: non_override_method"):

        class A(Object):
            @override
            def non_override_method(self) -> None:
                pass

    with pytest.raises(
        TypeError, match=r"These methods will not override base method: non_override_method2?, non_override_method2?"
    ):

        class B(Object, int):
            @override
            def non_override_method(self) -> None:
                pass

            @override(final=True)
            def non_override_method2(self) -> None:
                pass


def test_object_override_property() -> None:
    class A(Object):
        @property
        def a(self) -> int:
            return 2

    class B(A):
        @override  # type: ignore[misc]
        @property
        def a(self) -> int:
            return 3

        assert getattr(getattr(a, "fget"), "__mustoverride__")


@pytest.mark.skip("Not yet implemented")
def test_object_final_method_base_conflicts() -> None:
    class A(Object):
        def method(self) -> None:
            pass

    class B(Object):
        @final
        def method(self) -> None:
            pass

    class C(B, A):
        pass

    with pytest.raises(TypeError, match=r"Final methods conflict between base classes: .+"):

        class D(A, B):  # type: ignore[misc]
            pass


def test_object_final_method_overriden() -> None:
    class A(Object):
        @final
        def method(self) -> None:
            pass

    with pytest.raises(TypeError, match=r"These attributes would override final methods: method"):

        class B(A):
            def method(self) -> None:  # type: ignore[misc]
                return super().method()
