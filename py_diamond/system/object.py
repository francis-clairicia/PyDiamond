# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Object/ObjectMeta module"""

from __future__ import annotations

__all__ = ["Object", "ObjectMeta", "final", "mro", "override"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta
from functools import cached_property
from itertools import chain, takewhile
from operator import truth
from typing import TYPE_CHECKING, Any, Callable, TypeVar, overload

from typing_extensions import final

_T = TypeVar("_T")


class ObjectMeta(ABCMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="ObjectMeta")

    __finalmethods__: frozenset[str]

    def __new__(
        mcs: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        no_slots: bool = False,
        **kwargs: Any,
    ) -> __Self:
        if no_slots and "__slots__" in namespace:
            raise TypeError("__slots__ override is forbidden")

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        name = cls.__name__
        bases = cls.__bases__
        bases_mro = cls.__mro__[1:]  # Exclude 'cls'

        must_override = ObjectMeta.__must_override
        is_final_override = ObjectMeta.__is_final_override

        # Verify final bases
        final_bases: list[type]
        if final_bases := list(filter(lambda base: getattr(base, "__final__", False), bases)):
            raise TypeError(
                f"{name!r}: Base classes marked as final class: {', '.join(base.__qualname__ for base in final_bases)}"
            )

        # Retrieve final methods from base and exclusive to bases
        bases_final_methods_dict: dict[type, set[str]] = {
            base: {
                method_name
                for method_name in getattr(base, "__finalmethods__", ())
                if not any(method_name in getattr(b, "__finalmethods__", ()) for b in base.__bases__)
            }
            for base in bases_mro
        }
        bases_final_methods_set: set[str] = set(chain.from_iterable(bases_final_methods_dict.values()))

        # Verify conflict for final methods in multiple inheritance
        conflict_final_methods: dict[str, set[type]] = {
            method_name: bases_set
            for method_name in bases_final_methods_set
            if len(
                (
                    bases_set := {
                        base
                        for actual_base in bases_mro
                        if method_name in bases_final_methods_dict.get(actual_base, [])
                        for base in chain(
                            takewhile(
                                lambda base: base is not actual_base,
                                (base for base in bases_mro if method_name in vars(base)),
                            ),
                            [actual_base],
                        )
                    }
                )
            )
            > 1
        }

        if conflict_final_methods:
            conflict_message = ", ".join(
                f"{method} in {tuple(b.__qualname__ for b in bases)}" for method, bases in conflict_final_methods.items()
            )
            raise TypeError(f"{name!r}: Final methods conflict between base classes: {conflict_message}")

        # Verify final override
        if final_methods_overridden := list(filter(bases_final_methods_set.__contains__, namespace)):
            final_method_overridden_names = ", ".join(repr(f) for f in final_methods_overridden)
            raise TypeError(f"{name!r}: These attributes would override final methods: {final_method_overridden_names}")

        # Verify override() decorator usage
        if methods_that_will_not_override := [
            attr_name
            for attr_name in {attr_name for attr_name, attr_obj in namespace.items() if must_override(attr_obj)}
            if not any(hasattr(b, attr_name) for b in bases)
        ]:
            method_names_that_will_not_override = ", ".join(repr(f) for f in methods_that_will_not_override)
            raise TypeError(f"{name!r}: These methods will not override base method: {method_names_that_will_not_override}")

        # Retrieve final methods from namespace
        cls_final_methods: set[str] = {attr_name for attr_name, attr_obj in namespace.items() if is_final_override(attr_obj)}
        cls.__finalmethods__ = frozenset(bases_final_methods_set | cls_final_methods)

        return cls

    @staticmethod
    def __must_override(obj: Any) -> bool:
        return truth(ObjectMeta.__check_attr(obj, "__mustoverride__"))

    @staticmethod
    def __is_final_override(obj: Any) -> bool:
        return truth(ObjectMeta.__check_attr(obj, "__final__"))

    @staticmethod
    def __check_attr(obj: Any, attr: str) -> bool:
        if getattr(obj, attr, False):
            return True
        match obj:
            case property(fget=fget, fset=fset, fdel=fdel):
                return any(getattr(func, attr, False) for func in filter(callable, (fget, fset, fdel)))
            case classmethod(__func__=func) | staticmethod(__func__=func) | cached_property(func=func):
                return True if getattr(func, attr, False) else False
            case _:
                return False


class Object(metaclass=ObjectMeta):
    __slots__ = ()

    def __del__(self) -> None:
        pass


@overload
def override(f: _T, /) -> _T:
    ...


@overload
def override(*, final: bool = False) -> Callable[[_T], _T]:
    ...


def override(f: Any = ..., /, *, final: bool = False) -> Any:
    final = bool(final)

    def apply_markers(f: Any) -> None:
        setattr(f, "__mustoverride__", True)
        setattr(f, "__final__", final)

    def decorator(f: Any) -> Any:
        match f:
            case property(fget=fget, fset=fset, fdel=fdel):
                for func in filter(callable, (fget, fset, fdel)):
                    apply_markers(func)
            case classmethod(__func__=func) | staticmethod(__func__=func) | cached_property(func=func):
                apply_markers(f)
                apply_markers(func)
            case type():
                raise TypeError("override() must not decorate classes")
            case _ if not callable(f) and not hasattr(f, "__get__"):
                raise TypeError("override() must only decorate functions and descriptors")
            case _:
                apply_markers(f)
        return f

    return decorator if f is Ellipsis else decorator(f)


# Ref: https://code.activestate.com/recipes/577748-calculate-the-mro-of-a-class/
def mro(*bases: type, attr: str = "__mro__") -> tuple[type, ...]:
    """Calculate the Method Resolution Order of bases using the C3 algorithm.

    Suppose you intended creating a class K with the given base classes. This
    function returns the MRO which K would have, *excluding* K itself (since
    it doesn't yet exist), as if you had actually created the class.

    Another way of looking at this, if you pass a single class K, this will
    return the linearization of K (the MRO of K, *including* itself).
    """
    if not bases:
        return ()
    seqs: list[list[type]] = [list(getattr(C, attr, C.__mro__) if attr != "__mro__" else C.__mro__) for C in bases]
    seqs += [list(bases)]
    res: list[type] = []
    while True:
        non_empty = list(filter(None, seqs))
        if not non_empty:
            # Nothing left to process, we're done.
            return tuple(res)
        candidate: type | None = None
        for seq in non_empty:  # Find merge candidates among seq heads.
            candidate = seq[0]
            not_head = [s for s in non_empty if candidate in s[1:]]
            if not_head:
                # Reject the candidate.
                candidate = None
            else:
                break
        if not candidate:
            raise TypeError("inconsistent hierarchy, no C3 MRO is possible")
        res.append(candidate)
        for seq in non_empty:
            # Remove candidate.
            if seq[0] == candidate:
                del seq[0]
