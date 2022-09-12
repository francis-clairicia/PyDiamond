# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = [
    "CallableProxyType",
    "ProxyType",
    "proxy",
]

from typing import TYPE_CHECKING, Any, Callable, ClassVar, TypeVar
from weakref import WeakKeyDictionary, WeakValueDictionary

# Inspired from https://code.activestate.com/recipes/496741-object-proxying/

_T = TypeVar("_T")


# TODO: pickling proxy
class ProxyType(object):
    __slots__ = ("_obj",)

    def __init__(self, obj: Any, /) -> None:
        if issubclass(type(self), type(obj)):
            obj = object.__getattribute__(obj, "_obj")
        object.__setattr__(self, "_obj", obj)

    #
    # proxying (special cases)
    #
    def __getattribute__(self, name: str, /) -> Any:
        return getattr(object.__getattribute__(self, "_obj"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        setattr(object.__getattribute__(self, "_obj"), name, value)

    def __delattr__(self, name: str, /) -> None:
        delattr(object.__getattribute__(self, "_obj"), name)

    def __bool__(self) -> bool:
        return bool(object.__getattribute__(self, "_obj"))

    def __str__(self) -> str:
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self) -> str:
        obj: object = object.__getattribute__(self, "_obj")
        return f"<{type(self).__qualname__} at {id(self):#x}; to {obj!r}>"

    #
    # factories
    #
    __special_names = [
        "__abs__",
        "__add__",
        "__and__",
        "__bytes__",
        "__concat__",
        "__contains__",
        "__delete__",
        "__delitem__",
        "__div__",
        "__divmod__",
        "__enter__",
        "__eq__",
        "__exit__",
        "__float__",
        "__floordiv__",
        "__format__",
        "__ge__",
        "__get__",
        "__getitem__",
        "__gt__",
        "__hash__",
        "__hex__",
        "__iadd__",
        "__iand__",
        "__iconcat__",
        "__idiv__",
        "__idivmod__",
        "__ifloordiv__",
        "__ilshift__",
        "__imod__",
        "__imul__",
        "__index__",
        "__int__",
        "__invert__",
        "__ior__",
        "__ipow__",
        "__irshift__",
        "__isub__",
        "__iter__",
        "__itruediv__",
        "__ixor__",
        "__le__",
        "__len__",
        "__lshift__",
        "__lt__",
        "__mod__",
        "__mul__",
        "__ne__",
        "__neg__",
        "__next__",
        "__oct__",
        "__or__",
        "__pos__",
        "__pow__",
        "__radd__",
        "__rand__",
        "__rdiv__",
        "__rdivmod__",
        "__reversed__",
        "__rfloorfiv__",
        "__rlshift__",
        "__rmod__",
        "__rmul__",
        "__ror__",
        "__round__",
        "__rpow__",
        "__rrshift__",
        "__rshift__",
        "__rsub__",
        "__rtruediv__",
        "__rxor__",
        "__set__",
        "__setitem__",
        "__sub__",
        "__truediv__",
        "__xor__",
    ]

    @classmethod
    def __create_class_proxy(cls, theclass: type[Any]) -> type[ProxyType]:
        """creates a proxy for the given class"""

        from types import new_class

        def make_method(name: str) -> Callable[..., Any]:
            def method(self: object, *args: Any, **kwargs: Any) -> Any:
                return getattr(object.__getattribute__(self, "_obj"), name)(*args, **kwargs)

            return method

        cls_name: str = f"{cls.__name__}({theclass.__name__})"

        def exec_body(namespace: dict[str, Any]) -> None:
            namespace["__class__"] = property(lambda _: theclass)
            namespace["__qualname__"] = cls_name
            namespace["__module__"] = __name__
            namespace["__slots__"] = ()
            for name in cls.__special_names:
                if hasattr(theclass, name):
                    namespace[name] = make_method(name)
            if not hasattr(cls, "__weakref__") and hasattr(theclass, "__weakref__"):
                namespace["__slots__"] += ("__weakref__",)
            elif not hasattr(theclass, "__weakref__") and hasattr(cls, "__weakref__"):
                raise TypeError(f"{cls.__qualname__} supports weak references while real object {cls.__qualname__} does not.")

        return new_class(cls_name, (cls,), exec_body=exec_body)

    __class_proxy_cache: ClassVar[WeakKeyDictionary[type[ProxyType], WeakValueDictionary[type[Any], type[ProxyType]]]]
    __class_proxy_cache = WeakKeyDictionary()

    def __new__(cls, obj: Any, /, *args: Any, **kwargs: Any) -> Any:
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        cache: WeakValueDictionary[type[Any], type[ProxyType]]
        try:
            cache = ProxyType.__class_proxy_cache[cls]
        except KeyError:
            ProxyType.__class_proxy_cache[cls] = cache = WeakValueDictionary()
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls.__create_class_proxy(obj.__class__)
            ProxyType.__class_proxy_cache[theclass] = WeakValueDictionary({obj.__class__: theclass})
        return object.__new__(theclass)


class CallableProxyType(ProxyType):
    __slots__ = ()

    if TYPE_CHECKING:

        def __new__(cls, obj: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
            ...

        def __init__(self, obj: Callable[..., Any], /) -> None:
            ...

    def __call__(__self, /, *args: Any, **kwargs: Any) -> Any:
        func: Callable[..., Any] = object.__getattribute__(__self, "_obj")
        return func(*args, **kwargs)


def proxy(obj: _T, *, proxy_cls: type[ProxyType] | None = None) -> _T:
    if proxy_cls is not None:
        if not issubclass(proxy_cls, ProxyType):
            raise TypeError("proxy_cls must be a ProxyType subclass")
        return proxy_cls(obj)  # type: ignore[return-value]
    if callable(obj):
        return CallableProxyType(obj)  # type: ignore[return-value]
    return ProxyType(obj)  # type: ignore[return-value]
