# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""NonCopyable objects module"""

from __future__ import annotations

__all__ = ["NonCopyable", "NonCopyableMeta"]


from typing import TYPE_CHECKING, Any, NoReturn, TypeVar

from .object import Object, ObjectMeta, final


class NonCopyableMeta(ObjectMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="NonCopyableMeta")

    def __new__(
        mcs: type[__Self],
        /,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> __Self:
        if any(attr in namespace for attr in ("__copy__", "__deepcopy__")):
            raise TypeError("'__copy__' and '__deepcopy__' cannot be overriden from a non-copyable object")
        if any(attr in namespace for attr in ("__reduce__", "__reduce_ex__")):
            raise TypeError("'__reduce__' and '__reduce_ex__' cannot be overriden from a non-copyable object")

        bases_final_methods_set: set[str] = {
            method_name for base in bases for method_name in getattr(base, "__finalmethods__", ())
        }

        if "__copy__" not in bases_final_methods_set:

            def __copy__(self: Any) -> Any:
                raise TypeError("Non copyable class")

            namespace["__copy__"] = final(__copy__)

        if "__deepcopy__" not in bases_final_methods_set:

            def __deepcopy__(self: Any, memo: dict[int, Any]) -> Any:
                raise TypeError("Non copyable class")

            namespace["__deepcopy__"] = final(__deepcopy__)

        if "__reduce_ex__" not in bases_final_methods_set:

            def __reduce_ex__(self: Any, __protocol: Any) -> str | tuple[Any, ...]:
                raise TypeError(f"cannot pickle {type(self).__qualname__!r} object")

            namespace["__reduce_ex__"] = final(__reduce_ex__)

        if "__reduce__" not in bases_final_methods_set:

            def __reduce__(self: Any) -> str | tuple[Any, ...]:
                raise TypeError(f"cannot pickle {type(self).__qualname__!r} object")

            namespace["__reduce__"] = final(__reduce__)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if "__dict__" in vars(cls):
            raise TypeError("Non copyable objects must not have __dict__ slot")
        return cls


class NonCopyable(Object, metaclass=NonCopyableMeta):
    __slots__ = ()

    if TYPE_CHECKING:

        @final
        def __copy__(self) -> NoReturn:
            ...

        @final
        def __deepcopy__(self, memo: dict[str, Any]) -> NoReturn:
            ...

        @final
        def __reduce_ex__(self, __protocol: Any) -> str | tuple[Any, ...]:
            ...

        @final
        def __reduce__(self) -> str | tuple[Any, ...]:
            ...
