# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Configuration module"""

from __future__ import annotations

__all__ = [
    "ConfigError",
    "Configuration",
    "ConfigurationTemplate",
    "EmptyOptionNameError",
    "InitializationError",
    "InvalidAliasError",
    "OptionAttribute",
    "OptionError",
    "UnknownOptionError",
    "UnregisteredOptionError",
    "initializer",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import inspect
import re
from collections import ChainMap
from contextlib import ExitStack, contextmanager, nullcontext, suppress
from copy import copy
from dataclasses import KW_ONLY, dataclass, field
from enum import Enum
from functools import cache, update_wrapper, wraps
from itertools import chain
from threading import RLock
from types import BuiltinFunctionType, BuiltinMethodType, MappingProxyType
from typing import (
    TYPE_CHECKING,
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
_ValueValidatorVar = TypeVar("_ValueValidatorVar", bound=Callable[[Any, Any], None])
_StaticValueValidatorVar = TypeVar("_StaticValueValidatorVar", bound=Callable[[Any], None])
_ValueConverterVar = TypeVar("_ValueConverterVar", bound=Callable[[Any, Any], Any])
_StaticValueConverterVar = TypeVar("_StaticValueConverterVar", bound=Callable[[Any], Any])
_T = TypeVar("_T")
_DT = TypeVar("_DT")


class ConfigError(Exception):
    pass


class OptionError(ConfigError):
    def __init__(self, name: str, message: str) -> None:
        if name:
            message = f"{name!r}: {message}"
        super().__init__(message)
        self.name: str = name


class UnknownOptionError(OptionError):
    def __init__(self, name: str, message: str = "Unknown config option") -> None:
        super().__init__(name, message)


class UnregisteredOptionError(OptionError):
    def __init__(self, name: str) -> None:
        super().__init__(name, "Unregistered option")


class EmptyOptionNameError(UnknownOptionError):
    def __init__(self) -> None:
        super().__init__("", "Empty string option given")


class InvalidAliasError(OptionError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(name, message)


class InitializationError(ConfigError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def initializer(func: _FuncVar) -> _FuncVar:
    return _ConfigInitializer(func)  # type: ignore[return-value]


_ALLOWED_OPTIONS_PATTERN = re.compile(r"(?!__)(?:[a-zA-Z]\w*|_\w+)(?<!__)")
_MISSING: Any = object()
_NO_DEFAULT: Any = object()


class ConfigurationTemplate(Object):
    __slots__ = (
        "__template",
        "__no_parent_ownership",
        "__bound_class",
        "__attr_name",
        "__lock",
        "__info",
    )

    def __init__(
        self,
        *known_options: str,
        autocopy: bool | None = None,
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
        else:
            parent = list(dict.fromkeys(parent))

        self.__template: _ConfigInfoTemplate = _ConfigInfoTemplate(known_options, autocopy, list(p.__template for p in parent))
        self.__no_parent_ownership: set[str] = set()
        self.__bound_class: type | None = None
        self.__attr_name: str | None = None
        self.__lock = RLock()
        self.__info: ConfigurationInfo | None = None

    def __repr__(self) -> str:
        return f"{type(self).__name__}({{{', '.join(repr(s) for s in sorted(self.known_options()))}}})"

    def __set_name__(self, owner: type, name: str, /) -> None:
        if self.__bound_class is not None:
            raise TypeError(f"This configuration object is bound to a class: {self.__bound_class.__name__!r}")
        if getattr(owner, name) is not self:
            raise AttributeError("The attribute name does not correspond")
        template: _ConfigInfoTemplate = self.__template
        if name in template.options:
            raise OptionError(name, "ConfigurationTemplate attribute name is an option")
        self.__bound_class = owner
        self.__attr_name = name
        attribute_class_owner: dict[str, type] = template.attribute_class_owner
        no_parent_ownership: set[str] = self.__no_parent_ownership
        for option in template.options:
            if option in no_parent_ownership:
                attribute_class_owner[option] = owner
            else:
                attribute_class_owner.setdefault(option, owner)
            descriptor: _Descriptor | None = template.value_descriptors.get(option)
            if descriptor not in template.parent_descriptors and hasattr(descriptor, "__set_name__"):
                getattr(descriptor, "__set_name__")(attribute_class_owner[option], option)
        former_config: ConfigurationTemplate | None = _register_configuration(owner, self)
        for obj in _all_members(owner).values():
            if isinstance(obj, OptionAttribute):
                with suppress(AttributeError):
                    self.check_option_validity(obj.name, use_alias=True)
            elif isinstance(obj, ConfigurationTemplate) and obj is not self:
                _register_configuration(owner, former_config)
                raise TypeError(f"A class can't have several {ConfigurationTemplate.__name__!r} objects")
        self.__info = template.build(owner)

    @overload
    def __get__(self, obj: None, objtype: type, /) -> ConfigurationTemplate:
        ...

    @overload
    def __get__(self, obj: _T, objtype: type | None = None, /) -> Configuration[_T]:
        ...

    # TODO: Optimize this BIG block function
    def __get__(self, obj: Any, objtype: type | None = None, /) -> ConfigurationTemplate | Configuration[Any]:
        if obj is None:
            if objtype is None:
                raise TypeError("__get__(None, None) is invalid")
            return self
        attr_name = self.__attr_name
        info = self.__info
        bound_class = self.__bound_class
        if not attr_name or info is None or bound_class is None:
            raise TypeError("Cannot use ConfigurationTemplate instance without calling __set_name__ on it.")
        try:
            objref: WeakReferenceType[Any] = weakref(obj)
        except TypeError:
            return Configuration(obj, info)
        if objtype is None:
            objtype = type(obj)
        if getattr(objtype, attr_name, None) is not self:
            return Configuration(objref, info)
        try:
            obj_cache = obj.__dict__
        except AttributeError:
            return Configuration(objref, info)
        bound_config: Configuration[Any] = obj_cache.get(attr_name, _MISSING)
        if bound_config is not _MISSING:
            try:
                if bound_config.__self__ is not obj:  # __self__ will raise ReferenceError if the underlying object is dead
                    raise ReferenceError
            except ReferenceError:
                bound_config = Configuration(objref, info)
                with self.__lock, suppress(Exception):
                    obj_cache[attr_name] = bound_config
        else:
            with self.__lock:
                bound_config = obj_cache.get(attr_name, _MISSING)
                if bound_config is _MISSING:
                    bound_config = Configuration(objref, info)
                    with suppress(Exception):
                        obj_cache[attr_name] = bound_config
        return bound_config

    # TODO: __set__ and __delete__ exist only to force the call of __get__
    # There is some issues with cache and copy.copy ...
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
            if not option:
                raise EmptyOptionNameError()
            raise UnknownOptionError(option)
        return option

    def is_option_valid(self, option: str, *, use_alias: bool = False) -> bool:
        try:
            self.check_option_validity(option, use_alias=use_alias)
        except OptionError:
            return False
        return True

    @overload
    def set_autocopy(self, autocopy: bool, /) -> None:
        ...

    @overload
    def set_autocopy(self, option: str, /, *, copy_on_get: bool | None) -> None:
        ...

    @overload
    def set_autocopy(self, option: str, /, *, copy_on_set: bool | None) -> None:
        ...

    @overload
    def set_autocopy(self, option: str, /, *, copy_on_get: bool | None, copy_on_set: bool | None) -> None:
        ...

    def set_autocopy(self, arg1: bool | str, /, **kwargs: bool | None) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        if isinstance(arg1, bool) and not kwargs:
            template.autocopy = arg1
        elif isinstance(arg1, str) and ("copy_on_get" in kwargs or "copy_on_set" in kwargs):
            self.check_option_validity(arg1)
            if "copy_on_get" in kwargs:
                copy_on_get: bool | None = kwargs["copy_on_get"]
                if copy_on_get is None:
                    template.value_autocopy_get.pop(arg1, None)
                else:
                    template.value_autocopy_get[arg1] = bool(copy_on_get)
            if "copy_on_set" in kwargs:
                copy_on_set: bool | None = kwargs["copy_on_set"]
                if copy_on_set is None:
                    template.value_autocopy_set.pop(arg1, None)
                else:
                    template.value_autocopy_set[arg1] = bool(copy_on_set)
        else:
            raise TypeError("Invalid argument")

    def remove_parent_ownership(self, option: str) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        self.__no_parent_ownership.add(option)

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
        actual_descriptor: _Descriptor | None = template.value_descriptors.get(option)
        if not isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            if actual_descriptor is not None and not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            actual_property: _ConfigProperty | None = actual_descriptor
            if (
                actual_property is not None
                and readonly
                and (actual_property.fset is not None or actual_property.fdel is not None)
            ):
                raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")

            def decorator(func: _GetterVar, /) -> _GetterVar:
                wrapper = _make_function_wrapper(func, check_override=bool(use_override))
                new_config_property: property
                if actual_property is None:
                    new_config_property = _ConfigProperty(wrapper)
                else:
                    new_config_property = actual_property.getter(wrapper)
                if readonly:
                    template.value_descriptors[option] = _ReadOnlyOptionBuildPayload(new_config_property)
                else:
                    template.value_descriptors[option] = new_config_property
                return func

        else:
            readonly_descriptor: _ReadOnlyOptionBuildPayload = actual_descriptor
            actual_descriptor = readonly_descriptor.get_descriptor()
            if not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            config_property: _ConfigProperty = actual_descriptor

            def decorator(func: _GetterVar, /) -> _GetterVar:
                wrapper = _make_function_wrapper(func, check_override=bool(use_override))
                readonly_descriptor.set_new_descriptor(config_property.getter(wrapper))
                return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def getter_key(
        self, option: str, /, *, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_key(self, option: str, func: _KeyGetterVar, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    @overload
    def getter_key(
        self, option: str, func: _KeyGetterVar, /, *, use_key: Hashable, use_override: bool = True, readonly: bool = False
    ) -> None:
        ...

    def getter_key(
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

        def wrapper_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyGetterVar, /) -> _KeyGetterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, check_override=bool(use_override), no_object=False)
            self.getter(option, wrapper, readonly=readonly)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def getter_key_from_map(
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
    def getter_key_from_map(
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

    def getter_key_from_map(
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
        return self.getter_key(option, func, use_key=use_key, use_override=use_override, readonly=readonly)

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
        actual_descriptor: _Descriptor | None = template.value_descriptors.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing setter for this option which has no getter")
        if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            raise OptionError(option, "Read-only option")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _SetterVar, /) -> _SetterVar:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            template.value_descriptors[option] = actual_property.setter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_key(self, option: str, func: _KeySetterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def setter_key(self, option: str, func: _KeySetterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def setter_key(
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

        def wrapper_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return lambda self, value: func(self, use_key, value)

        def decorator(func: _KeySetterVar, /) -> _KeySetterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, check_override=bool(use_override), no_object=False)
            self.setter(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter_key_from_map(
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
    def setter_key_from_map(
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

    def setter_key_from_map(
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
        return self.setter_key(option, func, use_key=use_key, use_override=use_override)

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
        actual_descriptor: _Descriptor | None = template.value_descriptors.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing deleter for this option which has no getter")
        if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
            raise OptionError(option, "Read-only option")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _DeleterVar, /) -> _DeleterVar:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            template.value_descriptors[option] = actual_property.deleter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_key(self, option: str, func: _KeyDeleterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def deleter_key(self, option: str, func: _KeyDeleterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def deleter_key(
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

        def wrapper_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyDeleterVar, /) -> _KeyDeleterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, check_override=bool(use_override), no_object=False)
            self.deleter(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter_key_from_map(
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
    def deleter_key_from_map(
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

    def deleter_key_from_map(
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
        return self.deleter_key(option, func, use_key=use_key, use_override=use_override)

    def use_descriptor(self, option: str, descriptor: _Descriptor) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: _Descriptor
        if (
            option in template.value_descriptors
            and (actual_descriptor := template.value_descriptors[option]) not in template.parent_descriptors
        ):
            if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
                underlying_descriptor = actual_descriptor.get_descriptor()
                if underlying_descriptor is None:
                    raise OptionError(option, "Already uses custom getter register with getter() method")
                actual_descriptor = underlying_descriptor
            if isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, "Already uses custom getter register with getter() method")
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        template.value_descriptors[option] = descriptor

    def reset_getter_setter_deleter(self, option: str) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        if option in template.value_descriptors and template.value_descriptors[option] not in template.parent_descriptors:
            raise OptionError(option, "reset() accepted only when a descriptor is inherited from parent")
        template.value_descriptors.pop(option, None)

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
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if wrapper in template.main_updater:
                raise ConfigError("Function already registered")
            template.main_updater.append(wrapper)
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
            updater_list = template.option_updater.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_key(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_key(self, option: str, func: _KeyUpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_key(self, option: str, func: _KeyUpdaterVar, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def on_update_key(
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

        def wrapper_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        def decorator(func: _KeyUpdaterVar, /) -> _KeyUpdaterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, check_override=bool(use_override), no_object=False)
            self.on_update(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_key_from_map(
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
    def on_update_key_from_map(
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

    def on_update_key_from_map(
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
        return self.on_update_key(option, func, use_key=use_key, use_override=use_override)

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
            updater_list = template.option_value_updater.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_key_value(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_key_value(
        self, option: str, /, *, use_key: Hashable, use_override: bool = True
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_key_value(self, option: str, func: _KeyValueUpdaterVar, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_key_value(
        self, option: str, func: _KeyValueUpdaterVar, /, *, use_key: Hashable, use_override: bool = True
    ) -> None:
        ...

    def on_update_key_value(
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

        def wrapper_decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            return lambda self, value: func(self, use_key, value)

        def decorator(func: _KeyValueUpdaterVar, /) -> _KeyValueUpdaterVar:
            wrapper = _WrappedFunctionWrapper(func, key, wrapper_decorator, check_override=bool(use_override), no_object=False)
            self.on_update_value(option, wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_key_from_map_value(
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
    def on_update_key_from_map_value(
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

    def on_update_key_from_map_value(
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
        return self.on_update_key_value(option, func, use_key=use_key, use_override=use_override)

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
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if wrapper in value_validator_list:
                raise OptionError(option, "Function already registered")
            value_validator_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_validator_static(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_StaticValueValidatorVar], _StaticValueValidatorVar]:
        ...

    @overload
    def add_value_validator_static(
        self, option: str, objtype: type, /, *, accept_none: bool = False, use_override: bool = True
    ) -> None:
        ...

    @overload
    def add_value_validator_static(
        self, option: str, objtypes: Sequence[type], /, *, accept_none: bool = False, use_override: bool = True
    ) -> None:
        ...

    @overload
    def add_value_validator_static(self, option: str, func: _StaticValueValidatorVar, /, *, use_override: bool = True) -> None:
        ...

    def add_value_validator_static(
        self,
        option: str,
        func: _StaticValueValidatorVar | type | Sequence[type] | None = None,
        /,
        *,
        accept_none: bool = False,
        use_override: bool = True,
    ) -> Callable[[_StaticValueValidatorVar], _StaticValueValidatorVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(
            func: _StaticValueValidatorVar, /, *, check_override: bool = bool(use_override)
        ) -> _StaticValueValidatorVar:
            value_validator_list = template.value_validator.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=check_override, no_object=True)
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

            decorator(type_checker, check_override=False)
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_converter(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar]:
        ...

    @overload
    def add_value_converter(self, option: str, func: _ValueConverterVar, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter(
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
            raise TypeError("Use add_value_converter_static() to convert value using type")

        def decorator(func: _ValueConverterVar) -> _ValueConverterVar:
            value_converter_list = template.value_converter.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_converter_static(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar]:
        ...

    @overload
    def add_value_converter_static(
        self, option: str, convert_to_type: type[Any], /, *, accept_none: bool = False, use_override: bool = True
    ) -> None:
        ...

    @overload
    def add_value_converter_static(self, option: str, func: _StaticValueConverterVar, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter_static(
        self,
        option: str,
        func: _StaticValueConverterVar | type | None = None,
        /,
        *,
        accept_none: bool = False,
        use_override: bool = True,
    ) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(
            func: _StaticValueConverterVar, /, *, check_override: bool = bool(use_override)
        ) -> _StaticValueConverterVar:
            value_converter_list = template.value_converter.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=check_override, no_object=True)
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)
            return func

        if isinstance(func, type):

            if issubclass(func, Enum):
                raise TypeError("Use add_enum_converter() instead for enum conversions")

            value_converter: Any = _make_value_converter(func, accept_none)

            decorator(value_converter, check_override=False)
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_enum_converter(self, option: str, enum: type[Enum], *, store_value: bool = False, accept_none: bool = False) -> None:
        ...

    @overload
    def add_enum_converter(self, option: str, enum: type[Enum], *, return_value_on_get: bool, accept_none: bool = False) -> None:
        ...

    def add_enum_converter(self, option: str, enum: type[Enum], *, accept_none: bool = False, **kwargs: bool) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if not issubclass(enum, Enum):
            raise TypeError("Not an Enum class")

        if "store_value" in kwargs and "return_value_on_get" in kwargs:
            raise TypeError("Invalid arguments")

        store_value: bool = kwargs.pop("store_value", False)
        return_value_on_get: bool | None = kwargs.pop("return_value_on_get", None)

        if kwargs:
            raise TypeError("Invalid arguments")

        if option in template.enum_converter_registered:
            enum = template.enum_converter_registered[option]
            raise ValueError(f"Enum converter already set for option {option!r}: {enum.__qualname__!r}")

        self.add_value_converter_static(option, _make_enum_converter(enum, store_value, accept_none), use_override=False)
        template.enum_converter_registered[option] = enum
        if return_value_on_get is not None:
            template.enum_return_value[option] = bool(return_value_on_get)

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

    def register_copy_func(self, cls: type, func: Callable[[Any], Any], *, allow_subclass: bool = False) -> None:
        self.__check_locked()
        if not isinstance(cls, type):
            raise TypeError("'cls' argument must be a type")
        if not callable(func):
            raise TypeError("'func' is not callable")
        template: _ConfigInfoTemplate = self.__template
        template.value_copy[cls] = func
        template.value_copy_allow_subclass[cls] = bool(allow_subclass)

    def readonly(self, *options: str) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        for option in options:
            self.check_option_validity(option)
            descriptor: _Descriptor | None = template.value_descriptors.get(option)
            if isinstance(descriptor, _ReadOnlyOptionBuildPayload):
                continue
            if isinstance(descriptor, (_MutableDescriptor, _RemovableDescriptor)):
                if not isinstance(descriptor, property) or descriptor.fset is not None or descriptor.fdel is not None:
                    raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            template.value_descriptors[option] = _ReadOnlyOptionBuildPayload()

    def __check_locked(self) -> None:
        if self.__bound_class is not None:
            raise TypeError(f"Attempt to modify template after the class creation")

    @property
    @final
    def owner(self) -> type | None:
        return self.__bound_class

    @property
    @final
    def name(self) -> str | None:
        return self.__attr_name


@final
class OptionAttribute(Generic[_T], Object):

    __slots__ = ("__name", "__owner", "__config_name", "__doc__")

    def __init__(self, doc: str | None = None) -> None:
        super().__init__()
        self.__doc__ = doc

    def __set_name__(self, owner: type, name: str, /) -> None:
        if len(name) == 0:
            raise ValueError("Attribute name must not be empty")
        with suppress(AttributeError):
            if self.__name != name:
                raise ValueError(f"Assigning {self.__name!r} config attribute to {name}")
        self.__name: str = name
        self.__owner: type = owner
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
        config_name: str = self.__config_name
        name: str = self.__name
        config: Configuration[Any] = getattr(obj, config_name)  # TODO: Fix use of super()

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
    def name(self) -> str:
        return self.__name


def _default_mapping() -> MappingProxyType[Any, Any]:
    return MappingProxyType({})


@final
@dataclass(frozen=True, eq=False, slots=True)
class ConfigurationInfo(Object):
    options: frozenset[str]
    _: KW_ONLY
    option_value_updater: Mapping[str, Callable[[object, Any], None]] = field(default_factory=_default_mapping)
    option_updater: Mapping[str, Callable[[object], None]] = field(default_factory=_default_mapping)
    many_options_updater: Callable[[object, Sequence[str]], None] | None = field(default=None)
    main_updater: Callable[[object], None] | None = field(default=None)
    value_converter: Mapping[str, Callable[[object, Any], Any]] = field(default_factory=_default_mapping)
    value_validator: Mapping[str, Callable[[object, Any], None]] = field(default_factory=_default_mapping)
    value_descriptors: Mapping[str, _Descriptor] = field(default_factory=_default_mapping)
    autocopy: bool = field(default=False)
    value_autocopy_get: Mapping[str, bool] = field(default_factory=_default_mapping)
    value_autocopy_set: Mapping[str, bool] = field(default_factory=_default_mapping)
    attribute_class_owner: Mapping[str, type] = field(default_factory=_default_mapping)
    aliases: Mapping[str, str] = field(default_factory=_default_mapping)
    value_copy: Mapping[type, Callable[[Any], Any]] = field(default_factory=_default_mapping)
    value_copy_allow_subclass: Mapping[type, bool] = field(default_factory=_default_mapping)
    readonly_options: frozenset[str] = field(default_factory=frozenset)
    enum_return_value: frozenset[str] = field(default_factory=frozenset)

    if TYPE_CHECKING:
        __hash__: None  # type: ignore[assignment]

    __hash__ = None  # type: ignore[assignment]

    class __ReadOnlyOptionWrapper:
        def __init__(self, default_descriptor: _Descriptor) -> None:
            self.__descriptor: Callable[[], _Descriptor] = lambda: default_descriptor

        def __get__(self, obj: object, objtype: type | None = None, /) -> Any:
            descriptor: _Descriptor = self.__descriptor()
            return descriptor.__get__(obj, objtype)

    def check_option_validity(self, option: str, *, use_alias: bool = False) -> str:
        if use_alias:
            option = self.aliases.get(option, option)
        if option not in self.options:
            if not option:
                raise EmptyOptionNameError()
            raise UnknownOptionError(option)
        return option

    def is_option_valid(self, option: str, *, use_alias: bool = False) -> bool:
        try:
            self.check_option_validity(option, use_alias=use_alias)
        except OptionError:
            return False
        return True

    def get_value_descriptor(self, option: str, objtype: type) -> _Descriptor:
        descriptor: _Descriptor | None = self.value_descriptors.get(option, None)
        if descriptor is None:
            descriptor = _PrivateAttributeOptionPropertyFallback()
            descriptor.__set_name__(self.attribute_class_owner.get(option, objtype), option)
        if option in self.readonly_options:
            descriptor = self.__ReadOnlyOptionWrapper(descriptor)
        return descriptor

    def get_copy_func(self, objtype: type) -> Callable[[Any], Any]:
        try:
            return self.value_copy[objtype]
        except KeyError:
            if self.value_copy_allow_subclass.get(objtype, False):
                for _type, func in self.value_copy.items():
                    if issubclass(objtype, _type):
                        return func
        return copy


_InitializationRegister: TypeAlias = dict[str, Any]
_UpdateRegister: TypeAlias = list[str]


class Configuration(Generic[_T], Object):
    __update_stack: ClassVar[dict[object, list[str]]] = dict()
    __init_context: ClassVar[dict[object, _InitializationRegister]] = dict()
    __update_context: ClassVar[dict[object, _UpdateRegister]] = dict()
    __lock_cache: ClassVar[WeakKeyDictionary[object, RLock]] = WeakKeyDictionary()
    __default_lock: ClassVar[RLock] = RLock()

    __slots__ = ("__info", "__obj", "__weakref__")

    class __OptionUpdateContext(NamedTuple):
        first_call: bool
        init_context: _InitializationRegister | None
        updated: _UpdateRegister

    __DELETED: Any = object()

    def __init__(self, obj: _T | WeakReferenceType[_T], info: ConfigurationInfo) -> None:
        self.__obj: Callable[[], _T | None] = obj if isinstance(obj, WeakReferenceType) else lambda obj=obj: obj  # type: ignore[misc]
        self.__info: ConfigurationInfo = info

    def __repr__(self) -> str:
        option_dict = self.as_dict()
        return f"{type(self).__name__}({', '.join(f'{k}={option_dict[k]!r}' for k in sorted(option_dict))})"

    def __contains__(self, option: str) -> bool:
        return self.get(option, _MISSING) is not _MISSING

    @overload
    def get(self, option: str) -> Any:
        ...

    @overload
    def get(self, option: str, default: _DT) -> Any | _DT:
        ...

    def get(self, option: str, default: Any = _NO_DEFAULT) -> Any:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_descriptor(option, type(obj))
        try:
            with self.__lazy_lock(obj):
                value: Any = descriptor.__get__(obj, type(obj))
        except (AttributeError, UnregisteredOptionError):
            if default is _NO_DEFAULT:
                raise
            return default
        if option in info.enum_return_value and isinstance(value, Enum):
            return value.value
        if info.value_autocopy_get.get(option, info.autocopy):
            copy_func = info.get_copy_func(type(value))
            value = copy_func(value)
        return value

    def __getitem__(self, option: str, /) -> Any:
        try:
            return self.get(option)
        except OptionError as exc:
            raise KeyError(option) from exc

    def as_dict(self, *, sorted_keys: bool = False) -> dict[str, Any]:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
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
        info: ConfigurationInfo = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_descriptor(option, type(obj))

        if not isinstance(descriptor, _MutableDescriptor):
            raise OptionError(option, "Cannot be set")

        value_validator: Callable[[object, Any], None] | None = info.value_validator.get(option, None)
        value_converter: Callable[[object, Any], Any] | None = info.value_converter.get(option, None)
        if value_validator is not None:
            value_validator(obj, value)
        converter_applied: bool = False
        if value_converter is not None:
            value = value_converter(obj, value)
            converter_applied = True

        with self.__updating_option(obj, option, info, call_updaters=True) as update_context:
            try:
                actual_value = descriptor.__get__(obj, type(obj))
            except (AttributeError, UnregisteredOptionError):
                pass
            else:
                if actual_value is value or actual_value == value:
                    return

            if not converter_applied and info.value_autocopy_set.get(option, info.autocopy):
                copy_func = info.get_copy_func(type(value))
                value = copy_func(value)

            descriptor.__set__(obj, value)
            update_context.updated.append(option)

            register = update_context.init_context
            if register is not None:
                register[option] = value
                return

            value_updater = info.option_value_updater.get(option, None)
            if value_updater is not None:
                value_updater(obj, value)

    def __setitem__(self, option: str, value: Any, /) -> None:
        try:
            self.set(option, value)
        except OptionError as exc:
            raise KeyError(option) from exc

    def delete(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_descriptor(option, type(obj))

        if not isinstance(descriptor, _RemovableDescriptor):
            raise OptionError(option, "Cannot be deleted")

        with self.__updating_option(obj, option, info, call_updaters=True) as update_context:
            descriptor.__delete__(obj)
            update_context.updated.append(option)
            register = update_context.init_context
            if register is not None:
                register[option] = self.__DELETED
                return

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
        with self.__updating_many_options(obj, *options, info=self.__info, call_updaters=True):
            for option, value in kwargs.items():
                self.set(option, value)

    @contextmanager
    def initialization(self) -> Iterator[None]:
        obj: _T = self.__self__

        with self.__lazy_lock(obj):
            if obj in Configuration.__init_context:
                yield
                return

            if obj in Configuration.__update_stack:
                raise InitializationError("Cannot use initialization context while updating an option value")

            def cleanup() -> None:
                if obj is not None:
                    Configuration.__init_context.pop(obj, None)

            with ExitStack() as stack:
                initialization_register: _InitializationRegister = {}
                Configuration.__init_context[obj] = initialization_register
                stack.callback(cleanup)
                yield
                update_register: _InitializationRegister = {}
                Configuration.__init_context[obj] = update_register
                info: ConfigurationInfo = self.__info
                with self.__updating_many_options(obj, *initialization_register, info=info, call_updaters=False):
                    for option, value in initialization_register.items():
                        if value is self.__DELETED:
                            continue
                        value_update = info.option_value_updater.get(option, None)
                        if value_update is not None:
                            value_update(obj, value)
                    if update_register:
                        raise OptionError("", "Options were modified after value update in initialization context")
                    many_options_updater = info.many_options_updater
                    if many_options_updater is not None and len(initialization_register) > 1:
                        many_options_updater(obj, tuple(initialization_register))
                    else:
                        for option in initialization_register:
                            option_updater = info.option_updater.get(option, None)
                            if option_updater is not None:
                                option_updater(obj)
                    if update_register:
                        raise OptionError("", "Options were modified after update in initialization context")
                    main_updater = info.main_updater
                    if main_updater is not None:
                        main_updater(obj)
                        if update_register:
                            raise OptionError("", "Options were modified after main update in initialization context")

    @final
    def has_initialization_context(self) -> bool:
        return self.__self__ in Configuration.__init_context

    def update_option(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
        option = info.check_option_validity(option, use_alias=True)
        return self.__update_single_option(obj, option, info)

    def update_options(self, *options: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
        options = tuple(dict.fromkeys(info.check_option_validity(option, use_alias=True) for option in options))
        return self.__update_options(obj, *options, info=info)

    def update_all_options(self) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
        return self.__update_options(obj, *info.options, info=info)

    def __reduce_ex__(self, __protocol: SupportsIndex) -> str | tuple[Any, ...]:
        raise TypeError(f"cannot pickle {self.__class__.__qualname__!r} object")

    def __reduce__(self) -> str | tuple[Any, ...]:
        raise TypeError(f"cannot pickle {self.__class__.__qualname__!r} object")

    @property
    @final
    def info(self) -> ConfigurationInfo:
        return self.__info

    @property
    @final
    def __self__(self) -> _T:
        obj: _T | None = self.__obj()
        if obj is None:
            raise ReferenceError("weakly-referenced object no longer exists")
        return obj

    @staticmethod
    def __update_options(obj: object, *options: str, info: ConfigurationInfo) -> None:
        nb_options = len(options)
        if nb_options < 1:
            return
        if nb_options == 1:
            return Configuration.__update_single_option(obj, options[0], info)

        objtype: type = type(obj)
        with Configuration.__updating_many_options(obj, *options, info=info, call_updaters=False) as update_contexts:
            options = tuple(option for option, context in update_contexts.items() if context.first_call)
            if not options:
                return
            for option in options:
                descriptor = info.get_value_descriptor(option, objtype)
                try:
                    value: Any = descriptor.__get__(obj, type(obj))
                except (AttributeError, UnregisteredOptionError):
                    pass
                else:
                    value_update = info.option_value_updater.get(option, None)
                    if value_update is not None:
                        value_update(obj, value)
            many_options_updater = info.many_options_updater
            if many_options_updater is not None and len(options) > 1:
                many_options_updater(obj, options)
            else:
                for option in options:
                    option_updater = info.option_updater.get(option, None)
                    if option_updater is not None:
                        option_updater(obj)
            main_updater = info.main_updater
            if main_updater is not None:
                main_updater(obj)

    @staticmethod
    def __update_single_option(obj: object, option: str, info: ConfigurationInfo) -> None:
        descriptor = info.get_value_descriptor(option, type(obj))

        with Configuration.__updating_option(obj, option, info, call_updaters=False) as update_context:
            if not update_context.first_call:
                return
            try:
                value: Any = descriptor.__get__(obj, type(obj))
            except (AttributeError, UnregisteredOptionError):
                pass
            else:
                value_update = info.option_value_updater.get(option, None)
                if value_update is not None:
                    value_update(obj, value)
            option_updater = info.option_updater.get(option, None)
            if option_updater is not None:
                option_updater(obj)
            main_updater = info.main_updater
            if main_updater is not None:
                main_updater(obj)

    @staticmethod
    @contextmanager
    def __updating_option(
        obj: object, option: str, info: ConfigurationInfo, *, call_updaters: bool
    ) -> Iterator[__OptionUpdateContext]:
        UpdateContext = Configuration.__OptionUpdateContext

        with Configuration.__lazy_lock(obj):
            register = Configuration.__init_context.get(obj, None)
            if register is not None:
                yield UpdateContext(first_call=False, init_context=register, updated=[])
                return

            update_register: _UpdateRegister = Configuration.__update_context.setdefault(obj, [])
            update_stack: list[str] = Configuration.__update_stack.setdefault(obj, [])
            if option in update_stack:
                yield UpdateContext(first_call=False, init_context=None, updated=update_register)
                return

            def cleanup() -> None:
                with suppress(ValueError):
                    update_stack.remove(option)
                if not update_stack:
                    Configuration.__update_stack.pop(obj, None)

            update_stack.append(option)
            with ExitStack() as stack:
                stack.callback(cleanup)
                yield UpdateContext(first_call=True, init_context=None, updated=update_register)
            if update_stack:
                return
            update_register = list(dict.fromkeys(Configuration.__update_context.pop(obj, update_register)))
            if not call_updaters:
                return
            if update_register:
                main_updater = info.main_updater
                many_options_updater = info.many_options_updater if len(update_register) > 1 else None
                if many_options_updater is not None:
                    many_options_updater(obj, update_register)
                else:
                    for option in update_register:
                        option_updater = info.option_updater.get(option, None)
                        if option_updater is not None and option_updater is not main_updater:
                            option_updater(obj)
                if main_updater is not None:
                    main_updater(obj)

    @staticmethod
    @contextmanager
    def __updating_many_options(
        obj: object, *options: str, info: ConfigurationInfo, call_updaters: bool
    ) -> Iterator[dict[str, __OptionUpdateContext]]:
        nb_options = len(options)
        if nb_options < 1:
            yield {}
            return
        if nb_options == 1:
            with Configuration.__updating_option(obj, options[0], info, call_updaters=call_updaters) as update_context:
                yield {options[0]: update_context}
            return

        with Configuration.__lazy_lock(obj), ExitStack() as stack:
            yield {
                option: stack.enter_context(Configuration.__updating_option(obj, option, info, call_updaters=call_updaters))
                for option in options
            }

    @staticmethod
    def __lazy_lock(obj: object) -> RLock | nullcontext[None]:
        lock_cache = Configuration.__lock_cache
        try:
            lock: RLock = lock_cache.get(obj, _MISSING)
        except TypeError:
            return nullcontext()
        if lock is _MISSING:
            with Configuration.__default_lock:
                lock = lock_cache.get(obj, _MISSING)
                if lock is _MISSING:
                    try:
                        lock_cache[obj] = lock = RLock()
                    except Exception:
                        return nullcontext()
        return lock


def _no_type_check_cache(func: _FuncVar) -> _FuncVar:
    return cache(func)  # type: ignore[return-value]


def _make_function_wrapper(func: Any, *, check_override: bool = True, no_object: bool = False) -> Callable[..., Any]:
    wrapper: _FunctionWrapperBuilder | _WrappedFunctionWrapper
    if isinstance(func, _WrappedFunctionWrapper):
        wrapper = func
    else:
        wrapper = _FunctionWrapperBuilder(func, check_override=check_override, no_object=no_object)
    cached_func = wrapper.get_wrapper()
    if cached_func is not None:
        return cached_func
    return wrapper


@final
class _FunctionWrapperBuilder:
    __slots__ = ("info", "cache")

    class Info(NamedTuple):
        func: Any
        check_override: bool
        no_object: bool

    info: Info
    cache: dict[Any, Callable[..., Any]]

    __instance_cache: dict[Info, _FunctionWrapperBuilder] = dict()

    def __new__(cls, func: Any, check_override: bool, no_object: bool) -> _FunctionWrapperBuilder:
        if isinstance(func, cls):
            if func.info.check_override == check_override and func.info.no_object:
                return func
            func = func.info.func
        info = cls.Info(func=func, check_override=check_override, no_object=no_object)
        try:
            self = cls.__instance_cache[info]
        except KeyError:
            self = object.__new__(cls)
            self.info = info
            self.cache = {}
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
        check_override = info.check_override

        func_name: str = ""
        if check_override:
            func_name = next((attr_name for attr_name, attr_obj in _all_members(cls).items() if attr_obj is func), func_name)
            check_override = bool(func_name)

        if isinstance(func, (BuiltinFunctionType, BuiltinMethodType)) or not hasattr(func, "__get__"):
            no_object = True

        if info != self.Info(func, check_override=check_override, no_object=no_object):
            # Ask the right builder to compute the wrapper
            builder = self.__class__(func, check_override=check_override, no_object=no_object)
            computed_wrapper = builder.build_wrapper(cls)
            self.cache[func] = computed_wrapper  # Save in our cache for further calls
            return computed_wrapper

        if no_object:

            if func_name:

                def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                    _func: Callable[..., Any] = getattr(self, func_name, func)
                    return _func(*args, **kwargs)

            else:

                def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                    return func(*args, **kwargs)

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
        check_override: bool,
        no_object: bool,
    ) -> _WrappedFunctionWrapper:
        self = object.__new__(cls)

        self.wrapper = _FunctionWrapperBuilder(func, check_override, no_object)
        self.decorator = wrapper_decorator
        self.cache = self.__wrapper_cache.setdefault(unique_key, {})

        return self

    def __call__(self, *args: Any, **kwds: Any) -> Any:
        raise NotImplementedError("Dummy function")

    def get_wrapper(self) -> Callable[..., Any] | None:
        wrapper_cache = self.cache
        func: Any = self.wrapper.info.func
        if func in wrapper_cache:
            return wrapper_cache[func]
        return self.wrapper.get_wrapper()

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


@_no_type_check_cache
def _make_type_checker(_type: type | tuple[type, ...], accept_none: bool) -> Callable[[Any], None]:
    def type_checker(val: Any, /) -> None:
        if (accept_none and val is None) or isinstance(val, _type):
            return
        expected: str
        if isinstance(_type, type):
            expected = f"a {_type.__qualname__} object type"
        else:
            expected = f"one of those object types: ({', '.join(t.__qualname__ for t in _type)})"
        cls: type = type(val)
        got: str = repr(cls.__qualname__ if cls.__module__ != object.__module__ else val)
        raise TypeError(f"Invalid value type. expected {expected}, got {got}")

    return type_checker


@_no_type_check_cache
def _make_value_converter(_type: type, accept_none: bool) -> Callable[[Any], Any]:
    def value_converter(val: Any, /, *, _type: Callable[[Any], Any] = _type) -> Any:
        if accept_none and val is None:
            return None
        return _type(val)

    return value_converter


@_no_type_check_cache
def _make_enum_converter(enum: type[Enum], store_value: bool, accept_none: bool) -> Callable[[Any], Any]:
    if not store_value:

        def value_converter(val: Any, /, *, enum: type[Enum] = enum) -> Any:
            if accept_none and val is None:
                return None
            val = enum(val)
            return val

    else:

        def value_converter(val: Any, /, *, enum: type[Enum] = enum) -> Any:
            if accept_none and val is None:
                return None
            val = enum(val)
            return val.value

    return value_converter


def _all_members(cls: type) -> MutableMapping[str, Any]:
    return ChainMap(*map(vars, inspect.getmro(cls)))


def _register_configuration(cls: type, config: ConfigurationTemplate | None) -> ConfigurationTemplate | None:
    former_config: ConfigurationTemplate | None = None
    with suppress(TypeError):
        former_config = _retrieve_configuration(cls)
    if isinstance(config, ConfigurationTemplate):
        setattr(cls, "_bound_configuration_", config)
    else:
        with suppress(AttributeError):
            delattr(cls, "_bound_configuration_")
    return former_config


def _retrieve_configuration(cls: type) -> ConfigurationTemplate:
    try:
        config: ConfigurationTemplate = getattr(cls, "_bound_configuration_")
        if not isinstance(config, ConfigurationTemplate):
            raise AttributeError
    except AttributeError:
        raise TypeError(f"{cls.__name__} does not have a {ConfigurationTemplate.__name__} object") from None
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


class _ConfigInfoTemplate:
    def __init__(self, known_options: Sequence[str], autocopy: bool | None, parents: Sequence[_ConfigInfoTemplate]) -> None:
        self.options: frozenset[str] = frozenset(known_options)
        self.main_updater: list[Callable[[object], None]] = list()
        self.option_updater: dict[str, list[Callable[[object], None]]] = dict()
        self.option_value_updater: dict[str, list[Callable[[object, Any], None]]] = dict()
        self.value_descriptors: dict[str, _Descriptor] = dict()
        self.value_converter: dict[str, list[Callable[[object, Any], Any]]] = dict()
        self.value_validator: dict[str, list[Callable[[object, Any], None]]] = dict()
        self.autocopy: bool = bool(autocopy) if autocopy is not None else False
        self.value_autocopy_get: dict[str, bool] = dict()
        self.value_autocopy_set: dict[str, bool] = dict()
        self.attribute_class_owner: dict[str, type] = dict()
        self.aliases: dict[str, str] = dict()
        self.value_copy: dict[type, Callable[[Any], Any]] = dict()
        self.value_copy_allow_subclass: dict[type, bool] = dict()
        self.enum_converter_registered: dict[str, type[Enum]] = dict()
        self.enum_return_value: dict[str, bool] = dict()

        merge_dict = self.__merge_dict
        merge_list = self.__merge_list
        merge_updater_dict = self.__merge_updater_dict
        for p in parents:
            self.options |= p.options
            if autocopy is None:
                self.autocopy |= p.autocopy
            merge_list(self.main_updater, p.main_updater, on_duplicate="skip", setting="main_update")
            merge_updater_dict(self.option_updater, p.option_updater, setting="update")
            merge_updater_dict(self.option_value_updater, p.option_value_updater, setting="value_update")
            merge_dict(self.value_descriptors, p.value_descriptors, on_conflict="raise", setting="descriptor")
            merge_dict(
                self.value_converter,
                p.value_converter,
                on_conflict="raise",
                setting="value_converter",
                copy=list.copy,
            )
            merge_dict(
                self.value_validator,
                p.value_validator,
                on_conflict="raise",
                setting="value_validator",
                copy=list.copy,
            )
            merge_dict(
                self.value_autocopy_get,
                p.value_autocopy_get,
                on_conflict=lambda _, v1, v2: v1 | v2,
                setting="autocopy_get",
            )
            merge_dict(
                self.value_autocopy_set,
                p.value_autocopy_set,
                on_conflict=lambda _, v1, v2: v1 | v2,
                setting="autocopy_set",
            )
            merge_dict(self.attribute_class_owner, p.attribute_class_owner, on_conflict="skip", setting="class_owner")
            merge_dict(self.aliases, p.aliases, on_conflict="raise", setting="aliases")
            merge_dict(self.value_copy, p.value_copy, on_conflict="raise", setting="value_copy_func")
            merge_dict(
                self.value_copy_allow_subclass,
                p.value_copy_allow_subclass,
                on_conflict="raise",
                setting="copy_allow_subclass",
            )
            merge_dict(
                self.enum_converter_registered,
                p.enum_converter_registered,
                on_conflict="raise",
                setting="enum_converter_registered",
            )
            merge_dict(self.enum_return_value, p.enum_return_value, on_conflict="raise", setting="enum_return_value")

        self.parent_descriptors: frozenset[_Descriptor] = frozenset(self.value_descriptors.values())

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
                    raise ConfigError(f"Conflict of setting {setting!r} for {key!r} key")
                if callable(on_conflict):
                    value = on_conflict(key, d1[key], value)
            if copy is not None:
                value = copy(value)
            d1[key] = value

    @staticmethod
    def __merge_list(
        l1: list[_T],
        l2: list[_T],
        /,
        *,
        on_duplicate: L["keep", "put_at_end", "raise", "skip"],
        setting: str,
        copy: Callable[[_T], _T] | None = None,
    ) -> None:
        for value in l2:
            if value in l1:
                if on_duplicate == "skip":
                    continue
                if on_duplicate == "put_at_end":
                    l1.remove(value)
                elif on_duplicate == "raise":
                    raise ConfigError(f"Conflict of setting {setting!r}: Duplicate of value {value!r}")
            if copy is not None:
                value = copy(value)
            l1.append(value)

    @classmethod
    def __merge_updater_dict(
        cls,
        d1: dict[str, list[_FuncVar]],
        d2: dict[str, list[_FuncVar]],
        /,
        *,
        setting: str,
    ) -> None:
        merge_list = cls.__merge_list
        for key, l2 in d2.items():
            l1 = d1.setdefault(key, [])
            merge_list(l1, l2, on_duplicate="skip", setting=setting)

    def build(self, owner: type) -> ConfigurationInfo:
        self.__intern_build_all_wrappers(owner)

        return ConfigurationInfo(
            options=frozenset(self.options),
            option_value_updater=self.__build_option_value_updater_dict(),
            option_updater=self.__build_option_updater_dict(),
            many_options_updater=self.__build_many_options_updater(),
            main_updater=self.__build_main_updater(),
            value_converter=self.__build_value_converter_dict(),
            value_validator=self.__build_value_validator_dict(),
            value_descriptors=self.__build_value_descriptor_dict(),
            autocopy=bool(self.autocopy),
            value_autocopy_get=MappingProxyType(self.value_autocopy_get.copy()),
            value_autocopy_set=MappingProxyType(self.value_autocopy_set.copy()),
            attribute_class_owner=MappingProxyType(self.attribute_class_owner.copy()),
            aliases=MappingProxyType(self.aliases.copy()),
            value_copy=MappingProxyType(self.value_copy.copy()),
            value_copy_allow_subclass=MappingProxyType(self.value_copy_allow_subclass.copy()),
            readonly_options=self.__build_readonly_options_set(),
            enum_return_value=self.__build_enum_return_value_set(),
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

        callback_list: list[Callable[..., Any]]
        for callback_list in chain(  # type: ignore[assignment]
            [self.main_updater],
            self.option_updater.values(),
            self.option_value_updater.values(),
            self.value_converter.values(),
            self.value_validator.values(),
        ):
            callback_list[:] = [build_wrapper_if_needed(func) for func in callback_list]
        for option, descriptor in tuple(self.value_descriptors.items()):
            self.value_descriptors[option] = build_wrapper_within_descriptor(descriptor)

    def __build_option_value_updater_dict(self) -> MappingProxyType[str, Callable[[object, Any], None]]:
        build_option_value_updater = self.__build_option_value_updater_func

        return MappingProxyType(
            {
                option: build_option_value_updater(updater_list)
                for option, updater_list in self.option_value_updater.items()
                if len(updater_list) > 0
            }
        )

    @staticmethod
    def __build_option_value_updater_func(updater_list: Sequence[Callable[[object, Any], None]]) -> Callable[[object, Any], None]:
        if len(updater_list) == 1:
            return updater_list[0]

        def option_value_updater_func(
            obj: object, value: Any, /, *, updater_list: Sequence[Callable[[object, Any], None]] = tuple(updater_list)
        ) -> None:
            for option_value_updater in updater_list:
                option_value_updater(obj, value)

        return option_value_updater_func

    def __build_main_updater(self) -> Callable[[object], None] | None:
        main_updater_list = self.main_updater
        if not main_updater_list:
            return None
        build_updater = self.__build_updater_func
        return build_updater(main_updater_list)

    def __build_option_updater_dict(self) -> MappingProxyType[str, Callable[[object], None]]:
        build_updater = self.__build_updater_func
        main_updater_list = self.main_updater

        return MappingProxyType(
            {
                option: build_updater(filtered_updater_list)
                for option, updater_list in self.option_updater.items()
                if len((filtered_updater_list := [f for f in updater_list if f not in main_updater_list])) > 0
            }
        )

    @staticmethod
    def __build_updater_func(updater_list: Sequence[Callable[[object], None]]) -> Callable[[object], None]:
        if len(updater_list) == 1:
            return updater_list[0]

        def updater_func(obj: object, /, *, updater_list: Sequence[Callable[[object], None]] = tuple(updater_list)) -> None:
            for updater in updater_list:
                updater(obj)

        return updater_func

    def __build_many_options_updater(self) -> Callable[[object, Sequence[str]], None] | None:
        main_updater_list = self.main_updater
        option_updater_dict = {
            option: filtered_updater_list
            for option, updater_list in self.option_updater.items()
            if len((filtered_updater_list := [f for f in updater_list if f not in main_updater_list])) > 0
        }
        if len(option_updater_dict) < 2:
            return None

        # Check if all callbacks are hashable
        # (Commonly true but who knows...)
        try:
            _ = [hash(f) for f in chain.from_iterable(option_updater_dict.values())]
        except TypeError:
            # Not hashable, use our (less optmized) merge_list for unique call

            merge_list = _ConfigInfoTemplate.__merge_list

            def many_options_updater_func(
                obj: object,
                options: Sequence[str],
                /,
                *,
                option_updater_dict: dict[str, list[Callable[[object], None]]] = option_updater_dict,
            ) -> None:
                updater_list: list[Callable[[object], None]] = []
                for option in options:
                    merge_list(updater_list, option_updater_dict.get(option, []), on_duplicate="skip", setting="")
                for updater in updater_list:
                    updater(obj)

        else:

            def many_options_updater_func(
                obj: object,
                options: Sequence[str],
                /,
                *,
                option_updater_dict: dict[str, list[Callable[[object], None]]] = option_updater_dict,
            ) -> None:
                for updater in dict.fromkeys(chain.from_iterable(option_updater_dict.get(option, ()) for option in options)):
                    updater(obj)

        return many_options_updater_func

    def __build_value_converter_dict(self) -> MappingProxyType[str, Callable[[object, Any], Any]]:
        build_converter = self.__build_value_converter_func

        return MappingProxyType(
            {
                option: build_converter(converter_list)
                for option, converter_list in self.value_converter.items()
                if len(converter_list) > 0
            }
        )

    @staticmethod
    def __build_value_converter_func(converter_list: Sequence[Callable[[object, Any], Any]]) -> Callable[[object, Any], Any]:
        if len(converter_list) == 1:
            return converter_list[0]

        def value_converter_func(
            obj: object, value: Any, /, *, converter_list: Sequence[Callable[[object, Any], Any]] = tuple(converter_list)
        ) -> Any:
            for converter in converter_list:
                value = converter(obj, value)
            return value

        return value_converter_func

    def __build_value_validator_dict(self) -> MappingProxyType[str, Callable[[object, Any], None]]:
        build_value_validator = self.__build_value_validator_func

        return MappingProxyType(
            {
                option: build_value_validator(validator_list)
                for option, validator_list in self.value_validator.items()
                if len(validator_list) > 0
            }
        )

    @staticmethod
    def __build_value_validator_func(validator_list: Sequence[Callable[[object, Any], None]]) -> Callable[[object, Any], None]:
        if len(validator_list) == 1:
            return validator_list[0]

        def value_validator_func(
            obj: object, value: Any, /, *, validator_list: Sequence[Callable[[object, Any], None]] = tuple(validator_list)
        ) -> None:
            for value_validator in validator_list:
                value_validator(obj, value)

        return value_validator_func

    def __build_value_descriptor_dict(self) -> MappingProxyType[str, _Descriptor]:
        value_descriptors: dict[str, _Descriptor] = {}

        for option, descriptor in self.value_descriptors.items():
            if isinstance(descriptor, _ReadOnlyOptionBuildPayload):
                underlying_descriptor = descriptor.get_descriptor()
                if underlying_descriptor is None:
                    continue
                descriptor = underlying_descriptor
            value_descriptors[option] = descriptor

        return MappingProxyType(value_descriptors)

    def __build_readonly_options_set(self) -> frozenset[str]:
        return frozenset(
            option for option, descriptor in self.value_descriptors.items() if isinstance(descriptor, _ReadOnlyOptionBuildPayload)
        )

    def __build_enum_return_value_set(self) -> frozenset[str]:
        return frozenset(option for option, value in self.enum_return_value.items() if value)


class _ConfigInitializer:

    __slots__ = ("__func__", "__dict__")

    def __init__(self, func: Callable[..., Any]) -> None:
        if not hasattr(func, "__get__"):
            raise TypeError("Built-in functions cannot be used")
        self.__func__: Callable[..., Any] = func

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

        @wraps(init_func)
        def config_initializer(self: object, /, *args: Any, **kwargs: Any) -> Any:
            config_template: ConfigurationTemplate = _retrieve_configuration(type(self))
            config_name = config_template.name
            if config_name is None:
                raise TypeError("ConfigurationTemplate object was not initialized using __set_name__")
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


class _PrivateAttributeOptionPropertyFallback:
    def __set_name__(self, owner: type, name: str, /) -> None:
        self.__name: str = name
        self.__attribute: str = _private_attribute(owner, name)

    def __get__(self, obj: object, objtype: type | None = None, /) -> Any:
        if obj is None:
            return self
        attribute: str = self.__attribute
        try:
            return getattr(obj, attribute)
        except AttributeError as exc:
            name: str = self.__name
            raise UnregisteredOptionError(name) from exc

    def __set__(self, obj: object, value: Any, /) -> None:
        attribute: str = self.__attribute
        return setattr(obj, attribute, value)

    def __delete__(self, obj: object, /) -> None:
        attribute: str = self.__attribute
        try:
            return delattr(obj, attribute)
        except AttributeError as exc:
            name: str = self.__name
            raise UnregisteredOptionError(name) from exc


class _ReadOnlyOptionBuildPayload:
    def __init__(self, default_descriptor: _Descriptor | None = None) -> None:
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
