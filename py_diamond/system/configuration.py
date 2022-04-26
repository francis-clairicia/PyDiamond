# -*- coding: Utf-8 -*
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

import re
from contextlib import ExitStack, contextmanager, nullcontext, suppress
from copy import copy, deepcopy
from enum import Enum
from functools import cache, wraps
from threading import RLock
from types import BuiltinFunctionType, BuiltinMethodType, MappingProxyType, MethodType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    Generic,
    Iterator,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    final,
    overload,
    runtime_checkable,
)
from weakref import ReferenceType as WeakReferenceType, WeakKeyDictionary, ref as weakref

from ._mangling import mangle_private_attribute as _private_attribute

_Func = TypeVar("_Func", bound=Callable[..., Any])
_Updater = TypeVar("_Updater", bound=Callable[[Any], None])
_KeyUpdater = TypeVar("_KeyUpdater", bound=Callable[[Any, str], None])
_ValueUpdater = TypeVar("_ValueUpdater", bound=Callable[[Any, Any], None])
_KeyValueUpdater = TypeVar("_KeyValueUpdater", bound=Callable[[Any, str, Any], None])
_Getter = TypeVar("_Getter", bound=Callable[[Any], Any])
_Setter = TypeVar("_Setter", bound=Callable[[Any, Any], None])
_Deleter = TypeVar("_Deleter", bound=Callable[[Any], None])
_KeyGetter = TypeVar("_KeyGetter", bound=Callable[[Any, str], Any])
_KeySetter = TypeVar("_KeySetter", bound=Callable[[Any, str, Any], None])
_KeyDeleter = TypeVar("_KeyDeleter", bound=Callable[[Any, str], None])
_ValueValidator = TypeVar("_ValueValidator", bound=Callable[[Any, Any], None])
_StaticValueValidator = TypeVar("_StaticValueValidator", bound=Callable[[Any], None])
_ValueConverter = TypeVar("_ValueConverter", bound=Callable[[Any, Any], Any])
_StaticValueConverter = TypeVar("_StaticValueConverter", bound=Callable[[Any], Any])
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


def initializer(func: _Func) -> _Func:
    return _ConfigInitializer(func)  # type: ignore[return-value]


_ALLOWED_OPTIONS_PATTERN = re.compile(r"(?!__)(?:[a-zA-Z]\w*|_\w+)(?<!__)")
_MISSING: Any = object()
_NO_DEFAULT: Any = object()


class ConfigurationTemplate:
    __slots__ = (
        "__template",
        "__no_parent_ownership",
        "__bound_class",
        "__attr_name",
        "__lock",
        "__build",
    )

    def __init__(
        self,
        *known_options: str,
        autocopy: Optional[bool] = None,
        parent: Optional[Union[ConfigurationTemplate, Sequence[ConfigurationTemplate]]] = None,
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
        self.__no_parent_ownership: Set[str] = set()
        self.__bound_class: Optional[type] = None
        self.__attr_name: Optional[str] = None
        self.__lock = RLock()
        self.__build: Optional[ConfigurationInfo] = None

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
        attribute_class_owner: Dict[str, type] = template.attribute_class_owner
        no_parent_ownership: Set[str] = self.__no_parent_ownership
        for option in template.options:
            if option in no_parent_ownership:
                attribute_class_owner[option] = owner
            else:
                attribute_class_owner.setdefault(option, owner)
            descriptor: Optional[_Descriptor] = template.value_descriptors.get(option)
            if descriptor not in template.parent_descriptors and hasattr(descriptor, "__set_name__"):
                getattr(descriptor, "__set_name__")(attribute_class_owner[option], option)
        former_config: Optional[ConfigurationTemplate] = _register_configuration(owner, self)
        for obj in _all_members(owner).values():
            if isinstance(obj, OptionAttribute):
                with suppress(AttributeError):
                    self.check_option_validity(obj.name)
            elif isinstance(obj, ConfigurationTemplate) and obj is not self:
                _register_configuration(owner, former_config)
                raise TypeError(f"A class can't have several {ConfigurationTemplate.__name__!r} objects")
        self.__build = template.build()

    @overload
    def __get__(self, obj: None, objtype: type, /) -> ConfigurationTemplate:
        ...

    @overload
    def __get__(self, obj: _T, objtype: Optional[type] = None, /) -> Configuration[_T]:
        ...

    def __get__(self, obj: Any, objtype: Optional[type] = None, /) -> Union[ConfigurationTemplate, Configuration[Any]]:
        if obj is None:
            if objtype is None:
                raise TypeError("__get__(None, None) is invalid")
            return self
        attr_name = self.__attr_name
        info = self.__build
        bound_class = self.__bound_class
        if not attr_name or info is None or bound_class is None:
            raise TypeError("Cannot use ConfigurationTemplate instance without calling __set_name__ on it.")
        if objtype is None:
            objtype = type(obj)
        elif not isinstance(obj, objtype):
            raise TypeError("Invalid __get__ second argument")
        if not issubclass(objtype, bound_class):
            raise TypeError(f"{objtype.__qualname__} is not a subclass of {bound_class.__qualname__}")
        try:
            objref: WeakReferenceType[Any] = weakref(obj)
        except TypeError:
            return Configuration(obj, info)
        if getattr(objtype, attr_name, None) is not self:
            return Configuration(objref, info)
        try:
            obj_cache = obj.__dict__
        except AttributeError:
            return Configuration(objref, info)
        bound_config: Configuration[Any] = obj_cache.get(attr_name, _MISSING)
        if bound_config is _MISSING:
            with self.__lock:
                bound_config = obj_cache.get(attr_name, _MISSING)
                if bound_config is _MISSING:
                    bound_config = Configuration(objref, info)
                    with suppress(Exception):
                        obj_cache[attr_name] = bound_config
        return bound_config

    def known_options(self) -> FrozenSet[str]:
        return self.__template.options

    def known_aliases(self) -> FrozenSet[str]:
        return frozenset(self.__template.aliases)

    def check_option_validity(self, option: str, *, use_alias: bool = False) -> str:
        template = self.__template
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
    def set_autocopy(self, option: str, /, *, copy_on_get: Optional[bool]) -> None:
        ...

    @overload
    def set_autocopy(self, option: str, /, *, copy_on_set: Optional[bool]) -> None:
        ...

    @overload
    def set_autocopy(self, option: str, /, *, copy_on_get: Optional[bool], copy_on_set: Optional[bool]) -> None:
        ...

    def set_autocopy(self, arg1: Union[bool, str], /, **kwargs: Optional[bool]) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        if isinstance(arg1, bool) and not kwargs:
            template.autocopy = arg1
        elif isinstance(arg1, str) and ("copy_on_get" in kwargs or "copy_on_set" in kwargs):
            self.check_option_validity(arg1)
            if "copy_on_get" in kwargs:
                copy_on_get: Optional[bool] = kwargs["copy_on_get"]
                if copy_on_get is None:
                    template.value_autocopy_get.pop(arg1, None)
                else:
                    template.value_autocopy_get[arg1] = bool(copy_on_get)
            if "copy_on_set" in kwargs:
                copy_on_set: Optional[bool] = kwargs["copy_on_set"]
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
    def getter(self, option: str, /, *, use_override: bool = True, readonly: bool = False) -> Callable[[_Getter], _Getter]:
        ...

    @overload
    def getter(self, option: str, func: _Getter, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    def getter(
        self, option: str, func: Optional[_Getter] = None, /, *, use_override: bool = True, readonly: bool = False
    ) -> Optional[Callable[[_Getter], _Getter]]:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: Optional[_Descriptor] = template.value_descriptors.get(option)
        if not isinstance(actual_descriptor, _ReadOnlyOptionPayload):
            if actual_descriptor is not None and not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            actual_property: Optional[_ConfigProperty] = actual_descriptor
            if (
                actual_property is not None
                and readonly
                and (actual_property.fset is not None or actual_property.fdel is not None)
            ):
                raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")

            def decorator(func: _Getter, /) -> _Getter:
                wrapper = _make_function_wrapper(func, check_override=bool(use_override))
                new_config_property: property
                if actual_property is None:
                    new_config_property = _ConfigProperty(wrapper)
                else:
                    new_config_property = actual_property.getter(wrapper)
                if readonly:
                    template.value_descriptors[option] = _ReadOnlyOptionPayload(new_config_property)
                else:
                    template.value_descriptors[option] = new_config_property
                return func

        else:
            readonly_descriptor: _ReadOnlyOptionPayload = actual_descriptor
            actual_descriptor = readonly_descriptor.get_descriptor()
            if not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            config_property: _ConfigProperty = actual_descriptor

            def decorator(func: _Getter, /) -> _Getter:
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
    ) -> Callable[[_KeyGetter], _KeyGetter]:
        ...

    @overload
    def getter_key(
        self, option: str, /, *, use_key: str, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_KeyGetter], _KeyGetter]:
        ...

    @overload
    def getter_key(self, option: str, func: _KeyGetter, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    @overload
    def getter_key(
        self, option: str, func: _KeyGetter, /, *, use_key: str, use_override: bool = True, readonly: bool = False
    ) -> None:
        ...

    def getter_key(
        self,
        option: str,
        func: Optional[_KeyGetter] = None,
        /,
        *,
        use_key: Optional[str] = None,
        use_override: bool = True,
        readonly: bool = False,
    ) -> Optional[Callable[[_KeyGetter], _KeyGetter]]:
        self.__check_locked()

        def decorator(func: _KeyGetter, /) -> _KeyGetter:
            key: str = use_key or option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.getter(option, _wrap_function_wrapper(func, lambda self: wrapper(self, key)), readonly=readonly)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter(self, option: str, /, *, use_override: bool = True) -> Callable[[_Setter], _Setter]:
        ...

    @overload
    def setter(self, option: str, func: _Setter, /, *, use_override: bool = True) -> None:
        ...

    def setter(
        self, option: str, func: Optional[_Setter] = None, /, *, use_override: bool = True
    ) -> Optional[Callable[[_Setter], _Setter]]:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: Optional[_Descriptor] = template.value_descriptors.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing setter for this option which has no getter")
        if isinstance(actual_descriptor, _ReadOnlyOptionPayload):
            raise OptionError(option, "Read-only option")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _Setter, /) -> _Setter:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            template.value_descriptors[option] = actual_property.setter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeySetter], _KeySetter]:
        ...

    @overload
    def setter_key(self, option: str, /, *, use_key: str, use_override: bool = True) -> Callable[[_KeySetter], _KeySetter]:
        ...

    @overload
    def setter_key(self, option: str, func: _KeySetter, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def setter_key(self, option: str, func: _KeySetter, /, *, use_key: str, use_override: bool = True) -> None:
        ...

    def setter_key(
        self, option: str, func: Optional[_KeySetter] = None, /, *, use_key: Optional[str] = None, use_override: bool = True
    ) -> Optional[Callable[[_KeySetter], _KeySetter]]:
        self.__check_locked()

        def decorator(func: _KeySetter, /) -> _KeySetter:
            key: str = use_key or option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.setter(option, _wrap_function_wrapper(func, lambda self, value: wrapper(self, key, value)))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter(self, option: str, /, *, use_override: bool = True) -> Callable[[_Deleter], _Deleter]:
        ...

    @overload
    def deleter(self, option: str, func: _Deleter, /, *, use_override: bool = True) -> None:
        ...

    def deleter(
        self, option: str, func: Optional[_Deleter] = None, /, *, use_override: bool = True
    ) -> Optional[Callable[[_Deleter], _Deleter]]:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        actual_descriptor: Optional[_Descriptor] = template.value_descriptors.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing deleter for this option which has no getter")
        if isinstance(actual_descriptor, _ReadOnlyOptionPayload):
            raise OptionError(option, "Read-only option")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _Deleter, /) -> _Deleter:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            template.value_descriptors[option] = actual_property.deleter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyDeleter], _KeyDeleter]:
        ...

    @overload
    def deleter_key(self, option: str, /, *, use_key: str, use_override: bool = True) -> Callable[[_KeyDeleter], _KeyDeleter]:
        ...

    @overload
    def deleter_key(self, option: str, func: _KeyDeleter, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def deleter_key(self, option: str, func: _KeyDeleter, /, *, use_key: str, use_override: bool = True) -> None:
        ...

    def deleter_key(
        self, option: str, func: Optional[_KeyDeleter] = None, /, *, use_key: Optional[str] = None, use_override: bool = True
    ) -> Optional[Callable[[_KeyDeleter], _KeyDeleter]]:
        self.__check_locked()

        def decorator(func: _KeyDeleter, /) -> _KeyDeleter:
            key: str = use_key or option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.deleter(option, _wrap_function_wrapper(func, lambda self: wrapper(self, key)))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    def use_descriptor(self, option: str, descriptor: _Descriptor) -> None:
        self.__check_locked()
        self.check_option_validity(option)
        template: _ConfigInfoTemplate = self.__template
        if option in template.value_descriptors:
            actual_descriptor: _Descriptor = template.value_descriptors[option]
            if isinstance(actual_descriptor, _ReadOnlyOptionPayload):
                underlying_descriptor = actual_descriptor.get_descriptor()
                if underlying_descriptor is None:
                    raise OptionError(option, "Already uses custom getter register with getter() method")
                actual_descriptor = underlying_descriptor
            if isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, "Already uses custom getter register with getter() method")
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        template.value_descriptors[option] = descriptor

    @overload
    def add_main_update(self, func: _Updater, /, *, use_override: bool = True) -> _Updater:
        ...

    @overload
    def add_main_update(self, /, *, use_override: bool = True) -> Callable[[_Updater], _Updater]:
        ...

    def add_main_update(
        self, func: Optional[_Updater] = None, /, *, use_override: bool = True
    ) -> Union[_Updater, Callable[[_Updater], _Updater]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        def decorator(func: _Updater, /) -> _Updater:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if wrapper in template.main_updater:
                raise ConfigError("Function already registered")
            template.main_updater.append(wrapper)
            return func

        if func is None:
            return decorator
        return decorator(func)

    @overload
    def on_update(self, option: str, /, *, use_override: bool = True) -> Callable[[_Updater], _Updater]:
        ...

    @overload
    def on_update(self, option: str, func: _Updater, /, *, use_override: bool = True) -> None:
        ...

    def on_update(
        self, option: str, func: Optional[_Updater] = None, /, *, use_override: bool = True
    ) -> Optional[Union[_Updater, Callable[[_Updater], _Updater]]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _Updater, /) -> _Updater:
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
    def on_update_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyUpdater], _KeyUpdater]:
        ...

    @overload
    def on_update_key(self, option: str, /, *, use_key: str, use_override: bool = True) -> Callable[[_KeyUpdater], _KeyUpdater]:
        ...

    @overload
    def on_update_key(self, option: str, func: _KeyUpdater, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_key(self, option: str, func: _KeyUpdater, /, *, use_key: str, use_override: bool = True) -> None:
        ...

    def on_update_key(
        self, option: str, func: Optional[_KeyUpdater] = None, /, *, use_key: Optional[str] = None, use_override: bool = True
    ) -> Optional[Callable[[_KeyUpdater], _KeyUpdater]]:
        self.__check_locked()

        def decorator(func: _KeyUpdater, /) -> _KeyUpdater:
            key: str = use_key or option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.on_update(option, _wrap_function_wrapper(func, lambda self: wrapper(self, key)))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_value(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueUpdater], _ValueUpdater]:
        ...

    @overload
    def on_update_value(self, option: str, func: _ValueUpdater, /, *, use_override: bool = True) -> None:
        ...

    def on_update_value(
        self, option: str, func: Optional[_ValueUpdater] = None, /, *, use_override: bool = True
    ) -> Optional[Callable[[_ValueUpdater], _ValueUpdater]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _ValueUpdater, /) -> _ValueUpdater:
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
    def on_update_key_value(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyValueUpdater], _KeyValueUpdater]:
        ...

    @overload
    def on_update_key_value(
        self, option: str, /, *, use_key: str, use_override: bool = True
    ) -> Callable[[_KeyValueUpdater], _KeyValueUpdater]:
        ...

    @overload
    def on_update_key_value(self, option: str, func: _KeyValueUpdater, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_key_value(self, option: str, func: _KeyValueUpdater, /, *, use_key: str, use_override: bool = True) -> None:
        ...

    def on_update_key_value(
        self, option: str, func: Optional[_KeyValueUpdater] = None, /, *, use_key: Optional[str] = None, use_override: bool = True
    ) -> Optional[Callable[[_KeyValueUpdater], _KeyValueUpdater]]:
        self.__check_locked()

        def decorator(func: _KeyValueUpdater, /) -> _KeyValueUpdater:
            key: str = use_key or option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.on_update_value(option, _wrap_function_wrapper(func, lambda self, value: wrapper(self, key, value)))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_value_validator(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueValidator], _ValueValidator]:
        ...

    @overload
    def add_value_validator(self, option: str, func: _ValueValidator, /, *, use_override: bool = True) -> None:
        ...

    def add_value_validator(
        self,
        option: str,
        func: Optional[_ValueValidator] = None,
        /,
        *,
        use_override: bool = True,
    ) -> Optional[Callable[[_ValueValidator], _ValueValidator]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use value_validator_static() to check types")

        def decorator(func: _ValueValidator, /) -> _ValueValidator:
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
    def add_value_validator_static(self, option: str, /) -> Callable[[_StaticValueValidator], _StaticValueValidator]:
        ...

    @overload
    def add_value_validator_static(self, option: str, objtype: type, /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_validator_static(self, option: str, objtypes: Sequence[type], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_validator_static(self, option: str, func: _StaticValueValidator, /) -> None:
        ...

    def add_value_validator_static(
        self,
        option: str,
        func: Optional[Union[_StaticValueValidator, type, Sequence[type]]] = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Optional[Callable[[_StaticValueValidator], _StaticValueValidator]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _StaticValueValidator, /) -> _StaticValueValidator:
            value_validator_list = template.value_validator.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=False, no_object=True)
            if wrapper in value_validator_list:
                raise OptionError(option, "Function already registered")
            value_validator_list.append(wrapper)
            return func

        if isinstance(func, (type, Sequence)):
            _type: Union[type, Tuple[type, ...]] = func if isinstance(func, type) else tuple(func)

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
    def add_value_converter(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueConverter], _ValueConverter]:
        ...

    @overload
    def add_value_converter(self, option: str, func: _ValueConverter, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter(
        self,
        option: str,
        func: Optional[_ValueConverter] = None,
        /,
        *,
        use_override: bool = True,
    ) -> Optional[Callable[[_ValueConverter], _ValueConverter]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use value_converter_static() to convert value using type")

        def decorator(func: _ValueConverter) -> _ValueConverter:
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
    def add_value_converter_static(self, option: str, /) -> Callable[[_StaticValueConverter], _StaticValueConverter]:
        ...

    @overload
    def add_value_converter_static(self, option: str, convert_to_type: Type[Any], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def add_value_converter_static(self, option: str, func: _StaticValueConverter, /) -> None:
        ...

    def add_value_converter_static(
        self, option: str, func: Optional[Union[_StaticValueConverter, type]] = None, /, *, accept_none: bool = False
    ) -> Optional[Callable[[_StaticValueConverter], _StaticValueConverter]]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        def decorator(func: _StaticValueConverter, /) -> _StaticValueConverter:
            value_converter_list = template.value_converter.setdefault(option, [])
            wrapper = _make_function_wrapper(func, check_override=False, no_object=True)
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)
            return func

        if isinstance(func, type):

            if issubclass(func, Enum):
                if option in template.enum_converter_registered:
                    enum = template.enum_converter_registered[option]
                    raise ValueError(f"Enum converter already set for option {option!r}: {enum.__qualname__!r}")
                enum = func
                template.enum_converter_registered[option] = enum

            value_converter: Any = _make_value_converter(func, accept_none)

            decorator(value_converter)
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def add_enum_converter(self, option: str, enum: Type[Enum], *, store_value: bool = False) -> None:
        ...

    @overload
    def add_enum_converter(self, option: str, enum: Type[Enum], *, return_value_on_get: bool) -> None:
        ...

    def add_enum_converter(self, option: str, enum: Type[Enum], **kwargs: bool) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)

        if not issubclass(enum, Enum):
            raise TypeError("Not an Enum class")

        if "store_value" in kwargs and "return_value_on_get" in kwargs:
            raise TypeError("Invalid arguments")

        store_value: bool = kwargs.pop("store_value", False)
        return_value_on_get: Optional[bool] = kwargs.pop("return_value_on_get", None)

        if kwargs:
            raise TypeError("Invalid arguments")

        if option in template.enum_converter_registered:
            enum = template.enum_converter_registered[option]
            raise ValueError(f"Enum converter already set for option {option!r}: {enum.__qualname__!r}")

        self.add_value_converter_static(option, _make_enum_converter(enum, store_value=store_value))
        template.enum_converter_registered[option] = enum
        if return_value_on_get is not None:
            template.enum_return_value[option] = bool(return_value_on_get)

    def set_alias(self, option: str, alias: str, /, *aliases: str) -> None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template
        self.check_option_validity(option)
        for alias in set((alias, *aliases)):
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
            descriptor: Optional[_Descriptor] = template.value_descriptors.get(option)
            if isinstance(descriptor, _ReadOnlyOptionPayload):
                continue
            if isinstance(descriptor, (_MutableDescriptor, _RemovableDescriptor)):
                if not isinstance(descriptor, property) or descriptor.fset is not None or descriptor.fdel is not None:
                    raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            template.value_descriptors[option] = _ReadOnlyOptionPayload()

    def __check_locked(self) -> None:
        if self.__bound_class is not None:
            raise TypeError(f"Attempt to modify template after the class creation")

    @property
    @final
    def owner(self) -> Optional[type]:
        return self.__bound_class

    @property
    @final
    def name(self) -> Optional[str]:
        return self.__attr_name


class OptionAttribute(Generic[_T]):

    __slots__ = ("__name", "__config_name", "__doc__")

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
        config: ConfigurationTemplate = _retrieve_configuration(owner)
        if config.name is None:
            raise TypeError("OptionAttribute must be declared after the ConfigurationTemplate object")
        config.check_option_validity(name, use_alias=True)
        self.__config_name: str = config.name

    @overload
    def __get__(self, obj: None, objtype: type, /) -> OptionAttribute[_T]:
        ...

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> _T:
        ...

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Union[_T, OptionAttribute[_T]]:
        if obj is None:
            return self
        name: str = self.__name
        config: Configuration[Any] = getattr(obj, self.__config_name)
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


@final
class ConfigurationInfo(NamedTuple):
    options: FrozenSet[str]
    option_value_updater: Mapping[str, Callable[[object, Any], None]]
    option_updater: Mapping[str, Callable[[object], None]]
    many_options_updater: Optional[Callable[[object, Sequence[str]], None]]
    main_updater: Optional[Callable[[object], None]]
    value_converter: Mapping[str, Callable[[object, Any], Any]]
    value_validator: Mapping[str, Callable[[object, Any], None]]
    value_descriptors: Mapping[str, _Descriptor]
    autocopy: bool
    value_autocopy_get: Mapping[str, bool]
    value_autocopy_set: Mapping[str, bool]
    attribute_class_owner: Mapping[str, type]
    aliases: Mapping[str, str]
    value_copy: Mapping[type, Callable[[Any], Any]]
    value_copy_allow_subclass: Mapping[type, bool]
    readonly_options: FrozenSet[str]
    enum_return_value: FrozenSet[str]

    class __ReadOnlyOptionWrapper:  # type: ignore[misc]
        def __init__(self, default_descriptor: _Descriptor) -> None:
            self.__descriptor: Callable[[], _Descriptor] = lambda: default_descriptor

        def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Any:
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
        descriptor: Optional[_Descriptor] = self.value_descriptors.get(option, None)
        if descriptor is None:
            descriptor = _PrivateAttributeOptionProperty()
            descriptor.__set_name__(self.attribute_class_owner.get(option, objtype), option)
        if option in self.readonly_options:
            descriptor = self.__ReadOnlyOptionWrapper(descriptor)
        return descriptor

    def get_copy_func(self, cls: type) -> Callable[[Any], Any]:
        try:
            return self.value_copy[cls]
        except KeyError:
            if self.value_copy_allow_subclass.get(cls, False):
                for _type, func in self.value_copy.items():
                    if issubclass(cls, _type):
                        return func
        return _copy_object


_InitializationRegister = Dict[str, Any]
_UpdateRegister = List[str]


class Configuration(Generic[_T]):
    __update_stack: ClassVar[Dict[object, List[str]]] = dict()
    __init_context: ClassVar[Dict[object, _InitializationRegister]] = dict()
    __update_context: ClassVar[Dict[object, _UpdateRegister]] = dict()
    __lock_cache: ClassVar[WeakKeyDictionary[object, RLock]] = WeakKeyDictionary()
    __default_lock: ClassVar[RLock] = RLock()

    __slots__ = ("__info", "__obj")

    class __OptionUpdateContext(NamedTuple):
        first_update: bool
        init_context: Optional[_InitializationRegister]
        updated: _UpdateRegister

    __DELETED: Any = object()

    def __init__(self, obj: Union[_T, WeakReferenceType[_T]], info: ConfigurationInfo) -> None:
        self.__obj: Callable[[], Optional[_T]] = obj if isinstance(obj, WeakReferenceType) else lambda obj=obj: obj  # type: ignore[misc]
        self.__info: ConfigurationInfo = info

    def __repr__(self) -> str:
        option_dict = self.as_dict()
        return f"{type(self).__name__}({', '.join(f'{k}={option_dict[k]!r}' for k in sorted(option_dict))})"

    def __contains__(self, option: str) -> bool:
        try:
            self.get(option)
        except (AttributeError, OptionError):
            return False
        return True

    @overload
    def get(self, option: str) -> Any:
        ...

    @overload
    def get(self, option: str, default: _DT) -> Union[Any, _DT]:
        ...

    def get(self, option: str, default: Any = _NO_DEFAULT) -> Any:
        obj: _T = self.__self__
        info: ConfigurationInfo = self.__info
        option = info.check_option_validity(option, use_alias=True)
        descriptor = info.get_value_descriptor(option, type(obj))
        with self.__lazy_lock(obj):
            try:
                value: Any = descriptor.__get__(obj, type(obj))
            except (AttributeError, UnregisteredOptionError):
                if default is _NO_DEFAULT:
                    raise
                return default
            if option in info.enum_return_value and isinstance(value, Enum):
                return value.value
            if info.value_autocopy_get.get(option, info.autocopy):
                copy_func = info.get_copy_func(type(value))
                with suppress(Exception):
                    value = copy_func(value)
            return value

    def __getitem__(self, option: str, /) -> Any:
        try:
            return self.get(option)
        except OptionError as exc:
            raise KeyError(option) from exc

    def as_dict(self, *, sorted_keys: bool = False) -> Dict[str, Any]:
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

        with self.__updating_option(obj, option, info) as update_context:
            value_validator: Optional[Callable[[object, Any], None]] = info.value_validator.get(option, None)
            value_converter: Optional[Callable[[object, Any], Any]] = info.value_converter.get(option, None)
            if value_validator is not None:
                value_validator(obj, value)
            converter_applied: bool = False
            if value_converter is not None:
                value = value_converter(obj, value)
                converter_applied = True

            try:
                actual_value = descriptor.__get__(obj, type(obj))
            except (AttributeError, UnregisteredOptionError):
                pass
            else:
                if actual_value is value or actual_value == value:
                    return

            if not converter_applied and info.value_autocopy_set.get(option, info.autocopy):
                copy_func = info.get_copy_func(type(value))
                with suppress(Exception):
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

        with self.__updating_option(obj, option, info) as update_context:
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
        with self.__updating_many_options(obj, *options, info=self.__info):
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
                            if option in update_register:
                                raise OptionError(option, "Value modified after update in initialization context")
                    many_options_updater = info.many_options_updater
                    if many_options_updater is not None:
                        many_options_updater(obj, tuple(initialization_register))
                        if update_register:
                            raise OptionError("", "Options were modified after update in initialization context")
                    else:
                        for option in initialization_register:
                            option_updater = info.option_updater.get(option, None)
                            if option_updater is not None:
                                option_updater(obj)
                                if option in update_register:
                                    raise OptionError(option, "Value modified after update in initialization context")
                    main_updater = info.main_updater
                    if main_updater is not None:
                        main_updater(obj)
                        if update_register:
                            raise OptionError("", "Options were modified after update in initialization context")

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

    @property
    @final
    def info(self) -> ConfigurationInfo:
        return self.__info

    @property
    @final
    def __self__(self) -> _T:
        obj: Optional[_T] = self.__obj()
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
        with Configuration.__updating_many_options(obj, *options, info=info, call_updaters=False):
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
            if many_options_updater is not None:
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

        with Configuration.__updating_option(obj, option, info, call_updaters=False):
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
        obj: object, option: str, info: ConfigurationInfo, *, call_updaters: bool = True
    ) -> Iterator[__OptionUpdateContext]:
        UpdateContext = Configuration.__OptionUpdateContext

        with Configuration.__lazy_lock(obj):
            register = Configuration.__init_context.get(obj, None)
            if register is not None:
                yield UpdateContext(first_update=False, init_context=register, updated=[])
                return

            update_register: _UpdateRegister = Configuration.__update_context.setdefault(obj, [])
            update_stack: List[str] = Configuration.__update_stack.setdefault(obj, [])
            if option in update_stack:
                yield UpdateContext(first_update=False, init_context=None, updated=update_register)
                return

            def cleanup() -> None:
                with suppress(ValueError):
                    update_stack.remove(option)
                if not update_stack:
                    Configuration.__update_stack.pop(obj, None)

            update_stack.append(option)
            with ExitStack() as stack:
                stack.callback(cleanup)
                yield UpdateContext(first_update=True, init_context=None, updated=update_register)
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
        obj: object, *options: str, info: ConfigurationInfo, call_updaters: bool = True
    ) -> Iterator[None]:
        nb_options = len(options)
        if nb_options < 1:
            yield
            return

        with Configuration.__lazy_lock(obj):
            if obj in Configuration.__init_context:
                yield
                return
            if nb_options == 1:
                with Configuration.__updating_option(obj, options[0], info):
                    yield
                return
            with ExitStack() as stack:
                for option in options:
                    stack.enter_context(Configuration.__updating_option(obj, option, info, call_updaters=call_updaters))
                yield

    @staticmethod
    def __lazy_lock(obj: object) -> Union[RLock, nullcontext[None]]:
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


def _no_type_check_cache(func: _Func) -> _Func:
    return cache(func)  # type: ignore[return-value]


@_no_type_check_cache
def _make_function_wrapper(func: Any, *, check_override: bool = True, no_object: bool = False) -> Callable[..., Any]:
    if getattr(func, "__boundconfiguration_wrapper__", False):
        return cast(Callable[..., Any], func)

    if isinstance(func, (BuiltinFunctionType, BuiltinMethodType)):
        no_object = True
    if callable(func) and not _can_be_overriden(func):
        check_override = False

    if no_object:

        if callable(func):

            @wraps(func)
            def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                return func(*args, **kwargs)

        elif check_override:

            @wraps(func)
            def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                _func: Callable[..., Any] = getattr(func, "__get__", lambda *args: func)(self, type(self))
                if _can_be_overriden(_func):
                    _func = getattr(self, _func.__name__, _func)
                return _func(*args, **kwargs)

        else:

            @wraps(func)
            def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
                _func: Callable[..., Any] = getattr(func, "__get__", lambda *args: func)(self, type(self))
                return _func(*args, **kwargs)

    elif check_override:

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            _func: Callable[..., Any]
            _func = getattr(func, "__get__", lambda *args: func)(self, type(self))
            if _func is func:
                _func = MethodType(func, self)
            if _can_be_overriden(_func):
                _func = getattr(self, _func.__name__, _func)
            return _func(*args, **kwargs)

    else:

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            _func: Callable[..., Any]
            _func = getattr(func, "__get__", lambda *args: func)(self, type(self))
            if _func is func:
                _func = MethodType(func, self)
            return _func(*args, **kwargs)

    setattr(wrapper, "__boundconfiguration_wrapper__", True)
    return wrapper


_LAMBDA_FUNC_NAME = (lambda: None).__name__


def _can_be_overriden(func: Callable[..., Any]) -> bool:
    try:
        name: str = func.__name__
    except AttributeError:
        return False
    if name == _LAMBDA_FUNC_NAME:
        return False
    if name.startswith("__"):
        return name.endswith("__")
    return True


@_no_type_check_cache
def _wrap_function_wrapper(func: Any, wrapper: Callable[..., Any]) -> Callable[..., Any]:
    wrap_decorator = wraps(func)
    wrapper = wrap_decorator(wrapper)
    setattr(wrapper, "__boundconfiguration_wrapper__", True)
    return wrapper


@_no_type_check_cache
def _make_type_checker(_type: Union[type, Tuple[type, ...]], accept_none: bool) -> Callable[[Any], None]:
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
def _make_enum_converter(enum: Type[Enum], store_value: bool) -> Callable[[Any], Any]:
    if not store_value:

        def value_converter(val: Any, /, *, enum: Type[Enum] = enum) -> Any:
            val = enum(val)
            return val

    else:

        def value_converter(val: Any, /, *, enum: Type[Enum] = enum) -> Any:
            val = enum(val)
            return val.value

    return value_converter


def _get_cls_mro(cls: type) -> List[type]:
    try:
        mro: List[type] = list(getattr(cls, "__mro__"))
    except AttributeError:

        def getmro(cls: type) -> List[type]:
            mro = [cls]
            for base in cls.__bases__:
                mro.extend(getmro(base))
            return mro

        mro = getmro(cls)
    return mro


if not TYPE_CHECKING:
    try:
        from inspect import getmro as _inspect_get_mro
    except ImportError:
        pass
    else:

        def _get_cls_mro(cls: type) -> List[type]:
            return list(_inspect_get_mro(cls))


def _all_members(cls: type) -> Dict[str, Any]:
    mro: List[type] = _get_cls_mro(cls)
    mro.reverse()
    members: Dict[str, Any] = dict()
    for cls in mro:
        members.update(vars(cls))
    return members


def _register_configuration(cls: type, config: Optional[ConfigurationTemplate]) -> Optional[ConfigurationTemplate]:
    if not isinstance(cls, type):
        raise TypeError(f"{cls} is not a type")
    former_config: Optional[ConfigurationTemplate] = None
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
    def __get__(self, __obj: object, __objtype: Optional[type], /) -> Any:
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
    def __init__(self, known_options: Sequence[str], autocopy: Optional[bool], parents: Sequence[_ConfigInfoTemplate]) -> None:
        self.options: FrozenSet[str] = frozenset(known_options)
        self.main_updater: List[Callable[[object], None]] = list()
        self.option_updater: Dict[str, List[Callable[[object], None]]] = dict()
        self.option_value_updater: Dict[str, List[Callable[[object, Any], None]]] = dict()
        self.value_descriptors: Dict[str, _Descriptor] = dict()
        self.value_converter: Dict[str, List[Callable[[object, Any], Any]]] = dict()
        self.value_validator: Dict[str, List[Callable[[object, Any], None]]] = dict()
        self.autocopy: bool = bool(autocopy) if autocopy is not None else False
        self.value_autocopy_get: Dict[str, bool] = dict()
        self.value_autocopy_set: Dict[str, bool] = dict()
        self.attribute_class_owner: Dict[str, type] = dict()
        self.aliases: Dict[str, str] = dict()
        self.value_copy: Dict[type, Callable[[Any], Any]] = dict()
        self.value_copy_allow_subclass: Dict[type, bool] = dict()
        self.enum_converter_registered: Dict[str, type[Enum]] = dict()
        self.enum_return_value: Dict[str, bool] = dict()

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

        self.parent_descriptors: FrozenSet[_Descriptor] = frozenset(self.value_descriptors.values())

    @staticmethod
    def __merge_dict(
        d1: Dict[_KT, _VT],
        d2: Dict[_KT, _VT],
        /,
        *,
        on_conflict: Union[Literal["override", "raise", "skip"], Callable[[_KT, _VT, _VT], _VT]],
        setting: str,
        copy: Optional[Callable[[_VT], _VT]] = None,
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
        l1: List[_T],
        l2: List[_T],
        /,
        *,
        on_duplicate: Literal["keep", "put_at_end", "raise", "skip"],
        setting: str,
        copy: Optional[Callable[[_T], _T]] = None,
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
        d1: Dict[str, List[_Func]],
        d2: Dict[str, List[_Func]],
        /,
        *,
        setting: str,
    ) -> None:
        merge_list = cls.__merge_list
        for key, l2 in d2.items():
            l1 = d1.setdefault(key, [])
            merge_list(l1, l2, on_duplicate="skip", setting=setting)

    def build(self) -> ConfigurationInfo:
        options: FrozenSet[str] = self.options.copy()
        option_value_updater: Mapping[str, Callable[[object, Any], None]] = self.__build_option_value_updater_dict()
        option_updater: Mapping[str, Callable[[object], None]] = self.__build_option_updater_dict()
        many_options_updater: Optional[Callable[[object, Sequence[str]], None]] = self.__build_many_options_updater()
        main_updater: Optional[Callable[[object], None]] = self.__build_main_updater()
        value_converter: Mapping[str, Callable[[object, Any], Any]] = self.__build_value_converter_dict()
        value_validator: Mapping[str, Callable[[object, Any], None]] = self.__build_value_validator_dict()
        value_descriptors: Mapping[str, _Descriptor] = self.__build_value_descriptor_dict()
        autocopy: bool = bool(self.autocopy)
        value_autocopy_get: Mapping[str, bool] = MappingProxyType(self.value_autocopy_get.copy())
        value_autocopy_set: Mapping[str, bool] = MappingProxyType(self.value_autocopy_set.copy())
        attribute_class_owner: Mapping[str, type] = MappingProxyType(self.attribute_class_owner.copy())
        aliases: Mapping[str, str] = MappingProxyType(self.aliases.copy())
        value_copy: Mapping[type, Callable[[Any], Any]] = MappingProxyType(self.value_copy.copy())
        value_copy_allow_subclass: Mapping[type, bool] = MappingProxyType(self.value_copy_allow_subclass.copy())
        readonly_options: FrozenSet[str] = self.__build_readonly_options_set()
        enum_return_value: FrozenSet[str] = self.__build_enum_return_value_set()

        return ConfigurationInfo(
            options=options,
            option_value_updater=option_value_updater,
            option_updater=option_updater,
            many_options_updater=many_options_updater,
            main_updater=main_updater,
            value_converter=value_converter,
            value_validator=value_validator,
            value_descriptors=value_descriptors,
            autocopy=autocopy,
            value_autocopy_get=value_autocopy_get,
            value_autocopy_set=value_autocopy_set,
            attribute_class_owner=attribute_class_owner,
            aliases=aliases,
            value_copy=value_copy,
            value_copy_allow_subclass=value_copy_allow_subclass,
            readonly_options=readonly_options,
            enum_return_value=enum_return_value,
        )

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

    def __build_main_updater(self) -> Optional[Callable[[object], None]]:
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

    def __build_many_options_updater(self) -> Optional[Callable[[object, Sequence[str]], None]]:
        main_updater_list = self.main_updater
        option_updater_dict = {
            option: filtered_updater_list
            for option, updater_list in self.option_updater.items()
            if len((filtered_updater_list := [f for f in updater_list if f not in main_updater_list])) > 0
        }
        if len(option_updater_dict) < 2:
            return None

        merge_list = _ConfigInfoTemplate.__merge_list

        def many_options_updater_func(
            obj: object,
            options: Sequence[str],
            /,
            *,
            option_updater_dict: Dict[str, List[Callable[[object], None]]] = option_updater_dict,
        ) -> None:
            updater_list: List[Callable[[object], None]] = []
            for option in options:
                merge_list(updater_list, option_updater_dict.get(option, []), on_duplicate="skip", setting="")
            for updater in updater_list:
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
        value_descriptors: Dict[str, _Descriptor] = {}

        for option, descriptor in self.value_descriptors.items():
            if isinstance(descriptor, _ReadOnlyOptionPayload):
                underlying_descriptor = descriptor.get_descriptor()
                if underlying_descriptor is None:
                    continue
                descriptor = underlying_descriptor
            value_descriptors[option] = descriptor

        return MappingProxyType(value_descriptors)

    def __build_readonly_options_set(self) -> FrozenSet[str]:
        return frozenset(
            option for option, descriptor in self.value_descriptors.items() if isinstance(descriptor, _ReadOnlyOptionPayload)
        )

    def __build_enum_return_value_set(self) -> FrozenSet[str]:
        return frozenset(option for option, value in self.enum_return_value.items() if value)


def _copy_object(obj: _T) -> _T:
    try:
        return deepcopy(obj)
    except Exception:
        return copy(obj)


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

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Callable[..., Any]:
        config_initializer = self.__make_initializer()
        method_func: Callable[..., Any] = getattr(config_initializer, "__get__")(obj, objtype)
        return method_func

    def __make_initializer(self) -> Callable[..., Any]:
        init_func: Callable[..., Any] = self.__func__
        func_get: Callable[[object, Optional[type]], Callable[..., Any]] = getattr(init_func, "__get__")

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


class _PrivateAttributeOptionProperty:
    def __set_name__(self, owner: type, name: str, /) -> None:
        self.__owner: type = owner
        self.__name: str = name

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Any:
        if obj is None:
            return self
        attribute: str = _private_attribute(self.__owner, self.__name)
        try:
            return getattr(obj, attribute)
        except AttributeError as exc:
            name: str = self.__name
            raise UnregisteredOptionError(name) from exc

    def __set__(self, obj: object, value: Any, /) -> None:
        attribute: str = _private_attribute(self.__owner, self.__name)
        return setattr(obj, attribute, value)

    def __delete__(self, obj: object, /) -> None:
        attribute: str = _private_attribute(self.__owner, self.__name)
        try:
            return delattr(obj, attribute)
        except AttributeError as exc:
            name: str = self.__name
            raise UnregisteredOptionError(name) from exc


class _ReadOnlyOptionPayload:
    def __init__(self, default_descriptor: Optional[_Descriptor] = None) -> None:
        self.__descriptor: Callable[[], Optional[_Descriptor]]
        self.set_new_descriptor(default_descriptor)

    def __set_name__(self, owner: type, name: str, /) -> None:
        descriptor: Any = self.__descriptor()
        if hasattr(descriptor, "__set_name__"):
            getattr(descriptor, "__set_name__")(owner, name)

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Any:
        raise TypeError("Cannot be used at runtime")

    def get_descriptor(self) -> Optional[_Descriptor]:
        return self.__descriptor()

    def set_new_descriptor(self, descriptor: Optional[_Descriptor]) -> None:
        self.__descriptor = lambda: descriptor


del (
    _Func,
    _Updater,
    _KeyUpdater,
    _ValueUpdater,
    _KeyValueUpdater,
    _Getter,
    _Setter,
    _Deleter,
    _KeyGetter,
    _KeySetter,
    _KeyDeleter,
    _ValueValidator,
    _StaticValueValidator,
    _ValueConverter,
    _StaticValueConverter,
    _T,
    _DT,
    _KT,
    _VT,
)
