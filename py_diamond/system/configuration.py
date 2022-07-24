# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Configuration module"""

from __future__ import annotations

__all__ = [
    "Configuration",
    "ConfigurationError",
    "ConfigurationTemplate",
    "InitializationError",
    "InvalidAliasError",
    "OptionAttribute",
    "OptionError",
    "UnknownOptionError",
    "UnregisteredOptionError",
    "initializer",
]

import inspect
import re
from collections import ChainMap
from contextlib import ExitStack, contextmanager, suppress
from dataclasses import KW_ONLY, dataclass, field
from enum import Enum
from functools import cache, update_wrapper, wraps
from itertools import chain, combinations
from threading import RLock
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    AbstractSet as Set,
    Any,
    Callable,
    ClassVar,
    Generic,
    Hashable,
    Iterator,
    Literal as L,
    Mapping,
    MutableMapping,
    NamedTuple,
    NoReturn,
    Protocol,
    Sequence,
    SupportsIndex,
    TypeAlias,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)
from weakref import ReferenceType as WeakReferenceType, WeakKeyDictionary, ref as weakref

from .object import Object, final
from .utils._mangling import mangle_private_attribute as _private_attribute

_FuncVar = TypeVar("_FuncVar", bound=Callable[..., Any])
_UpdaterVar = TypeVar("_UpdaterVar", bound=Callable[[Any], None])
_KeyUpdaterVar = TypeVar("_KeyUpdaterVar", bound=Callable[[Any, Any], None])
_ValueUpdaterVar = TypeVar("_ValueUpdaterVar", bound=Callable[[Any, Any], None])
_KeyValueUpdaterVar = TypeVar("_KeyValueUpdaterVar", bound=Callable[[Any, Any, Any], None])
_GetterVar = TypeVar("_GetterVar", bound=Callable[[Any], Any])
_SetterVar = TypeVar("_SetterVar", bound=Callable[[Any, Any], None])
_DeleterVar = TypeVar("_DeleterVar", bound=Callable[[Any], None])
_KeyGetterVar = TypeVar("_KeyGetterVar", bound=Callable[[Any, Any], Any])
_KeySetterVar = TypeVar("_KeySetterVar", bound=Callable[[Any, Any, Any], None])
_KeyDeleterVar = TypeVar("_KeyDeleterVar", bound=Callable[[Any, Any], None])
_ValueValidatorVar = TypeVar("_ValueValidatorVar", bound=Callable[[Any, Any], Any])
_StaticValueValidatorVar = TypeVar("_StaticValueValidatorVar", bound=Callable[[Any], Any])
_ValueConverterVar = TypeVar("_ValueConverterVar", bound=Callable[[Any, Any], Any])
_StaticValueConverterVar = TypeVar("_StaticValueConverterVar", bound=Callable[[Any], Any])
_T = TypeVar("_T")
_DT = TypeVar("_DT")


class ConfigurationError(Exception):
    pass


class OptionError(ConfigurationError):
    def __init__(self, name: str, message: str) -> None:
        if name:
            message = f"{name!r}: {message}"
        super().__init__(message)
        self.name: str = name


class UnknownOptionError(OptionError):
    def __init__(self, name: str, message: str = "") -> None:
        if not message:
            if name:
                message = "Unknown config option"
            else:
                message = "Empty string given"
        super().__init__(name, message)


class UnregisteredOptionError(OptionError, AttributeError):
    def __init__(self, name: str) -> None:
        super().__init__(name, "Unregistered option")


class InvalidAliasError(OptionError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(name, message)


class InitializationError(ConfigurationError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def initializer(func: _FuncVar) -> _FuncVar:
    return _ConfigInitializer(func)  # type: ignore[return-value]


_ALLOWED_OPTIONS_PATTERN = re.compile(r"(?!__)(?:[a-zA-Z]\w*|_\w+)(?<!__)")
_MISSING: Any = object()
_NO_DEFAULT: Any = object()


@final
class ConfigurationTemplate(Object):
    __slots__ = (
        "__template",
        "__no_parent_ownership",
        "__bound_class",
        "__attr_name",
        "__cache_lock",
        "__info",
    )

    __cache: WeakKeyDictionary[Any, Configuration[Any]] = WeakKeyDictionary()

    def __init__(
        self,
        *known_options: str,
        parent: ConfigurationTemplate | Sequence[ConfigurationTemplate] | None = None,
    ) -> None:
        for option in known_options:
            if not option:
                raise ValueError("Configuration option must not be empty")
            if not _ALLOWED_OPTIONS_PATTERN.fullmatch(option):
                if option.startswith("__") or option.endswith("__"):
                    raise ValueError(f"{option!r}: Only one leading/trailing underscore is accepted")
                raise ValueError(f"{option!r}: Forbidden option format")
        if parent is None:
            parent = []
        elif isinstance(parent, ConfigurationTemplate):
            parent = [parent]

        if not all(p1.name == p2.name for p1, p2 in combinations(parent, r=2)):
            raise AttributeError("Parents' ConfigurationTemplate name mismatch")

        self.__template: _ConfigInfoTemplate = _ConfigInfoTemplate(known_options, list(p.__template for p in parent))
        self.__bound_class: type | None = None
        self.__attr_name: str | None = parent[0].name if parent else None
        self.__cache_lock = RLock()
        self.__info: ConfigurationInfo[Any] | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({{{', '.join(map(repr, sorted(self.known_options())))}}})"

    def __set_name__(self, owner: type, name: str, /) -> None:
        if self.__bound_class is not None:
            raise TypeError(f"This configuration object is bound to a class: {self.__bound_class.__name__!r}")

        if self.__attr_name is not None and name != self.__attr_name:
            raise AttributeError("Configuration name mismatch")

        if not hasattr(owner, "__weakref__") and not inspect.isabstract(owner):
            raise TypeError(f"{owner.__qualname__} objects are not weak-referenceable. Consider adding '__weakref__' to slots.")

        if getattr(owner, name) is not self:
            raise AttributeError("The attribute name does not correspond")
        template: _ConfigInfoTemplate = self.__template
        if name in template.options:
            raise OptionError(name, "ConfigurationTemplate attribute name is an option")

        def retrieve_config_or_none(cls: type) -> ConfigurationTemplate | None:
            try:
                return _retrieve_configuration(cls)
            except TypeError:
                return None

        if list(template.parents) != [config.__template for config in map(retrieve_config_or_none, owner.__bases__) if config]:
            raise TypeError("Inconsistent configuration template hierarchy")

        self.__bound_class = owner
        self.__attr_name = name
        for option in template.options:
            descriptor: _Descriptor | None = template.value_descriptor.get(option)
            if descriptor not in template.parent_descriptors and hasattr(descriptor, "__set_name__"):
                getattr(descriptor, "__set_name__")(owner, option)
        for obj in _all_members(owner).values():
            if isinstance(obj, OptionAttribute):
                try:
                    obj.owner
                    obj.name
                except AttributeError:
                    continue
                if obj.owner is not owner:
                    new_option_attribute: OptionAttribute[Any] = OptionAttribute()
                    new_option_attribute.__doc__ = obj.__doc__
                    setattr(owner, obj.name, new_option_attribute)
                    new_option_attribute.__set_name__(owner, obj.name)
            elif isinstance(obj, ConfigurationTemplate) and obj is not self:
                raise TypeError(f"A class can't have several {ConfigurationTemplate.__name__!r} objects")
        self.__info = template.build(owner)

        default_init_subclass = owner.__init_subclass__

        @wraps(default_init_subclass)
        def __init_subclass__(cls: type, **kwargs: Any) -> None:
            config: ConfigurationTemplate = getattr(cls, name)
            if config.__bound_class is not cls:
                subclass_config = ConfigurationTemplate(parent=list(filter(None, map(retrieve_config_or_none, cls.__bases__))))
                setattr(cls, name, subclass_config)
                subclass_config.__set_name__(cls, name)
            return default_init_subclass(**kwargs)

        owner.__init_subclass__ = classmethod(__init_subclass__)  # type: ignore[assignment]

    @overload
    def __get__(self, obj: None, objtype: type, /) -> ConfigurationTemplate:
        ...

    @overload
    def __get__(self, obj: _T, objtype: type | None = None, /) -> Configuration[_T]:
        ...

    def __get__(self, obj: Any, objtype: type | None = None, /) -> ConfigurationTemplate | Configuration[Any]:
        if obj is None:
            if objtype is None:
                raise TypeError("__get__(None, None) is invalid")
            return self

        if self.__bound_class is not (objtype if objtype is not None else type(obj)):  # called by super()
            return Configuration(weakref(obj), self.info)

        try:
            return self.__cache[obj]
        except KeyError:
            pass

        info = self.info

        with self.__cache_lock:
            try:
                return self.__cache[obj]
            except KeyError:  # Not added by another thread
                self.__cache[obj] = bound_config = Configuration(weakref(obj), info)
                return bound_config

    def __set__(self, obj: _T, value: Any) -> None:
        raise AttributeError("Read-only attribute")

    def __delete__(self, obj: _T) -> None:
        raise AttributeError("Read-only attribute")

    def known_options(self) -> frozenset[str]:
        return self.__template.options

    def known_aliases(self) -> frozenset[str]:
        return frozenset(self.__template.aliases)

    def check_option_validity(self, option: str, *, use_alias: bool = False) -> str:
        template = self.__template
        if not isinstance(option, str):
            raise TypeError(f"Expected str, got {type(option).__qualname__}")
        if use_alias:
            option = template.aliases.get(option, option)
        if option not in template.options:
            raise UnknownOptionError(option)
        return option

    def is_option_valid(self, option: str, *, use_alias: bool = False) -> bool:
        try:
            self.check_option_validity(option, use_alias=use_alias)
        except UnknownOptionError:
            return False
        return True

    def remove_parent_ownership(self, option: str) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        template = self.__template
        try:
            actual_descriptor = template.value_descriptor[option]
        except KeyError as exc:
            raise OptionError(option, "There is no parent ownership") from exc
        if not isinstance(actual_descriptor, _PrivateAttributeOptionProperty):
            if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
                underlying_descriptor = actual_descriptor.get_descriptor()
                if underlying_descriptor is None:
                    raise OptionError(option, "There is no parent ownership")
                if isinstance(actual_descriptor, _PrivateAttributeOptionProperty):
                    actual_descriptor.set_new_descriptor(None)
                    return
                actual_descriptor = underlying_descriptor
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        del template.value_descriptor[option]

    @overload
    def getter(self, option: str, /, *, use_override: bool = True, readonly: bool = False) -> Callable[[_GetterVar], _GetterVar]:
        ...

    @overload
    def getter(self, option: str, func: _GetterVar, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    def getter(
        self, option: str, func: _GetterVar | None = None, /, *, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_GetterVar], _GetterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: _Descriptor | None = template.value_descriptor.get(option)
        if not isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            if actual_descriptor is not None:
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            actual_property: _ConfigProperty | None = actual_descriptor
            if (
                actual_property is not None
                and readonly
                and (actual_property.fset is not None or actual_property.fdel is not None)
            ):
                raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            if readonly and (
                template.option_update_hooks.get(option)
                or template.option_value_update_hooks.get(option)
                or template.option_delete_hooks.get(option)
            ):
                raise OptionError(option, "Trying to flag option as read-only with registered update/delete hooks")

            def decorator(func: _GetterVar, /) -> _GetterVar:
                wrapper = _make_function_wrapper(func, use_override=bool(use_override))
                new_config_property: property
                if actual_property is None:
                    new_config_property = _ConfigProperty(wrapper)
                else:
                    new_config_property = actual_property.getter(wrapper)
                if readonly:
                    template.value_descriptor[option] = _ReadOnlyOptionBuildPayload(new_config_property)
                else:
                    template.value_descriptor[option] = new_config_property
                return func

        else:
            readonly_descriptor: _ReadOnlyOptionBuildPayload = actual_descriptor
            actual_descriptor = readonly_descriptor.get_descriptor()
            if not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            config_property: _ConfigProperty = actual_descriptor

            def decorator(func: _GetterVar, /) -> _GetterVar:
                wrapper = _make_function_wrapper(func, use_override=bool(use_override))
                readonly_descriptor.set_new_descriptor(config_property.getter(wrapper))
                return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def getter_with_key(
        self, option: str, /, *, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_with_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_with_key(self, option: str, func: _KeyGetterVar, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    @overload
    def getter_with_key(
        self, option: str, func: _KeyGetterVar, /, *, use_key: Hashable, use_override: bool = True, readonly: bool = False
    ) -> None:
        ...

    def getter_with_key(
        self,
        option: str,
        func: _KeyGetterVar | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
        readonly: bool = False,
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        if use_key is _NO_DEFAULT:
            use_key = option
        else:
            hash(use_key)
        key: Hashable = (option, use_key)

        def wrapper_decorator(func: Callable[..., Any], *, use_key: Hashable = use_key) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyGetterVar, /) -> _KeyGetterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, use_override=bool(use_override), no_object=False)
            self.getter(option, wrapper, readonly=readonly)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def getter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
        ignore_key_error: bool = False,
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyGetterVar,
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
        ignore_key_error: bool = False,
    ) -> None:
        ...

    def getter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
        ignore_key_error: bool = False,
    ) -> Any:
        try:
            use_key: Hashable = key_map[option]
        except KeyError:
            if not ignore_key_error:
                raise
            use_key = option
        return self.getter_with_key(option, func, use_key=use_key, use_override=use_override, readonly=readonly)

    @overload
    def setter(self, option: str, /, *, use_override: bool = True) -> Callable[[_SetterVar], _SetterVar]:
        ...

    @overload
    def setter(self, option: str, func: _SetterVar, /, *, use_override: bool = True) -> None:
        ...

    def setter(
        self, option: str, func: _SetterVar | None = None, /, *, use_override: bool = True
    ) -> Callable[[_SetterVar], _SetterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: _Descriptor | None = template.value_descriptor.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing setter for this option which has no getter")
        if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            raise OptionError(option, "Read-only option")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _SetterVar, /) -> _SetterVar:
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            template.value_descriptor[option] = actual_property.setter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter_with_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_with_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_with_key(self, option: str, func: _KeySetterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def setter_with_key(self, option: str, func: _KeySetterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def setter_with_key(
        self,
        option: str,
        func: _KeySetterVar | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeySetterVar], _KeySetterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        if use_key is _NO_DEFAULT:
            use_key = option
        else:
            hash(use_key)
        key: Hashable = (option, use_key)

        def wrapper_decorator(func: Callable[..., Any], *, use_key: Hashable = use_key) -> Callable[..., Any]:
            return lambda self, value: func(self, use_key, value)

        def decorator(func: _KeySetterVar, /) -> _KeySetterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, use_override=bool(use_override), no_object=False)
            self.setter(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeySetterVar,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> None:
        ...

    def setter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Any:
        try:
            use_key: Hashable = key_map[option]
        except KeyError:
            if not ignore_key_error:
                raise
            use_key = option
        return self.setter_with_key(option, func, use_key=use_key, use_override=use_override)

    @overload
    def deleter(self, option: str, /, *, use_override: bool = True) -> Callable[[_DeleterVar], _DeleterVar]:
        ...

    @overload
    def deleter(self, option: str, func: _DeleterVar, /, *, use_override: bool = True) -> None:
        ...

    def deleter(
        self, option: str, func: _DeleterVar | None = None, /, *, use_override: bool = True
    ) -> Callable[[_DeleterVar], _DeleterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: _Descriptor | None = template.value_descriptor.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing deleter for this option which has no getter")
        if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            raise OptionError(option, "Read-only option")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _DeleterVar, /) -> _DeleterVar:
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            template.value_descriptor[option] = actual_property.deleter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter_with_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_with_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_with_key(self, option: str, func: _KeyDeleterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def deleter_with_key(self, option: str, func: _KeyDeleterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def deleter_with_key(
        self,
        option: str,
        func: _KeyDeleterVar | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        if use_key is _NO_DEFAULT:
            use_key = option
        else:
            hash(use_key)
        key: Hashable = (option, use_key)

        def wrapper_decorator(func: Callable[..., Any], *, use_key: Hashable = use_key) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyDeleterVar, /) -> _KeyDeleterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, use_override=bool(use_override), no_object=False)
            self.deleter(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyDeleterVar,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> None:
        ...

    def deleter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Any:
        try:
            use_key: Hashable = key_map[option]
        except KeyError:
            if not ignore_key_error:
                raise
            use_key = option
        return self.deleter_with_key(option, func, use_key=use_key, use_override=use_override)

    def use_descriptor(self, option: str, descriptor: _Descriptor) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: _Descriptor
        if (
            option in template.value_descriptor
            and (actual_descriptor := template.value_descriptor[option]) not in template.parent_descriptors
        ):
            if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
                underlying_descriptor = actual_descriptor.get_descriptor()
                if underlying_descriptor is None:
                    raise OptionError(option, "Already uses custom getter register with getter() method")
                actual_descriptor = underlying_descriptor
            if isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, "Already uses custom getter register with getter() method")
            if not isinstance(descriptor, actual_descriptor.__class__):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        template.value_descriptor[option] = descriptor

    def reset_getter_setter_deleter(self, option: str) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        if option not in template.value_descriptor or template.value_descriptor[option] not in template.parent_descriptors:
            raise OptionError(option, "reset() accepted only when a descriptor is inherited from parent")
        actual_descriptor = template.value_descriptor[option]
        if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            underlying_descriptor = actual_descriptor.get_descriptor()
            if not isinstance(underlying_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(underlying_descriptor).__name__}")
            actual_descriptor.set_new_descriptor(None)
            return
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        del template.value_descriptor[option]

    @overload
    def add_main_update(self, func: _UpdaterVar, /, *, use_override: bool = True) -> _UpdaterVar:
        ...

    @overload
    def add_main_update(self, /, *, use_override: bool = True) -> Callable[[_UpdaterVar], _UpdaterVar]:
        ...

    def add_main_update(
        self, func: _UpdaterVar | None = None, /, *, use_override: bool = True
    ) -> _UpdaterVar | Callable[[_UpdaterVar], _UpdaterVar]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        def decorator(func: _UpdaterVar, /) -> _UpdaterVar:
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in template.main_update_hooks:
                raise ConfigurationError("Function already registered")
            template.main_update_hooks.add(wrapper)
            return func

        if func is None:
            return decorator
        return decorator(func)

    @overload
    def on_update(self, option: str, /, *, use_override: bool = True) -> Callable[[_UpdaterVar], _UpdaterVar]:
        ...

    @overload
    def on_update(self, option: str, func: _UpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    def on_update(
        self, option: str, func: _UpdaterVar | None = None, /, *, use_override: bool = True
    ) -> Callable[[_UpdaterVar], _UpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _UpdaterVar, /) -> _UpdaterVar:
            if isinstance(template.value_descriptor.get(option), _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Cannot add update hook on read-only option")
            updater_list = template.option_update_hooks.setdefault(option, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.add(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_with_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_with_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_with_key(self, option: str, func: _KeyUpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_with_key(self, option: str, func: _KeyUpdaterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def on_update_with_key(
        self,
        option: str,
        func: _KeyUpdaterVar | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        if use_key is _NO_DEFAULT:
            use_key = option
        else:
            hash(use_key)
        key: Hashable = (option, use_key)

        def wrapper_decorator(func: Callable[..., Any], *, use_key: Hashable = use_key) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyUpdaterVar, /) -> _KeyUpdaterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, use_override=bool(use_override), no_object=False)
            self.on_update(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyUpdaterVar,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> None:
        ...

    def on_update_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Any:
        try:
            use_key: Hashable = key_map[option]
        except KeyError:
            if not ignore_key_error:
                raise
            use_key = option
        return self.on_update_with_key(option, func, use_key=use_key, use_override=use_override)

    @overload
    def on_update_value(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueUpdaterVar], _ValueUpdaterVar]:
        ...

    @overload
    def on_update_value(self, option: str, func: _ValueUpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    def on_update_value(
        self, option: str, func: _ValueUpdaterVar | None = None, /, *, use_override: bool = True
    ) -> Callable[[_ValueUpdaterVar], _ValueUpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _ValueUpdaterVar, /) -> _ValueUpdaterVar:
            if isinstance(template.value_descriptor.get(option), _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Cannot add update hook on read-only option")
            updater_list = template.option_value_update_hooks.setdefault(option, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.add(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_value_with_key(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_value_with_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_value_with_key(self, option: str, func: _KeyValueUpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_value_with_key(
        self, option: str, func: _KeyValueUpdaterVar, /, *, use_key: Hashable, use_override: bool = True
    ) -> None:
        ...

    def on_update_value_with_key(
        self,
        option: str,
        func: _KeyValueUpdaterVar | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        if use_key is _NO_DEFAULT:
            use_key = option
        else:
            hash(use_key)
        key: Hashable = (option, use_key)

        def wrapper_decorator(func: Callable[..., Any], *, use_key: Hashable = use_key) -> Callable[..., Any]:
            return lambda self, value: func(self, use_key, value)

        def decorator(func: _KeyValueUpdaterVar, /) -> _KeyValueUpdaterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, use_override=bool(use_override), no_object=False)
            self.on_update_value(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_value_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_value_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyValueUpdaterVar,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> None:
        ...

    def on_update_value_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Any:
        try:
            use_key: Hashable = key_map[option]
        except KeyError:
            if not ignore_key_error:
                raise
            use_key = option
        return self.on_update_value_with_key(option, func, use_key=use_key, use_override=use_override)

    @overload
    def on_delete(self, option: str, /, *, use_override: bool = True) -> Callable[[_UpdaterVar], _UpdaterVar]:
        ...

    @overload
    def on_delete(self, option: str, func: _UpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    def on_delete(
        self, option: str, func: _UpdaterVar | None = None, /, *, use_override: bool = True
    ) -> Callable[[_UpdaterVar], _UpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _UpdaterVar, /) -> _UpdaterVar:
            if isinstance(template.value_descriptor.get(option), _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Cannot add delete hook on read-only option")
            updater_list = template.option_delete_hooks.setdefault(option, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.add(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_delete_with_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_delete_with_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_delete_with_key(self, option: str, func: _KeyUpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_delete_with_key(self, option: str, func: _KeyUpdaterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def on_delete_with_key(
        self,
        option: str,
        func: _KeyUpdaterVar | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar] | None:
        self.__check_locked()
        self.check_option_validity(option)
        if use_key is _NO_DEFAULT:
            use_key = option
        else:
            hash(use_key)
        key: Hashable = (option, use_key)

        def wrapper_decorator(func: Callable[..., Any], *, use_key: Hashable = use_key) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyUpdaterVar, /) -> _KeyUpdaterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, use_override=bool(use_override), no_object=False)
            self.on_delete(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_delete_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_delete_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyUpdaterVar,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> None:
        ...

    def on_delete_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        ignore_key_error: bool = False,
    ) -> Any:
        try:
            use_key: Hashable = key_map[option]
        except KeyError:
            if not ignore_key_error:
                raise
            use_key = option
        return self.on_delete_with_key(option, func, use_key=use_key, use_override=use_override)

    @overload
    def add_value_validator(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_ValueValidatorVar], _ValueValidatorVar]:
        ...

    @overload
    def add_value_validator(self, option: str, func: _ValueValidatorVar, /, *, use_override: bool = True) -> None:
        ...

    def add_value_validator(
        self,
        option: str,
        func: _ValueValidatorVar | None = None,
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_ValueValidatorVar], _ValueValidatorVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use value_validator_static() to check types")

        def decorator(func: _ValueValidatorVar, /) -> _ValueValidatorVar:
            value_validator_list = template.value_validator.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in value_validator_list:
                raise OptionError(option, "Function already registered")
            value_validator_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_validator_static(self, option: str, /) -> Callable[[_StaticValueValidatorVar], _StaticValueValidatorVar]:
        ...

    @overload
    def add_value_validator_static(self, option: str, objtype: type, /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_validator_static(self, option: str, objtypes: Sequence[type], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_validator_static(self, option: str, func: _StaticValueValidatorVar, /) -> None:
        ...

    def add_value_validator_static(
        self,
        option: str,
        func: _StaticValueValidatorVar | type | Sequence[type] | None = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Callable[[_StaticValueValidatorVar], _StaticValueValidatorVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _StaticValueValidatorVar, /) -> _StaticValueValidatorVar:
            value_validator_list = template.value_validator.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=False, no_object=True)
            if wrapper in value_validator_list:
                raise OptionError(option, "Function already registered")
            value_validator_list.append(wrapper)
            return func

        if isinstance(func, (type, Sequence)):
            _type: type | tuple[type, ...] = func if isinstance(func, type) else tuple(func)

            if isinstance(_type, tuple):
                if not _type or any(not isinstance(t, type) for t in _type):
                    raise TypeError("Invalid types argument")
                if len(_type) == 1:
                    _type = _type[0]

            type_checker: Any = _make_type_checker(_type, accept_none)

            decorator(type_checker)
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_converter_on_get(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar]:
        ...

    @overload
    def add_value_converter_on_get(self, option: str, func: _ValueConverterVar, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter_on_get(
        self,
        option: str,
        func: _ValueConverterVar | None = None,
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use add_value_converter_on_set_static() to convert value using type")

        def decorator(func: _ValueConverterVar, /) -> _ValueConverterVar:
            value_converter_list = template.value_converter_on_get.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            value_converter_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_converter_on_get_static(self, option: str, /) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar]:
        ...

    @overload
    def add_value_converter_on_get_static(self, option: str, convert_to_type: type[Any], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_converter_on_get_static(self, option: str, func: _StaticValueConverterVar, /) -> None:
        ...

    def add_value_converter_on_get_static(
        self,
        option: str,
        func: _StaticValueConverterVar | type | None = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _StaticValueConverterVar, /) -> _StaticValueConverterVar:
            value_converter_list = template.value_converter_on_get.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=False, no_object=True)
            value_converter_list.append(wrapper)
            return func

        if isinstance(func, type):

            if issubclass(func, Enum):
                raise TypeError("Use add_enum_converter() instead for enum conversions")

            value_converter: Any = _make_value_converter(func, accept_none)

            decorator(value_converter)
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_converter_on_set(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar]:
        ...

    @overload
    def add_value_converter_on_set(self, option: str, func: _ValueConverterVar, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter_on_set(
        self,
        option: str,
        func: _ValueConverterVar | None = None,
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use add_value_converter_on_set_static() to convert value using type")

        def decorator(func: _ValueConverterVar, /) -> _ValueConverterVar:
            value_converter_list = template.value_converter_on_set.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            value_converter_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_converter_on_set_static(self, option: str, /) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar]:
        ...

    @overload
    def add_value_converter_on_set_static(self, option: str, convert_to_type: type[Any], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_converter_on_set_static(self, option: str, func: _StaticValueConverterVar, /) -> None:
        ...

    def add_value_converter_on_set_static(
        self,
        option: str,
        func: _StaticValueConverterVar | type | None = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _StaticValueConverterVar, /) -> _StaticValueConverterVar:
            value_converter_list = template.value_converter_on_set.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=False, no_object=True)
            value_converter_list.append(wrapper)
            return func

        if isinstance(func, type):

            if issubclass(func, Enum):
                raise TypeError("Use add_enum_converter() instead for enum conversions")

            value_converter: Any = _make_value_converter(func, accept_none)

            decorator(value_converter)
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    def add_enum_converter(
        self,
        option: str,
        enum: type[Enum],
        *,
        accept_none: bool = False,
        store_value: bool = False,
        return_value_on_get: bool = False,
    ) -> None:
        self.__check_locked()
        self.check_option_validity(option)

        if not issubclass(enum, Enum):
            raise TypeError("Not an Enum class")

        self.add_value_converter_on_get_static(
            option,
            _make_enum_converter(enum, return_value_on_get, accept_none),
        )
        self.add_value_converter_on_set_static(
            option,
            _make_enum_converter(enum, store_value, accept_none),
        )

    def set_alias(self, option: str, alias: str, /, *aliases: str) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)
        for alias in {alias, *aliases}:
            if not isinstance(alias, str):
                raise InvalidAliasError(alias, "Invalid type")
            if alias == option:
                raise InvalidAliasError(alias, "Same name with option")
            if not alias:
                raise InvalidAliasError(alias, "Empty string alias")
            if alias in template.options:
                raise InvalidAliasError(alias, "Alias name is a configuration option")
            if alias in template.aliases:
                raise InvalidAliasError(alias, f"Already bound to option {template.aliases[alias]!r}")
            template.aliases[alias] = option

    def readonly(self, *options: str) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        for option in options:
            self.check_option_validity(option)
            descriptor: _Descriptor | None = template.value_descriptor.get(option)
            if isinstance(descriptor, _ReadOnlyOptionBuildPayload):
                continue
            if isinstance(descriptor, (_MutableDescriptor, _RemovableDescriptor)):
                if not isinstance(descriptor, property) or descriptor.fset is not None or descriptor.fdel is not None:
                    raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            if (
                template.option_update_hooks.get(option)
                or template.option_value_update_hooks.get(option)
                or template.option_delete_hooks.get(option)
            ):
                raise OptionError(option, "Trying to flag option as read-only with registered update/delete hooks")
            template.value_descriptor[option] = _ReadOnlyOptionBuildPayload(descriptor)

    def __check_locked(self) -> None:
        if self.__info is not None:
            raise TypeError(f"Attempt to modify template after the class creation")

    @property
    @final
    def owner(self) -> type | None:
        return self.__bound_class

    @property
    @final
    def name(self) -> str | None:
        return self.__attr_name

    @property
    @final
    def info(self) -> ConfigurationInfo[Any]:
        info = self.__info
        assert info is not None, "Cannot use ConfigurationTemplate instance without calling __set_name__ on it."
        return info


@final
class OptionAttribute(Generic[_T], Object):

    __slots__ = ("__name", "__owner", "__config_name", "__doc__")

    def __init__(self) -> None:
        super().__init__()
        self.__doc__ = None

    def __set_name__(self, owner: type, name: str, /) -> None:
        if len(name) == 0:
            raise ValueError("Attribute name must not be empty")
        with suppress(AttributeError):
            if self.__name != name:
                raise ValueError(f"Assigning {self.__name!r} config attribute to {name}")
        self.__owner: type = owner
        self.__name: str = name
        config: ConfigurationTemplate = _retrieve_configuration(owner)
        if config.name is None:
            raise TypeError("OptionAttribute must be declared after the ConfigurationTemplate object")
        config.check_option_validity(name, use_alias=True)
        self.__config_name: str = config.name

    @overload
    def __get__(self, obj: None, objtype: type, /) -> OptionAttribute[_T]:
        ...

    @overload
    def __get__(self, obj: object, objtype: type | None = None, /) -> _T:
        ...

    def __get__(self, obj: object, objtype: type | None = None, /) -> _T | OptionAttribute[_T]:
        if obj is None:
            return self
        name: str = self.__name
        config_template: ConfigurationTemplate = getattr(self.owner, self.__config_name)
        config: Configuration[Any] = config_template.__get__(obj, objtype)

        try:
            value: _T = config.get(name)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from exc
        return value

    def __set__(self, obj: object, value: _T, /) -> None:
        name: str = self.__name
        config: Configuration[Any] = getattr(obj, self.__config_name)
        try:
            config.set(name, value)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from exc

    def __delete__(self, obj: object, /) -> None:
        name: str = self.__name
        config: Configuration[Any] = getattr(obj, self.__config_name)
        try:
            config.delete(name)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from exc

    @property
    @final
    def owner(self) -> type:
        return self.__owner

    @property
    @final
    def name(self) -> str:
        return self.__name


def _default_mapping() -> MappingProxyType[Any, Any]:
    return MappingProxyType({})


@final
@dataclass(frozen=True, eq=False, slots=True)
class ConfigurationInfo(Object, Generic[_T]):
    options: Set[str]
    _: KW_ONLY
    option_value_update_hooks: Mapping[str, Set[Callable[[_T, Any], None]]] = field(default_factory=_default_mapping)
    option_delete_hooks: Mapping[str, Set[Callable[[_T], None]]] = field(default_factory=_default_mapping)
    option_update_hooks: Mapping[str, Set[Callable[[_T], None]]] = field(default_factory=_default_mapping)
    main_object_update_hooks: Set[Callable[[_T], None]] = field(default_factory=frozenset)
    value_converter_on_get: Mapping[str, Sequence[Callable[[_T, Any], Any]]] = field(default_factory=_default_mapping)
    value_converter_on_set: Mapping[str, Sequence[Callable[[_T, Any], Any]]] = field(default_factory=_default_mapping)
    value_validator: Mapping[str, Sequence[Callable[[_T, Any], None]]] = field(default_factory=_default_mapping)
    value_descriptor: Mapping[str, _Descriptor] = field(default_factory=_default_mapping)
    aliases: Mapping[str, str] = field(default_factory=_default_mapping)
    readonly_options: Set[str] = field(default_factory=frozenset)

    if TYPE_CHECKING:
        __hash__: None  # type: ignore[assignment]

    __hash__ = None  # type: ignore[assignment]

    class __ReadOnlyOptionWrapper:
        def __init__(self, default_descriptor: _Descriptor) -> None:
            self.__descriptor_get = default_descriptor.__get__

        def __get__(self, obj: object, objtype: type | None = None, /) -> Any:
            return self.__descriptor_get(obj, objtype)

    def check_option_validity(self, option: str, *, use_alias: bool = False) -> str:
        if use_alias:
            option = self.aliases.get(option, option)
        if option not in self.options:
            raise UnknownOptionError(option)
        return option

    def is_option_valid(self, option: str, *, use_alias: bool = False) -> bool:
        try:
            self.check_option_validity(option, use_alias=use_alias)
        except UnknownOptionError:
            return False
        return True

    def get_value_descriptor(self, option: str, objtype: type) -> _Descriptor:
        descriptor: _Descriptor | None = self.value_descriptor.get(option, None)
        if descriptor is None:
            descriptor = _PrivateAttributeOptionProperty()
            descriptor.__set_name__(objtype, option)
        if option in self.readonly_options:
            descriptor = self.__ReadOnlyOptionWrapper(descriptor)
        return descriptor

    def get_value_setter(self, option: str, objtype: type) -> _MutableDescriptor:
        descriptor = self.get_value_descriptor(option, objtype)
        if not isinstance(descriptor, _MutableDescriptor):
            raise OptionError(option, "Cannot be set")
        return descriptor

    def get_value_deleter(self, option: str, objtype: type) -> _RemovableDescriptor:
        descriptor = self.get_value_descriptor(option, objtype)
        if not isinstance(descriptor, _RemovableDescriptor):
            raise OptionError(option, "Cannot be deleted")
        return descriptor

    def get_options_update_hooks(self, *options: str, exclude_main_updaters: bool) -> Set[Callable[[_T], None]]:
        get_hooks = self.option_update_hooks.get
        updaters = set(chain.from_iterable(get_hooks(option, ()) for option in set(options)))
        if exclude_main_updaters and (main_updater := self.main_object_update_hooks):
            updaters.difference_update(main_updater)
        return updaters

    def get_options_delete_hooks(self, *options: str, exclude_main_updaters: bool) -> Set[Callable[[_T], None]]:
        get_hooks = self.option_delete_hooks.get
        updaters = set(chain.from_iterable(get_hooks(option, ()) for option in set(options)))
        if exclude_main_updaters and (main_updater := self.main_object_update_hooks):
            updaters.difference_update(main_updater)
        return updaters


del _default_mapping

_InitializationRegister: TypeAlias = dict[str, Any]


@final
@dataclass(kw_only=True, frozen=True, eq=False, slots=True)
class _UpdateRegister(Object):
    modified: set[str] = field(default_factory=set)
    deleted: set[str] = field(default_factory=set)

    def has_new_value(self, option: str) -> None:
        self.modified.add(option)
        self.deleted.discard(option)

    def has_been_deleted(self, option: str) -> None:
        self.modified.discard(option)
        self.deleted.add(option)

    def __bool__(self) -> bool:
        return bool(self.modified) or bool(self.deleted)


class Configuration(Object, Generic[_T]):
    __update_stack: ClassVar[dict[object, set[str]]] = dict()
    __init_context: ClassVar[dict[object, _InitializationRegister]] = dict()
    __update_context: ClassVar[dict[object, _UpdateRegister]] = dict()
    __lock_cache: ClassVar[WeakKeyDictionary[object, RLock]] = WeakKeyDictionary()
    __default_lock: ClassVar[RLock] = RLock()

    __slots__ = ("__info", "__obj", "__weakref__")

    class __OptionUpdateContext(NamedTuple):
        first_call: bool
        init_context: _InitializationRegister | None
        register: _UpdateRegister

    def __init__(self, obj: _T | WeakReferenceType[_T], info: ConfigurationInfo[_T]) -> None:
        self.__obj: Callable[[], _T | None]
        if isinstance(obj, WeakReferenceType):
            self.__obj = obj
        else:
            weakref(obj)  # Even if we store a strong reference, the object MUST be weak-referenceable
            self.__obj = lambda obj=obj: obj  # type: ignore[misc]
        self.__info: ConfigurationInfo[_T] = info

    def __repr__(self) -> str:
        option_dict = self.as_dict(sorted_keys=True)
        return f"{type(self).__name__}({', '.join(f'{k}={v!r}' for k, v in option_dict.items())})"

    @overload
    def get(self, option: str) -> Any:
        ...

    @overload
    def get(self, option: str, default: _DT) -> Any | _DT:
        ...

    def get(self, option: str, default: Any = _NO_DEFAULT) -> Any:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_descriptor(option, type(obj))
        try:
            with self.__lazy_lock(obj):
                value: Any = descriptor.__get__(obj, type(obj))
        except AttributeError:
            if default is _NO_DEFAULT:
                raise
            return default
        for value_converter in info.value_converter_on_get.get(option, ()):
            value = value_converter(obj, value)
        return value

    def __getitem__(self, option: str, /) -> Any:
        try:
            return self.get(option)
        except OptionError as exc:
            raise KeyError(option) from exc

    def as_dict(self, *, sorted_keys: bool = False) -> dict[str, Any]:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        with self.__lazy_lock(obj):
            get = self.get
            null = object()
            return {
                opt: value
                for opt in (info.options if not sorted_keys else sorted(info.options))
                if (value := get(opt, null)) is not null
            }

    def set(self, option: str, value: Any) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_setter(option, type(obj))

        for value_validator in info.value_validator.get(option, ()):
            value_validator(obj, value)
        for value_converter in info.value_converter_on_set.get(option, ()):
            value = value_converter(obj, value)

        with self.__updating_option(obj, option, info) as update_context:
            init_context = update_context.init_context
            try:
                actual_value = descriptor.__get__(obj, type(obj))
            except AttributeError:
                pass
            else:
                if init_context is None and (actual_value is value or actual_value == value):
                    return

            descriptor.__set__(obj, value)

            if init_context is not None:
                init_context[option] = value
            else:
                for value_updater in info.option_value_update_hooks.get(option, ()):
                    value_updater(obj, value)

            update_context.register.has_new_value(option)

    def only_set(self, option: str, value: Any) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_setter(option, type(obj))

        for value_validator in info.value_validator.get(option, ()):
            value_validator(obj, value)
        for value_converter in info.value_converter_on_set.get(option, ()):
            value = value_converter(obj, value)

        descriptor.__set__(obj, value)

    def __setitem__(self, option: str, value: Any, /) -> None:
        try:
            self.set(option, value)
        except OptionError as exc:
            raise KeyError(option) from exc

    def delete(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_deleter(option, type(obj))

        with self.__updating_option(obj, option, info) as update_context:
            descriptor.__delete__(obj)

            init_context = update_context.init_context
            if init_context is not None:
                init_context.pop(option, None)

            update_context.register.has_been_deleted(option)

    def only_delete(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_deleter(option, type(obj))
        descriptor.__delete__(obj)

    def __delitem__(self, option: str, /) -> None:
        try:
            return self.delete(option)
        except OptionError as exc:
            raise KeyError(option) from exc

    def __call__(self, **kwargs: Any) -> None:
        obj: _T = self.__self__

        nb_options = len(kwargs)
        if nb_options < 1:
            return

        option: str
        value: Any
        if nb_options == 1:
            option, value = next(iter(kwargs.items()))
            return self.set(option, value)

        # TODO (3.11): Exception groups
        info = self.__info
        options = [info.check_option_validity(option, use_alias=True) for option in kwargs]
        if any(options.count(option) > 1 for option in kwargs):
            raise TypeError("Multiple aliases to the same option given")
        with self.__updating_many_options(obj, *options, info=self.__info):
            set_value = self.set
            for option, value in kwargs.items():
                set_value(option, value)

    def reset(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_setter(option, type(obj))

        with self.__updating_option(obj, option, info) as update_context:
            value: Any = descriptor.__get__(obj, type(obj))

            for value_converter in info.value_converter_on_get.get(option, ()):
                value = value_converter(obj, value)

            for value_validator in info.value_validator.get(option, ()):
                value_validator(obj, value)

            for value_converter in info.value_converter_on_set.get(option, ()):
                value = value_converter(obj, value)

            descriptor.__set__(obj, value)

            register = update_context.init_context
            if register is not None:
                register[option] = value
            else:
                for value_updater in info.option_value_update_hooks.get(option, ()):
                    value_updater(obj, value)

            update_context.register.has_new_value(option)

    def only_reset(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_setter(option, type(obj))

        with self.__lazy_lock(obj):
            value: Any = descriptor.__get__(obj, type(obj))

            for value_converter in info.value_converter_on_get.get(option, ()):
                value = value_converter(obj, value)

            for value_validator in info.value_validator.get(option, ()):
                value_validator(obj, value)

            for value_converter in info.value_converter_on_set.get(option, ()):
                value = value_converter(obj, value)

            descriptor.__set__(obj, value)

    @contextmanager
    def initialization(self) -> Iterator[None]:
        obj: _T = self.__self__

        if obj in Configuration.__init_context:
            yield
            return

        with self.__lazy_lock(obj):
            if obj in Configuration.__update_stack:
                raise InitializationError("Cannot use initialization context while updating an option value")

            def cleanup(obj: _T) -> None:
                Configuration.__init_context.pop(obj, None)
                Configuration.__update_context.pop(obj, None)

            def register_modified_error(register: _InitializationRegister, context: str) -> NoReturn:
                raise InitializationError(
                    f"{', '.join(register)} {'were' if len(register) > 1 else 'was'} modified after {context} in initialization context"
                )

            with ExitStack() as stack:
                stack.callback(cleanup, obj)
                initialization_register: _InitializationRegister = {}
                Configuration.__init_context[obj] = initialization_register
                update_register = _UpdateRegister()
                Configuration.__update_context[obj] = update_register
                yield
                Configuration.__update_context.pop(obj, None)
                after_init_register: _InitializationRegister = {}
                Configuration.__init_context[obj] = after_init_register
                info: ConfigurationInfo[_T] = self.__info
                for option, value in initialization_register.items():
                    for value_updater in info.option_value_update_hooks.get(option, ()):
                        value_updater(obj, value)
                        if after_init_register:
                            register_modified_error(after_init_register, f"value update of {option}")
                for option_deleted in info.get_options_delete_hooks(*update_register.deleted, exclude_main_updaters=True):
                    option_deleted(obj)
                    if after_init_register:
                        register_modified_error(after_init_register, "option delete hook")
                for option_updater in info.get_options_update_hooks(*update_register.modified, exclude_main_updaters=True):
                    option_updater(obj)
                    if after_init_register:
                        register_modified_error(after_init_register, "update")
                for main_updater in info.main_object_update_hooks:
                    main_updater(obj)
                    if after_init_register:
                        register_modified_error(after_init_register, "main update")

    @final
    def has_initialization_context(self) -> bool:
        return self.__self__ in Configuration.__init_context

    def update_option(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        option = info.check_option_validity(option, use_alias=True)
        return self.__update_single_option(obj, option, info)

    def update_options(self, *options: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        valid_option = info.check_option_validity
        return self.__update_options(obj, *set(valid_option(option, use_alias=True) for option in options), info=info)

    def update_object(self) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        return self.__update_options(obj, *info.options, info=info)

    def __reduce_ex__(self, __protocol: SupportsIndex) -> str | tuple[Any, ...]:
        raise TypeError(f"cannot pickle {self.__class__.__qualname__!r} object")

    def __reduce__(self) -> str | tuple[Any, ...]:
        raise TypeError(f"cannot pickle {self.__class__.__qualname__!r} object")

    @property
    @final
    def info(self) -> ConfigurationInfo[_T]:
        return self.__info

    @property
    @final
    def __self__(self) -> _T:
        obj: _T | None = self.__obj()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        return obj

    @classmethod
    def __update_options(cls, obj: object, *options: str, info: ConfigurationInfo[Any]) -> None:
        nb_options = len(options)
        if nb_options < 1:
            return
        if nb_options == 1:
            return cls.__update_single_option(obj, options[0], info)

        objtype: type = type(obj)
        with cls.__updating_many_options(obj, *options, info=info) as update_contexts:
            for option, context in update_contexts.items():
                if not context.first_call:
                    continue
                descriptor = info.get_value_descriptor(option, objtype)
                try:
                    value: Any = descriptor.__get__(obj, type(obj))
                except AttributeError:
                    context.register.has_been_deleted(option)
                else:
                    for value_updater in info.option_value_update_hooks.get(option, ()):
                        value_updater(obj, value)
                    context.register.has_new_value(option)

    @classmethod
    def __update_single_option(cls, obj: object, option: str, info: ConfigurationInfo[Any]) -> None:
        descriptor = info.get_value_descriptor(option, type(obj))

        with cls.__updating_option(obj, option, info) as update_context:
            if not update_context.first_call:
                return
            try:
                value: Any = descriptor.__get__(obj, type(obj))
            except AttributeError:
                update_context.register.has_been_deleted(option)
            else:
                for value_updater in info.option_value_update_hooks.get(option, ()):
                    value_updater(obj, value)
                update_context.register.has_new_value(option)

    @classmethod
    @contextmanager
    def __updating_option(cls, obj: object, option: str, info: ConfigurationInfo[Any]) -> Iterator[__OptionUpdateContext]:
        UpdateContext = cls.__OptionUpdateContext

        with cls.__lazy_lock(obj):
            if not info.main_object_update_hooks and not info.option_update_hooks:
                # first_call=False to avoid useless actions
                yield UpdateContext(first_call=False, init_context=None, register=_UpdateRegister())
                return

            register = cls.__init_context.get(obj, None)
            if register is not None:
                update_register = cls.__update_context.get(obj, _UpdateRegister())
                yield UpdateContext(first_call=False, init_context=register, register=update_register)
                return

            update_register = cls.__update_context.setdefault(obj, _UpdateRegister())
            update_stack: set[str] = cls.__update_stack.setdefault(obj, set())
            if option in update_stack:
                yield UpdateContext(first_call=False, init_context=None, register=update_register)
                return

            def cleanup(obj: object) -> None:
                update_stack.discard(option)
                if not update_stack:
                    cls.__update_stack.pop(obj, None)

            update_stack.add(option)
            with ExitStack() as stack:
                stack.callback(cleanup, obj)
                yield UpdateContext(first_call=True, init_context=None, register=update_register)
            if update_stack:
                return
            update_register = cls.__update_context.pop(obj, update_register)
            if not update_register:
                return
            for option_deleted in info.get_options_delete_hooks(*update_register.deleted, exclude_main_updaters=True):
                option_deleted(obj)
            for option_updater in info.get_options_update_hooks(*update_register.modified, exclude_main_updaters=True):
                option_updater(obj)
            for main_updater in info.main_object_update_hooks:
                main_updater(obj)

    @classmethod
    @contextmanager
    def __updating_many_options(
        cls,
        obj: object,
        *options: str,
        info: ConfigurationInfo[Any],
    ) -> Iterator[dict[str, __OptionUpdateContext]]:
        if len(options) < 1:  # No need to take the lock and init something
            yield {}
            return

        with cls.__lazy_lock(obj), ExitStack() as stack:
            yield {option: stack.enter_context(cls.__updating_option(obj, option, info)) for option in options}

    @classmethod
    def __lazy_lock(cls, obj: object) -> RLock:
        lock_cache = cls.__lock_cache
        lock: RLock = lock_cache.get(obj, _MISSING)
        if lock is _MISSING:
            with cls.__default_lock:
                lock = lock_cache.get(obj, _MISSING)
                if lock is _MISSING:
                    lock_cache[obj] = lock = RLock()
        return lock


def _no_type_check_cache(func: _FuncVar) -> _FuncVar:
    return cache(func)  # type: ignore[return-value]


def _make_function_wrapper(func: Any, *, use_override: bool = True, no_object: bool = False) -> Callable[..., Any]:
    wrapper: _FunctionWrapperBuilder | _WrappedFunctionWrapper
    if isinstance(func, _WrappedFunctionWrapper):
        wrapper = func
    else:
        wrapper = _FunctionWrapperBuilder(func, use_override=use_override, no_object=no_object)
    cached_func = wrapper.get_wrapper()
    if cached_func is not None:
        return cached_func

    if wrapper.traceback is None:
        frame = inspect.currentframe()
        try:
            if frame is not None:
                while (tb := inspect.getframeinfo(frame, context=0)).filename == __file__ and (frame := frame.f_back) is not None:
                    continue
                wrapper.traceback = tb
        finally:
            del frame

    return wrapper


@final
class _FunctionWrapperBuilder:
    __slots__ = ("info", "cache", "traceback")

    class Info(NamedTuple):
        func: Any
        use_override: bool
        no_object: bool

    info: Info
    cache: dict[Any, Callable[..., Any]]
    traceback: inspect.Traceback | None

    __instance_cache: dict[Info, _FunctionWrapperBuilder] = dict()

    def __new__(cls, func: Any, use_override: bool, no_object: bool) -> _FunctionWrapperBuilder:
        if isinstance(func, cls):
            if func.info.use_override == use_override and func.info.no_object == no_object:
                return func
            func = func.info.func
        info = cls.Info(func=func, use_override=use_override, no_object=no_object)
        try:
            self = cls.__instance_cache[info]
        except KeyError:
            self = object.__new__(cls)
            self.info = info
            self.cache = {}
            self.traceback = None
            cls.__instance_cache[info] = self
        return self

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError("Dummy function")

    @staticmethod
    def is_wrapper(func: Callable[..., Any]) -> bool:
        return True if getattr(func, "__boundconfiguration_wrapper__", False) else False

    @staticmethod
    def mark_wrapper(wrapper: Callable[..., Any]) -> None:
        setattr(wrapper, "__boundconfiguration_wrapper__", True)

    def get_wrapper(self) -> Callable[..., Any] | None:
        func: Any = self.info.func
        if self.is_wrapper(func):
            return cast(Callable[..., Any], func)
        return self.cache.get(func)

    def build_wrapper(self, cls: type) -> Callable[..., Any]:
        info = self.info
        func: Any = info.func
        if self.is_wrapper(func):
            return cast(Callable[..., Any], func)
        if func in self.cache:
            return self.cache[func]

        no_object = info.no_object
        use_override = info.use_override

        if no_object:
            use_override = False

        if info != self.Info(func, use_override=use_override, no_object=no_object):
            # Ask the right builder to compute the wrapper
            builder = self.__class__(func, use_override=use_override, no_object=no_object)
            computed_wrapper = builder.build_wrapper(cls)
            self.cache[func] = computed_wrapper  # Save in our cache for further calls
            return computed_wrapper

        func_name: str = ""
        if use_override:
            func_name = next((attr_name for attr_name, attr_obj in _all_members(cls).items() if attr_obj is func), func_name)
            if not func_name:
                msg = f"Couldn't find {func!r} in {cls.__qualname__} members"
                if self.traceback:
                    msg = f"{self.traceback.filename}:{self.traceback.lineno}: {msg}"
                raise AttributeError(msg)

        if no_object:
            assert callable(func)

            def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

        elif not hasattr(func, "__get__"):

            assert callable(func)

            if func_name:

                def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                    _func: Callable[..., Any] = getattr(self, func_name, func)
                    return _func(self, *args, **kwargs)

            else:

                def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                    return func(self, *args, **kwargs)

        else:
            func_get_descriptor: Callable[[Any, type], Callable[..., Any]] = getattr(func, "__get__")

            assert callable(func_get_descriptor)

            if func_name:

                def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                    _func: Callable[..., Any]
                    try:
                        _func = getattr(self, func_name)
                    except AttributeError:
                        _func = func_get_descriptor(self, type(self))
                    return _func(*args, **kwargs)

            else:

                def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                    _func: Callable[..., Any] = func_get_descriptor(self, type(self))
                    return _func(*args, **kwargs)

        try:
            wrapper = update_wrapper(wrapper=wrapper, wrapped=func)
        except (AttributeError, TypeError):
            pass

        self.mark_wrapper(wrapper)
        self.cache[func] = wrapper
        return wrapper


@final
class _WrappedFunctionWrapper:
    __slots__ = ("wrapper", "decorator", "cache")

    wrapper: _FunctionWrapperBuilder
    decorator: Any
    cache: dict[Any, Callable[..., Any]]

    __wrapper_cache: dict[Hashable, dict[Any, Callable[..., Any]]] = {}

    def __new__(
        cls,
        func: Any,
        unique_key: Hashable,
        wrapper_decorator: Callable[[Callable[..., Any]], Callable[..., Any]],
        use_override: bool,
        no_object: bool,
    ) -> _WrappedFunctionWrapper:
        self = object.__new__(cls)

        self.wrapper = _FunctionWrapperBuilder(func, use_override, no_object)
        self.decorator = wrapper_decorator
        self.cache = self.__wrapper_cache.setdefault(unique_key, {})

        return self

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError("Dummy function")

    def get_wrapper(self) -> Callable[..., Any] | None:
        func: Any = self.wrapper.info.func
        if _FunctionWrapperBuilder.is_wrapper(func):
            return cast(Callable[..., Any], func)
        return self.cache.get(func)

    def build_wrapper(self, cls: type) -> Callable[..., Any]:
        func: Any = self.wrapper.info.func
        wrapper_cache = self.cache
        if func in wrapper_cache:
            return wrapper_cache[func]

        decorator: Callable[[Callable[..., Any]], Callable[..., Any]] = self.decorator

        wrapper = self.wrapper.build_wrapper(cls)
        wrapper = decorator(wrapper)

        try:
            wrapper = update_wrapper(wrapper=wrapper, wrapped=func)
        except (AttributeError, TypeError):
            pass

        _FunctionWrapperBuilder.mark_wrapper(wrapper)
        wrapper_cache[func] = wrapper
        return wrapper

    @property
    def traceback(self) -> inspect.Traceback | None:
        return self.wrapper.traceback

    @traceback.setter
    def traceback(self, tb: inspect.Traceback | None) -> None:
        self.wrapper.traceback = tb


@_no_type_check_cache
def _make_type_checker(_type: type | tuple[type, ...], accept_none: bool, /) -> Callable[[Any], None]:
    if accept_none:
        if isinstance(_type, type):
            _type = (_type,)
        if type(None) not in _type:
            _type += (type(None),)

    def type_checker(val: Any, /, *, _type: Any = _type) -> None:
        if isinstance(val, _type):
            return
        expected: str
        if isinstance(_type, type):
            expected = f"a {_type.__qualname__} object type"
        else:
            expected = f"one of those object types: ({', '.join(t.__qualname__ for t in _type)})"
        val_type: type = type(val)
        gotten: str = repr(f"{val_type.__module__}.{val_type.__qualname__}" if val_type.__module__ != object.__module__ else val)
        raise TypeError(f"Invalid value type. expected {expected}, got {gotten}")

    return type_checker


@_no_type_check_cache
def _make_value_converter(_type: type, accept_none: bool, /) -> Callable[[Any], Any]:
    assert isinstance(_type, type)

    if not accept_none:
        return lambda val, /, *, _type=_type: _type(val)  # type: ignore[misc]

    def value_converter(val: Any, /, *, _type: Callable[[Any], Any] = _type) -> Any:
        if val is None:
            return None
        return _type(val)

    return value_converter


@_no_type_check_cache
def _make_enum_converter(enum: type[Enum], return_value: bool, accept_none: bool, /) -> Callable[[Any], Any]:
    assert issubclass(enum, Enum)

    if not return_value:

        if not accept_none:
            return lambda val, /, *, enum=enum: enum(val)  # type: ignore[misc]

        def value_converter(val: Any, /, *, enum: type[Enum] = enum) -> Any:
            if val is None:
                return None
            return enum(val)

    else:

        if not accept_none:
            return lambda val, /, *, enum=enum: enum(val).value  # type: ignore[misc]

        def value_converter(val: Any, /, *, enum: type[Enum] = enum) -> Any:
            if val is None:
                return None
            return enum(val).value

    return value_converter


def _all_members(cls: type) -> MutableMapping[str, Any]:
    return ChainMap(*map(vars, inspect.getmro(cls)))


def _retrieve_configuration(cls: type) -> ConfigurationTemplate:
    config: ConfigurationTemplate | None = next(
        (obj for obj in _all_members(cls).values() if isinstance(obj, ConfigurationTemplate)), None
    )
    if config is None:
        raise TypeError(f"{cls.__name__} does not have a {ConfigurationTemplate.__name__} object")
    return config


@runtime_checkable
class _Descriptor(Protocol):
    def __get__(self, __obj: object, __objtype: type | None, /) -> Any:
        pass


@runtime_checkable
class _MutableDescriptor(_Descriptor, Protocol):
    def __set__(self, __obj: object, __value: Any, /) -> None:
        pass


@runtime_checkable
class _RemovableDescriptor(_Descriptor, Protocol):
    def __delete__(self, __obj: object, /) -> None:
        pass


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


@final
class _ConfigInfoTemplate:
    def __init__(self, known_options: Sequence[str], parents: Sequence[_ConfigInfoTemplate]) -> None:
        self.parents: tuple[_ConfigInfoTemplate, ...] = tuple(parents)
        self.options: frozenset[str] = frozenset(known_options)
        self.main_update_hooks: set[Callable[[object], None]] = set()
        self.option_update_hooks: dict[str, set[Callable[[object], None]]] = dict()
        self.option_delete_hooks: dict[str, set[Callable[[object], None]]] = dict()
        self.option_value_update_hooks: dict[str, set[Callable[[object, Any], None]]] = dict()
        self.value_descriptor: dict[str, _Descriptor] = dict()
        self.value_converter_on_get: dict[str, list[Callable[[object, Any], Any]]] = dict()
        self.value_converter_on_set: dict[str, list[Callable[[object, Any], Any]]] = dict()
        self.value_validator: dict[str, list[Callable[[object, Any], None]]] = dict()
        self.aliases: dict[str, str] = dict()

        merge_dict = self.__merge_dict
        merge_updater_dict = self.__merge_updater_dict
        for p in parents:
            self.options |= p.options
            self.main_update_hooks |= p.main_update_hooks
            merge_updater_dict(self.option_update_hooks, p.option_update_hooks)
            merge_updater_dict(self.option_delete_hooks, p.option_delete_hooks)
            merge_updater_dict(self.option_value_update_hooks, p.option_value_update_hooks)
            merge_dict(self.value_descriptor, p.value_descriptor, on_conflict="raise", setting="descriptor")
            merge_dict(
                self.value_converter_on_get,
                p.value_converter_on_get,
                on_conflict="raise",
                setting="value_converter_on_get",
                copy=list.copy,
            )
            merge_dict(
                self.value_converter_on_set,
                p.value_converter_on_set,
                on_conflict="raise",
                setting="value_converter_on_set",
                copy=list.copy,
            )
            merge_dict(
                self.value_validator,
                p.value_validator,
                on_conflict="raise",
                setting="value_validator",
                copy=list.copy,
            )
            merge_dict(self.aliases, p.aliases, on_conflict="raise", setting="aliases")

        self.parent_descriptors: frozenset[_Descriptor] = frozenset(self.value_descriptor.values())

    @staticmethod
    def __merge_dict(
        d1: dict[_KT, _VT],
        d2: dict[_KT, _VT],
        /,
        *,
        on_conflict: L["override", "raise", "skip"] | Callable[[_KT, _VT, _VT], _VT],
        setting: str,
        copy: Callable[[_VT], _VT] | None = None,
    ) -> None:
        for key, value in d2.items():
            if key in d1:
                if d1[key] == value or on_conflict == "skip":
                    continue
                if on_conflict == "raise":
                    raise ConfigurationError(f"Conflict of setting {setting!r} for {key!r} key")
                if callable(on_conflict):
                    value = on_conflict(key, d1[key], value)
            if copy is not None:
                value = copy(value)
            d1[key] = value

    @classmethod
    def __merge_updater_dict(
        cls,
        d1: dict[str, set[_FuncVar]],
        d2: dict[str, set[_FuncVar]],
        /,
    ) -> None:
        for key, s2 in d2.items():
            s1 = d1.setdefault(key, set())
            s1.update(s2)

    def build(self, owner: type) -> ConfigurationInfo[Any]:
        self.__intern_build_all_wrappers(owner)
        self.__set_default_value_descriptors(owner)

        return ConfigurationInfo(
            options=frozenset(self.options),
            option_value_update_hooks=self.__build_option_value_update_hooks_dict(),
            option_delete_hooks=self.__build_option_delete_hooks_dict(),
            option_update_hooks=self.__build_option_update_hooks_dict(),
            main_object_update_hooks=frozenset(self.main_update_hooks),
            value_converter_on_get=self.__build_value_converter_dict(on="get"),
            value_converter_on_set=self.__build_value_converter_dict(on="set"),
            value_validator=self.__build_value_validator_dict(),
            value_descriptor=self.__build_value_descriptor_dict(owner),
            aliases=MappingProxyType(self.aliases.copy()),
            readonly_options=self.__build_readonly_options_set(),
        )

    def __intern_build_all_wrappers(self, owner: type) -> None:
        def build_wrapper_if_needed(func: _FuncVar) -> _FuncVar:
            if isinstance(func, (_FunctionWrapperBuilder, _WrappedFunctionWrapper)):
                return func.build_wrapper(owner)  # type: ignore[return-value]
            return func

        def build_wrapper_within_descriptor(descriptor: _Descriptor) -> _Descriptor:
            if isinstance(descriptor, _ConfigProperty):
                if descriptor.fget is not None:
                    descriptor = descriptor.getter(build_wrapper_if_needed(descriptor.fget))
                if descriptor.fset is not None:
                    descriptor = descriptor.setter(build_wrapper_if_needed(descriptor.fset))
                if descriptor.fdel is not None:
                    descriptor = descriptor.deleter(build_wrapper_if_needed(descriptor.fdel))
            elif isinstance(descriptor, _ReadOnlyOptionBuildPayload):
                if (underlying_descriptor := descriptor.get_descriptor()) is not None:
                    descriptor.set_new_descriptor(build_wrapper_within_descriptor(underlying_descriptor))
            return descriptor

        self.main_update_hooks = set(build_wrapper_if_needed(func) for func in self.main_update_hooks)
        self.option_update_hooks = {
            option: set(build_wrapper_if_needed(func) for func in func_set)
            for option, func_set in self.option_update_hooks.items()
        }
        self.option_delete_hooks = {
            option: set(build_wrapper_if_needed(func) for func in func_set)
            for option, func_set in self.option_delete_hooks.items()
        }
        self.option_value_update_hooks = {
            option: set(build_wrapper_if_needed(func) for func in func_set)
            for option, func_set in self.option_value_update_hooks.items()
        }
        for callback_list in chain(
            self.value_converter_on_get.values(),
            self.value_converter_on_set.values(),
            self.value_validator.values(),
        ):
            callback_list[:] = [build_wrapper_if_needed(func) for func in callback_list]
        for option, descriptor in tuple(self.value_descriptor.items()):
            self.value_descriptor[option] = build_wrapper_within_descriptor(descriptor)

    def __set_default_value_descriptors(self, owner: type) -> None:
        for option in list(filter(lambda option: option not in self.value_descriptor, self.options)):
            self.value_descriptor[option] = descriptor = _PrivateAttributeOptionProperty()
            descriptor.__set_name__(owner, option)

    def __build_option_value_update_hooks_dict(self) -> MappingProxyType[str, frozenset[Callable[[object, Any], None]]]:
        return MappingProxyType(
            {option: frozenset(hooks) for option, hooks in self.option_value_update_hooks.items() if len(hooks) > 0}
        )

    def __build_option_update_hooks_dict(self) -> MappingProxyType[str, frozenset[Callable[[object], None]]]:
        return MappingProxyType(
            {
                option: frozenset(filtered_hooks)
                for option, hooks in self.option_update_hooks.items()
                if len((filtered_hooks := hooks.difference(self.main_update_hooks))) > 0
            }
        )

    def __build_option_delete_hooks_dict(self) -> MappingProxyType[str, frozenset[Callable[[object], None]]]:
        return MappingProxyType(
            {
                option: frozenset(filtered_hooks)
                for option, hooks in self.option_delete_hooks.items()
                if len((filtered_hooks := hooks.difference(self.main_update_hooks))) > 0
            }
        )

    def __build_value_converter_dict(
        self, *, on: L["get", "set"]
    ) -> MappingProxyType[str, tuple[Callable[[object, Any], Any], ...]]:
        value_converter: dict[str, list[Callable[[object, Any], Any]]] = getattr(self, f"value_converter_on_{on}")
        return MappingProxyType(
            {option: tuple(converter_list) for option, converter_list in value_converter.items() if len(converter_list) > 0}
        )

    def __build_value_validator_dict(self) -> MappingProxyType[str, tuple[Callable[[object, Any], None], ...]]:
        return MappingProxyType(
            {option: tuple(validator_list) for option, validator_list in self.value_validator.items() if len(validator_list) > 0}
        )

    def __build_value_descriptor_dict(self, owner: type) -> MappingProxyType[str, _Descriptor]:
        value_descriptors: dict[str, _Descriptor] = {}

        for option, descriptor in self.value_descriptor.items():
            if isinstance(descriptor, _ReadOnlyOptionBuildPayload):
                underlying_descriptor = descriptor.get_descriptor()
                if underlying_descriptor is not None:
                    descriptor = underlying_descriptor
                else:
                    descriptor = _PrivateAttributeOptionProperty()
                    descriptor.__set_name__(owner, option)
            value_descriptors[option] = descriptor

        return MappingProxyType(value_descriptors)

    def __build_readonly_options_set(self) -> frozenset[str]:
        return frozenset(
            option for option, descriptor in self.value_descriptor.items() if isinstance(descriptor, _ReadOnlyOptionBuildPayload)
        )


class _ConfigInitializer:

    __slots__ = ("__func__", "__config_name", "__dict__")

    def __init__(self, func: Callable[..., Any]) -> None:
        if not hasattr(func, "__get__"):
            raise TypeError("Built-in functions cannot be used")
        self.__func__: Callable[..., Any] = func
        self.__config_name: str = ""

    def __set_name__(self, owner: type, name: str, /) -> None:
        config: ConfigurationTemplate = _retrieve_configuration(owner)
        if config.name is None:
            raise TypeError("@initializer must be declared after the ConfigurationTemplate object")
        self.__config_name = config.name

    @property
    def __call__(self) -> Callable[..., Any]:
        return self.__make_initializer()

    def __getattr__(self, name: str, /) -> Any:
        func: Any = self.__func__
        return getattr(func, name)

    def __get__(self, obj: object, objtype: type | None = None, /) -> Callable[..., Any]:
        config_initializer = self.__make_initializer()
        method_func: Callable[..., Any] = getattr(config_initializer, "__get__")(obj, objtype)
        return method_func

    def __make_initializer(self) -> Callable[..., Any]:
        init_func: Callable[..., Any] = self.__func__
        func_get: Callable[[object, type | None], Callable[..., Any]] = getattr(init_func, "__get__")
        config_name: str = self.__config_name

        @wraps(init_func)
        def config_initializer(self: object, /, *args: Any, **kwargs: Any) -> Any:
            config: Configuration[object] = getattr(self, config_name)
            method: Callable[..., Any] = func_get(self, type(self))
            with config.initialization():
                return method(*args, **kwargs)

        return config_initializer

    @property
    def __wrapped__(self) -> Callable[..., Any]:
        return self.__func__


class _ConfigProperty(property):
    pass


class _PrivateAttributeOptionProperty:
    def __set_name__(self, owner: type, name: str, /) -> None:
        self.__attribute: str = _private_attribute(owner, name)

    def __get__(self, obj: object, objtype: type | None = None, /) -> Any:
        if obj is None:
            return self
        return getattr(obj, self.__attribute)

    def __set__(self, obj: object, value: Any, /) -> None:
        return setattr(obj, self.__attribute, value)

    def __delete__(self, obj: object, /) -> None:
        return delattr(obj, self.__attribute)


class _ReadOnlyOptionBuildPayload:
    def __init__(self, default_descriptor: _Descriptor | None) -> None:
        self.__descriptor: Callable[[], _Descriptor | None]
        self.set_new_descriptor(default_descriptor)

    def __set_name__(self, owner: type, name: str, /) -> None:
        descriptor: Any = self.__descriptor()
        if hasattr(descriptor, "__set_name__"):
            getattr(descriptor, "__set_name__")(owner, name)

    def __get__(self, obj: object, objtype: type | None = None, /) -> Any:
        raise TypeError("Cannot be used at runtime")

    def get_descriptor(self) -> _Descriptor | None:
        return self.__descriptor()

    def set_new_descriptor(self, descriptor: _Descriptor | None) -> None:
        self.__descriptor = lambda: descriptor
