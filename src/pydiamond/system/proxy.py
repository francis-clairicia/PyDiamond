# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = [
    "CallableProxyType",
    "ProxyType",
    "proxy",
]

from typing import TYPE_CHECKING, Any, Callable, ClassVar, SupportsIndex, TypeVar
from weakref import WeakSet, WeakValueDictionary

from ..system.collections import WeakKeyDefaultDictionary

# Inspired from https://code.activestate.com/recipes/496741-object-proxying/

_T = TypeVar("_T")


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
        if name in ProxyType.__special_names_pickle:
            return object.__getattribute__(self, name)
        obj: Any = object.__getattribute__(self, "_obj")
        value: Any = getattr(obj, name)
        return value if value is not obj else self

    def __setattr__(self, name: str, value: Any, /) -> None:
        if name in ProxyType.__special_names_pickle:
            return object.__setattr__(self, name, value)
        obj: Any = object.__getattribute__(self, "_obj")
        setattr(obj, name, value if value is not obj else self)

    def __delattr__(self, name: str, /) -> None:
        if name in ProxyType.__special_names_pickle:
            return object.__delattr__(self, name)
        delattr(object.__getattribute__(self, "_obj"), name)

    def __bool__(self) -> bool:
        return bool(object.__getattribute__(self, "_obj"))

    def __str__(self) -> str:
        return str(object.__getattribute__(self, "_obj"))

    def __repr__(self) -> str:
        obj: object = object.__getattribute__(self, "_obj")
        return f"<{type(self).__qualname__} at {id(self):#x}; to {obj!r}>"

    def __reduce_ex__(self, __protocol: SupportsIndex) -> str | tuple[Any, ...]:
        proxy_cls: type[Any] = type(self)
        dynmaic_classes = ProxyType.__dynamic_classes
        while proxy_cls in dynmaic_classes:
            proxy_cls = proxy_cls.__base__
        return proxy_cls, (object.__getattribute__(self, "_obj"),)

    def __reduce__(self) -> str | tuple[Any, ...]:
        proxy_cls: type[Any] = type(self)
        dynmaic_classes = ProxyType.__dynamic_classes
        while proxy_cls in dynmaic_classes:
            proxy_cls = proxy_cls.__base__
        return proxy_cls, (object.__getattribute__(self, "_obj"),)

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

    __special_names_returning_self = [
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
        "__ior__",
        "__ipow__",
        "__irshift__",
        "__isub__",
        "__itruediv__",
        "__ixor__",
    ]

    # fmt: off
    assert not (set(__special_names_returning_self) - set(__special_names)), (set(__special_names_returning_self) - set(__special_names))
    # fmt: on

    __special_names_pickle = [
        "__getnewargs__",
        "__getnewargs_ex__",
        "__getstate__",
        "__reduce__",
        "__reduce_ex__",
        "__setstate__",
    ]

    @classmethod
    def __create_class_proxy(cls, theclass: type[Any], *, callable: bool) -> type[ProxyType]:
        """creates a proxy for the given class"""

        from types import new_class

        def make_method(name: str) -> Callable[..., Any]:
            if name not in ProxyType.__special_names_returning_self:

                def method(self: object, *args: Any, **kwargs: Any) -> Any:
                    obj = object.__getattribute__(self, "_obj")
                    value = getattr(obj, name)(*args, **kwargs)
                    if value is obj:
                        return self
                    return value

            else:

                def method(self: object, *args: Any, **kwargs: Any) -> Any:
                    proxy_cls: type[Any] = type(self)
                    obj = object.__getattribute__(self, "_obj")
                    value = getattr(obj, name)(*args, **kwargs)
                    if value is obj:
                        return self
                    return proxy_cls(value)

            return method

        cls_name: str = f"{cls.__name__}({theclass.__name__})"
        cls_bases: tuple[object, ...] = (cls,)
        if callable and not issubclass(cls, CallableProxyType):
            if issubclass(CallableProxyType, cls):
                cls_bases = (CallableProxyType,)
            else:
                cls_bases = (cls, CallableProxyType)

        def exec_body(namespace: dict[str, Any]) -> None:
            namespace["__class__"] = property(lambda _: theclass)
            namespace["__qualname__"] = cls_name
            namespace["__module__"] = __name__
            namespace["__slots__"] = ()
            for name in ProxyType.__special_names:
                if hasattr(theclass, name):
                    namespace[name] = make_method(name)
            if not hasattr(cls, "__weakref__") and hasattr(theclass, "__weakref__"):
                namespace["__slots__"] += ("__weakref__",)

        return new_class(cls_name, cls_bases, exec_body=exec_body)

    __class_proxy_cache: ClassVar[WeakKeyDefaultDictionary[type[ProxyType], WeakValueDictionary[type[Any], type[ProxyType]]]]
    __class_proxy_cache = WeakKeyDefaultDictionary(WeakValueDictionary)
    __dynamic_classes: WeakSet[type[ProxyType]] = WeakSet()

    def __new__(cls, obj: Any, /, *args: Any, **kwargs: Any) -> Any:
        """
        creates an proxy instance referencing `obj`. (obj, *args, **kwargs) are
        passed to this class' __init__, so deriving classes can define an
        __init__ method of their own.
        note: _class_proxy_cache is unique per deriving class (each deriving
        class must hold its own cache)
        """
        while cls in ProxyType.__dynamic_classes:
            cls = cls.__base__
        cache: WeakValueDictionary[type[Any], type[ProxyType]] = ProxyType.__class_proxy_cache[cls]
        try:
            theclass = cache[obj.__class__]
        except KeyError:
            cache[obj.__class__] = theclass = cls.__create_class_proxy(obj.__class__, callable=callable(obj))
            ProxyType.__class_proxy_cache[theclass] = WeakValueDictionary({obj.__class__: theclass})
            ProxyType.__dynamic_classes.add(theclass)
        return object.__new__(theclass)


class CallableProxyType(ProxyType):
    __slots__ = ()

    if TYPE_CHECKING:

        def __new__(cls, obj: Callable[..., Any], /, *args: Any, **kwargs: Any) -> Any:
            ...

        def __init__(self, obj: Callable[..., Any], /) -> None:
            ...

    def __call__(__self, /, *args: Any, **kwargs: Any) -> Any:
        obj: Callable[..., Any] = object.__getattribute__(__self, "_obj")
        value: Any = obj(*args, **kwargs)
        return value if value is not obj else __self


def proxy(obj: _T, proxy_cls: type[ProxyType] | None = None) -> _T:
    if proxy_cls is not None:
        if not issubclass(proxy_cls, ProxyType):
            raise TypeError("proxy_cls must be a ProxyType subclass")
        return proxy_cls(obj)  # type: ignore[return-value]
    return ProxyType(obj)  # type: ignore[return-value]
