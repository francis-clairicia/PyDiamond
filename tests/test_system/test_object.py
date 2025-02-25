from __future__ import annotations

from typing import Any, final, override

from pydiamond.system.object import Object, mro

import pytest

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

        assert getattr(method, "__override__")

    class C(B):
        @final
        @override
        def method(self) -> None:
            return super().method()

        assert getattr(method, "__override__")
        assert getattr(method, "__final__")

    assert C.__finalmethods__ == frozenset({"method"})


def test_object_override_missing_in_bases() -> None:
    with pytest.raises(TypeError, match=r"These methods will not override base method: .+"):

        class A(Object):
            @override
            def non_override_method(self) -> None:  # type: ignore[misc]
                pass


def test_object_override_property() -> None:
    class A(Object):
        @property
        def a(self) -> int:
            return 2

    class B(A):
        @property
        @override
        def a(self) -> int:
            return 3

        assert getattr(getattr(a, "fget"), "__override__")


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


def test_object_final_method_base_no_conflict_in_complex_inheritance() -> None:
    class A(Object):
        @final
        def method(self) -> None:
            pass

    class B(A):
        pass

    class C(B):
        pass

    class D(A):
        pass

    class Test(D, C):  # Must not fail
        pass

    assert Test.__finalmethods__ == frozenset({"method"})


def test_object_final_method_overriden() -> None:
    class A(Object):
        @final
        def method(self) -> None:
            pass

    with pytest.raises(TypeError, match=r"These attributes would override final methods: 'method'"):

        class B(A):
            def method(self) -> None:  # type: ignore[misc]
                return super().method()


def test_mro_invalid_order() -> None:
    class SeriousOrderDisagreement:
        class X:
            pass

        class Y:
            pass

        class A(X, Y):
            pass

        class B(Y, X):
            pass

        bases = (A, B)

    with pytest.raises(TypeError, match=r"inconsistent hierarchy, no C3 MRO is possible"):
        _ = mro(*SeriousOrderDisagreement.bases)


## Example classes samples (TODO: Fixture)
class _Example0:  # Trivial single inheritance case.
    class A:
        pass

    class B(A):
        pass

    class C(B):
        pass

    class D(C):
        pass

    tester = D
    expected = (D, C, B, A, object)


class _Example1:
    class F:
        pass

    class E:
        pass

    class D:
        pass

    class C(D, F):
        pass

    class B(D, E):
        pass

    class A(B, C):
        pass

    tester = A
    expected = (A, B, C, D, E, F, object)


class _Example2:
    class F:
        pass

    class E:
        pass

    class D:
        pass

    class C(D, F):
        pass

    class B(E, D):
        pass

    class A(B, C):
        pass

    tester = A
    expected = (A, B, E, C, D, F, object)


class _Example3:
    class A:
        pass

    class B:
        pass

    class C:
        pass

    class D:
        pass

    class E:
        pass

    class K1(A, B, C):
        pass

    class K2(D, B, E):
        pass

    class K3(D, A):
        pass

    class Z(K1, K2, K3):
        pass

    tester = Z
    expected = (Z, K1, K2, K3, D, A, B, C, E, object)


@pytest.mark.parametrize("example", [_Example0, _Example1, _Example2, _Example3])
def test_mro_case(example: Any) -> None:
    tester: type = getattr(example, "tester")
    expected: tuple[type, ...] = getattr(example, "expected")

    # First test that the expected result is the same as what Python
    # actually generates.
    assert expected == tester.__mro__

    # Now check the calculated MRO.
    assert mro(tester) == expected


def test_mro_example_3_subcases() -> None:
    assert mro(_Example3.A) == (_Example3.A, object)
    assert mro(_Example3.B) == (_Example3.B, object)
    assert mro(_Example3.C) == (_Example3.C, object)
    assert mro(_Example3.D) == (_Example3.D, object)
    assert mro(_Example3.E) == (_Example3.E, object)
    assert mro(_Example3.K1) == (_Example3.K1, _Example3.A, _Example3.B, _Example3.C, object)
    assert mro(_Example3.K2) == (_Example3.K2, _Example3.D, _Example3.B, _Example3.E, object)
    assert mro(_Example3.K3) == (_Example3.K3, _Example3.D, _Example3.A, object)
