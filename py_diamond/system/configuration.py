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
    "Section",
    "SectionError",
    "SectionProperty",
    "UnknownOptionError",
    "UnknownSectionError",
    "UnregisteredOptionError",
    "initializer",
]

import inspect
import re
import reprlib
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
    Literal,
    Mapping,
    MutableMapping,
    NamedTuple,
    NoReturn,
    Protocol,
    Sequence,
    TypeAlias,
    TypeGuard,
    TypeVar,
    cast,
    overload,
    runtime_checkable,
)
from weakref import WeakKeyDictionary, ref as weakref

from .non_copyable import NonCopyable
from .object import Object, final
from .utils._mangling import mangle_private_attribute as _private_attribute
from .utils.itertools import prepend

_Func: TypeAlias = Callable[..., Any]
_Updater: TypeAlias = Callable[[Any], None]
_KeyUpdater: TypeAlias = Callable[[Any, Any], None]
_ValueUpdater: TypeAlias = Callable[[Any, Any], None]
_KeyValueUpdater: TypeAlias = Callable[[Any, Any, Any], None]
_Getter: TypeAlias = Callable[[Any], Any]
_Setter: TypeAlias = Callable[[Any, Any], None]
_Deleter: TypeAlias = Callable[[Any], None]
_KeyGetter: TypeAlias = Callable[[Any, Any], Any]
_KeySetter: TypeAlias = Callable[[Any, Any, Any], None]
_KeyDeleter: TypeAlias = Callable[[Any, Any], None]
_ValueValidator: TypeAlias = Callable[[Any, Any], None]
_StaticValueValidator: TypeAlias = Callable[[Any], None]
_ValueConverter: TypeAlias = Callable[[Any, Any], Any]
_StaticValueConverter: TypeAlias = Callable[[Any], Any]

_FuncVar = TypeVar("_FuncVar", bound=_Func)
_UpdaterVar = TypeVar("_UpdaterVar", bound=_Updater)
_KeyUpdaterVar = TypeVar("_KeyUpdaterVar", bound=_KeyUpdater)
_ValueUpdaterVar = TypeVar("_ValueUpdaterVar", bound=_ValueUpdater)
_KeyValueUpdaterVar = TypeVar("_KeyValueUpdaterVar", bound=_KeyValueUpdater)
_GetterVar = TypeVar("_GetterVar", bound=_Getter)
_SetterVar = TypeVar("_SetterVar", bound=_Setter)
_DeleterVar = TypeVar("_DeleterVar", bound=_Deleter)
_KeyGetterVar = TypeVar("_KeyGetterVar", bound=_KeyGetter)
_KeySetterVar = TypeVar("_KeySetterVar", bound=_KeySetter)
_KeyDeleterVar = TypeVar("_KeyDeleterVar", bound=_KeyDeleter)
_ValueValidatorVar = TypeVar("_ValueValidatorVar", bound=_ValueValidator)
_StaticValueValidatorVar = TypeVar("_StaticValueValidatorVar", bound=_StaticValueValidator)
_ValueConverterVar = TypeVar("_ValueConverterVar", bound=_ValueConverter)
_StaticValueConverterVar = TypeVar("_StaticValueConverterVar", bound=_StaticValueConverter)

_S = TypeVar("_S")
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


class SectionError(OptionError):
    pass


class UnknownOptionError(OptionError):
    def __init__(self, name: str, message: str = "") -> None:
        if not message:
            if name:
                message = "Unknown config option"
            else:
                message = "Empty string given"
        super().__init__(name, message)


class UnknownSectionError(SectionError):
    def __init__(self, name: str, message: str = "") -> None:
        if not message:
            if name:
                message = "Unknown config section"
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


_ALLOWED_OPTIONS_PATTERN = re.compile(r"^(?!__)(?:[a-zA-Z]\w*|_\w+)(?<!__)$")
_ALLOWED_ALIASES_PATTERN = _ALLOWED_OPTIONS_PATTERN
_ALLOWED_SECTIONS_PATTERN = _ALLOWED_OPTIONS_PATTERN
_OPTIONS_IN_SECTION_FMT = "{section}.{option}"
_OPTIONS_IN_SECTION_PATTERN = re.compile(r"^(?P<section>\w+)\.(?P<option>(?:\w+\.)*\w+)$")
_EXCLUDE_SECTION_PATTERN = re.compile(r"^(?P<section>\w+)\.(?P<subsection>(?:\w+\.)*\*)$")
_NO_DEFAULT: Any = object()


@final
class ConfigurationTemplate(Object):
    __slots__ = (
        "__template",
        "__bound_class",
        "__attr_name",
        "__cache",
        "__cache_lock",
        "__info",
    )

    def __init__(
        self,
        *known_options: str,
        parent: ConfigurationTemplate | Sequence[ConfigurationTemplate] | None = None,
    ) -> None:
        for option in known_options:
            if not option:
                raise ValueError("Configuration option must not be empty")
            if not _ALLOWED_OPTIONS_PATTERN.match(option):
                if option.startswith("__") or option.endswith("__"):
                    raise ValueError(f"{option!r}: Only one leading/trailing underscore is accepted")
                raise ValueError(f"{option!r}: Forbidden option format")
        if parent is None:
            parent = []
        elif isinstance(parent, ConfigurationTemplate):
            parent = [parent]

        if not all(p1.name == p2.name for p1, p2 in combinations(parent, r=2)):
            raise AttributeError("Parents' ConfigurationTemplate name mismatch")

        self.__template: _ConfigInfoTemplate = _ConfigInfoTemplate(known_options, [p.__template for p in parent])
        self.__bound_class: type | None = None
        self.__attr_name: str | None = parent[0].name if parent else None
        self.__cache: WeakKeyDictionary[Any, Configuration[Any]] = WeakKeyDictionary()
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
            match obj:
                case OptionAttribute(name=option_name, owner=option_owner) if option_owner is not owner:
                    new_option_attribute: OptionAttribute[Any] = OptionAttribute()
                    new_option_attribute.__doc__ = obj.__doc__
                    setattr(owner, option_name, new_option_attribute)
                    new_option_attribute.__set_name__(owner, option_name)
                case SectionProperty(name=section_name, owner=section_owner) if section_owner is not owner:
                    new_section_attribute: SectionProperty[Any] = SectionProperty()
                    new_section_attribute.__doc__ = obj.__doc__
                    setattr(owner, section_name, new_section_attribute)
                    new_section_attribute.__set_name__(owner, section_name)
                case ConfigurationTemplate() if obj is not self:
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

        try:
            return self.__cache[obj]
        except KeyError:
            pass

        with self.__cache_lock:
            try:
                return self.__cache[obj]
            except KeyError:  # Not added by another thread
                self.__cache[obj] = bound_config = Configuration(weakref(obj), self.info)
                return bound_config

    def __set__(self, obj: _T, value: Configuration[_T]) -> NoReturn:
        raise AttributeError("Read-only attribute")

    def __delete__(self, obj: Any) -> NoReturn:
        raise AttributeError("Read-only attribute")

    def known_options(self) -> frozenset[str]:
        return self.__template.options

    def known_aliases(self) -> frozenset[str]:
        return frozenset(self.__template.aliases)

    def check_option_validity(self, option: str, *, use_alias: bool = False) -> None:
        template = self.__template
        if not isinstance(option, str):
            raise TypeError(f"Expected str, got {type(option).__qualname__}")
        if use_alias:
            option = template.aliases.get(option, option)
        if option not in template.options:
            raise UnknownOptionError(option)

    def is_option_valid(self, option: str, *, use_alias: bool = False) -> bool:
        try:
            self.check_option_validity(option, use_alias=use_alias)
        except UnknownOptionError:
            return False
        return True

    def check_section_validity(self, section: str) -> None:
        template = self.__template
        if section not in template.sections:
            raise UnknownSectionError(section)

    def is_section_valid(self, section: str) -> bool:
        try:
            self.check_section_validity(section)
        except UnknownSectionError:
            return False
        return True

    def add_section(
        self,
        name: str,
        config_getter: Callable[[Any], Configuration[Any]],
        *,
        include_options: Set[str] | None = None,
        exclude_options: Set[str] | None = None,
    ) -> None:
        self.__check_locked()
        template = self.__template

        if not name:
            raise ValueError("Empty string section")
        if not _ALLOWED_SECTIONS_PATTERN.match(name):
            if name.startswith("__") or name.endswith("__"):
                raise ValueError(f"{name!r}: Only one leading/trailing underscore is accepted")
            raise ValueError(f"{name!r}: Forbidden section format")
        if name in template.options:
            raise ConfigurationError("Already have an option with the same name")
        if name in template.sections:
            raise ConfigurationError("Section already exists")

        if include_options is None:
            include_options = set()
        if exclude_options is None:
            exclude_options = set()

        for option in chain(include_options, exclude_options):
            if not option:
                raise ValueError("Option must not be empty")
            if not any(
                pattern.match(option)
                for pattern in (_ALLOWED_OPTIONS_PATTERN, _OPTIONS_IN_SECTION_PATTERN, _EXCLUDE_SECTION_PATTERN)
            ):
                raise ValueError(f"{option!r}: Forbidden option format")

        template.sections[name] = _SectionBuildPayload(
            func=config_getter,
            include_options=tuple(include_options),
            exclude_options=tuple(exclude_options),
        )

    @overload
    def section_property(self, func: Callable[[Any], Configuration[_T]], /) -> SectionProperty[_T]:
        ...

    @overload
    def section_property(
        self,
        /,
        *,
        include_options: Set[str] | None = ...,
        exclude_options: Set[str] | None = ...,
    ) -> Callable[[Callable[[Any], Configuration[_T]]], SectionProperty[_T]]:
        ...

    def section_property(
        self,
        func: Callable[[Any], Configuration[_T]] | None = None,
        /,
        *,
        include_options: Set[str] | None = None,
        exclude_options: Set[str] | None = None,
    ) -> Callable[[Callable[[Any], Configuration[_T]]], SectionProperty[_T]] | SectionProperty[_T]:
        self.__check_locked()

        def decorator(func: Callable[[Any], Configuration[_T]]) -> SectionProperty[_T]:
            self.add_section(func.__name__, func, include_options=include_options, exclude_options=exclude_options)
            return SectionProperty(func.__name__)

        if func is not None:
            return decorator(func)
        return decorator

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
    def getter(self, option: str, func: _Getter, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    def getter(
        self, option: str, func: _Getter | None = None, /, *, use_override: bool = True, readonly: bool = False
    ) -> Callable[[_GetterVar], _GetterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _Getter, /) -> None:
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

                wrapper = _make_function_wrapper(func, use_override=bool(use_override))
                new_config_property: _ConfigProperty
                if actual_property is None:
                    new_config_property = _ConfigProperty(wrapper)
                else:
                    new_config_property = actual_property.getter(wrapper)
                if readonly:
                    template.value_descriptor[option] = _ReadOnlyOptionBuildPayload(new_config_property)
                else:
                    template.value_descriptor[option] = new_config_property
            else:
                readonly_descriptor: _ReadOnlyOptionBuildPayload = actual_descriptor
                actual_descriptor = readonly_descriptor.get_descriptor()
                if not isinstance(actual_descriptor, _ConfigProperty):
                    raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")

                wrapper = _make_function_wrapper(func, use_override=bool(use_override))
                readonly_descriptor.set_new_descriptor(actual_descriptor.getter(wrapper))

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
    def getter_with_key(self, option: str, func: _KeyGetter, /, *, use_override: bool = True, readonly: bool = False) -> None:
        ...

    @overload
    def getter_with_key(
        self, option: str, func: _KeyGetter, /, *, use_key: Hashable, use_override: bool = True, readonly: bool = False
    ) -> None:
        ...

    def getter_with_key(
        self,
        option: str,
        func: _KeyGetter | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
        readonly: bool = False,
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar] | None:
        self.__check_locked()

        def wrapper_decorator(func: Callable[..., Any], use_key: Hashable) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        decorator = self.__make_option_key_decorator(
            option,
            lambda option, func: self.getter(option, func, readonly=readonly),
            wrapper_decorator,
            use_key=use_key,
            use_override=bool(use_override),
            no_object=False,
            allow_section_options=False,
        )

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def getter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: _KeyGetter,
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
    ) -> None:
        ...

    def getter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
    ) -> Any:
        self.__check_locked()

        decorator = self.__make_option_key_from_callable_decorator(
            option,
            lambda option, func, use_key: self.getter_with_key(
                option,
                func,
                use_key=use_key,
                use_override=use_override,
                readonly=readonly,
            ),
            key_factory=key_factory,
        )

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
    ) -> Callable[[_KeyGetterVar], _KeyGetterVar]:
        ...

    @overload
    def getter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyGetter,
        /,
        *,
        use_override: bool = True,
        readonly: bool = False,
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
    ) -> Any:
        return self.getter_with_key_from_callable(option, key_map.__getitem__, func, use_override=use_override, readonly=readonly)

    @overload
    def setter(self, option: str, /, *, use_override: bool = True) -> Callable[[_SetterVar], _SetterVar]:
        ...

    @overload
    def setter(self, option: str, func: _Setter, /, *, use_override: bool = True) -> None:
        ...

    def setter(
        self, option: str, func: _Setter | None = None, /, *, use_override: bool = True
    ) -> Callable[[_SetterVar], _SetterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _Setter, /) -> None:
            actual_descriptor: _Descriptor | None = template.value_descriptor.get(option)
            if actual_descriptor is None:
                raise OptionError(option, "Attributing setter for this option which has no getter")
            if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Read-only option")
            if not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            actual_property: _ConfigProperty = actual_descriptor
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            template.value_descriptor[option] = actual_property.setter(wrapper)

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
    def setter_with_key(self, option: str, func: _KeySetter, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def setter_with_key(self, option: str, func: _KeySetter, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def setter_with_key(
        self,
        option: str,
        func: _KeySetter | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeySetterVar], _KeySetterVar] | None:
        self.__check_locked()

        def wrapper_decorator(func: Callable[..., Any], use_key: Hashable) -> Callable[..., Any]:
            return lambda self, value: func(self, use_key, value)

        decorator = self.__make_option_key_decorator(
            option,
            self.setter,
            wrapper_decorator,
            use_key=use_key,
            use_override=bool(use_override),
            no_object=False,
            allow_section_options=False,
        )

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def setter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: _KeySetter,
        /,
        *,
        use_override: bool = True,
    ) -> None:
        ...

    def setter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
    ) -> Any:
        self.__check_locked()

        decorator = self.__make_option_key_from_callable_decorator(
            option,
            lambda option, func, use_key: self.setter_with_key(
                option,
                func,
                use_key=use_key,
                use_override=use_override,
            ),
            key_factory=key_factory,
        )

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
    ) -> Callable[[_KeySetterVar], _KeySetterVar]:
        ...

    @overload
    def setter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeySetter,
        /,
        *,
        use_override: bool = True,
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
    ) -> Any:
        return self.setter_with_key_from_callable(option, key_map.__getitem__, func, use_override=use_override)

    @overload
    def deleter(self, option: str, /, *, use_override: bool = True) -> Callable[[_DeleterVar], _DeleterVar]:
        ...

    @overload
    def deleter(self, option: str, func: _Deleter, /, *, use_override: bool = True) -> None:
        ...

    def deleter(
        self, option: str, func: _Deleter | None = None, /, *, use_override: bool = True
    ) -> Callable[[_DeleterVar], _DeleterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _Deleter, /) -> None:
            actual_descriptor: _Descriptor | None = template.value_descriptor.get(option)
            if actual_descriptor is None:
                raise OptionError(option, "Attributing deleter for this option which has no getter")
            if isinstance(actual_descriptor, _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Read-only option")
            if not isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
            actual_property: _ConfigProperty = actual_descriptor
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            template.value_descriptor[option] = actual_property.deleter(wrapper)

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
    def deleter_with_key(self, option: str, func: _KeyDeleter, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def deleter_with_key(self, option: str, func: _KeyDeleter, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def deleter_with_key(
        self,
        option: str,
        func: _KeyDeleter | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar] | None:
        self.__check_locked()

        def wrapper_decorator(func: Callable[..., Any], use_key: Hashable) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        decorator = self.__make_option_key_decorator(
            option,
            self.deleter,
            wrapper_decorator,
            use_key=use_key,
            use_override=bool(use_override),
            no_object=False,
            allow_section_options=False,
        )

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def deleter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: _KeyDeleter,
        /,
        *,
        use_override: bool = True,
    ) -> None:
        ...

    def deleter_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
    ) -> Any:
        self.__check_locked()

        decorator = self.__make_option_key_from_callable_decorator(
            option,
            lambda option, func, use_key: self.deleter_with_key(
                option,
                func,
                use_key=use_key,
                use_override=use_override,
            ),
            key_factory=key_factory,
        )

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
    ) -> Callable[[_KeyDeleterVar], _KeyDeleterVar]:
        ...

    @overload
    def deleter_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyDeleter,
        /,
        *,
        use_override: bool = True,
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
    ) -> Any:
        return self.deleter_with_key_from_callable(option, key_map.__getitem__, func, use_override=use_override)

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
    def add_main_update(self, /, *, use_override: bool = True) -> Callable[[_UpdaterVar], _UpdaterVar]:
        ...

    @overload
    def add_main_update(self, func: _UpdaterVar, /, *, use_override: bool = True) -> _UpdaterVar:
        ...

    def add_main_update(
        self, func: _UpdaterVar | None = None, /, *, use_override: bool = True
    ) -> _UpdaterVar | Callable[[_UpdaterVar], _UpdaterVar]:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        def decorator(func: _UpdaterVar, /) -> _UpdaterVar:
            self.__check_locked()
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
    def on_update(self, option: str, func: _Updater, /, *, use_override: bool = True) -> None:
        ...

    def on_update(
        self, option: str, func: _Updater | None = None, /, *, use_override: bool = True
    ) -> Callable[[_UpdaterVar], _UpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=True)
        def decorator(option: str, func: _Updater, /) -> None:
            if isinstance(template.value_descriptor.get(option), _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Cannot add update hook on read-only option")
            updater_list = template.option_update_hooks.setdefault(option, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.add(wrapper)

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
    def on_update_with_key(self, option: str, func: _KeyUpdater, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_with_key(self, option: str, func: _KeyUpdater, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def on_update_with_key(
        self,
        option: str,
        func: _KeyUpdater | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar] | None:
        self.__check_locked()

        def wrapper_decorator(func: Callable[..., Any], use_key: Hashable) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        decorator = self.__make_option_key_decorator(
            option,
            self.on_update,
            wrapper_decorator,
            use_key=use_key,
            use_override=bool(use_override),
            no_object=False,
            allow_section_options=True,
        )

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: _KeyUpdater,
        /,
        *,
        use_override: bool = True,
    ) -> None:
        ...

    def on_update_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
    ) -> Any:
        self.__check_locked()

        decorator = self.__make_option_key_from_callable_decorator(
            option,
            lambda option, func, use_key: self.on_update_with_key(
                option,
                func,
                use_key=use_key,
                use_override=use_override,
            ),
            key_factory=key_factory,
        )

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
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar]:
        ...

    @overload
    def on_update_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyUpdater,
        /,
        *,
        use_override: bool = True,
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
    ) -> Any:
        return self.on_update_with_key_from_callable(option, key_map.__getitem__, func, use_override=use_override)

    @overload
    def on_update_value(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueUpdaterVar], _ValueUpdaterVar]:
        ...

    @overload
    def on_update_value(self, option: str, func: _ValueUpdater, /, *, use_override: bool = True) -> None:
        ...

    def on_update_value(
        self, option: str, func: _ValueUpdater | None = None, /, *, use_override: bool = True
    ) -> Callable[[_ValueUpdaterVar], _ValueUpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=True)
        def decorator(option: str, func: _ValueUpdater, /) -> None:
            if isinstance(template.value_descriptor.get(option), _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Cannot add update hook on read-only option")
            updater_list = template.option_value_update_hooks.setdefault(option, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.add(wrapper)

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
    def on_update_value_with_key(self, option: str, func: _KeyValueUpdater, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_update_value_with_key(
        self, option: str, func: _KeyValueUpdater, /, *, use_key: Hashable, use_override: bool = True
    ) -> None:
        ...

    def on_update_value_with_key(
        self,
        option: str,
        func: _KeyValueUpdater | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar] | None:
        self.__check_locked()

        def wrapper_decorator(func: Callable[..., Any], use_key: Hashable) -> Callable[..., Any]:
            return lambda self, value: func(self, use_key, value)

        decorator = self.__make_option_key_decorator(
            option,
            self.on_update_value,
            wrapper_decorator,
            use_key=use_key,
            use_override=bool(use_override),
            no_object=False,
            allow_section_options=True,
        )

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_update_value_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_value_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: _KeyValueUpdater,
        /,
        *,
        use_override: bool = True,
    ) -> None:
        ...

    def on_update_value_with_key_from_callable(
        self,
        option: str,
        key_factory: Callable[[str], Hashable],
        func: Any = None,
        /,
        *,
        use_override: bool = True,
    ) -> Any:
        self.__check_locked()

        decorator = self.__make_option_key_from_callable_decorator(
            option,
            lambda option, func, use_key: self.on_update_value_with_key(
                option,
                func,
                use_key=use_key,
                use_override=use_override,
            ),
            key_factory=key_factory,
        )

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
    ) -> Callable[[_KeyValueUpdaterVar], _KeyValueUpdaterVar]:
        ...

    @overload
    def on_update_value_with_key_from_map(
        self,
        option: str,
        key_map: Mapping[str, Hashable],
        func: _KeyValueUpdater,
        /,
        *,
        use_override: bool = True,
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
    ) -> Any:
        return self.on_update_value_with_key_from_callable(option, key_map.__getitem__, func, use_override=use_override)

    @overload
    def on_section_update(self, section: str, /, *, use_override: bool = True) -> Callable[[_UpdaterVar], _UpdaterVar]:
        ...

    @overload
    def on_section_update(self, section: str, func: _Updater, /, *, use_override: bool = True) -> None:
        ...

    def on_section_update(
        self, section: str, func: _Updater | None = None, /, *, use_override: bool = True
    ) -> Callable[[_UpdaterVar], _UpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__section_decorator(section)
        def decorator(section: str, func: _Updater, /) -> None:
            updater_list = template.section_update_hooks.setdefault(section, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise SectionError(section, "Function already registered")
            updater_list.add(wrapper)

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def on_delete(self, option: str, /, *, use_override: bool = True) -> Callable[[_UpdaterVar], _UpdaterVar]:
        ...

    @overload
    def on_delete(self, option: str, func: _Updater, /, *, use_override: bool = True) -> None:
        ...

    def on_delete(
        self, option: str, func: _Updater | None = None, /, *, use_override: bool = True
    ) -> Callable[[_UpdaterVar], _UpdaterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=True)
        def decorator(option: str, func: _Updater, /) -> None:
            if isinstance(template.value_descriptor.get(option), _ReadOnlyOptionBuildPayload):
                raise OptionError(option, "Cannot add delete hook on read-only option")
            updater_list = template.option_delete_hooks.setdefault(option, set())
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in updater_list:
                raise OptionError(option, "Function already registered")
            updater_list.add(wrapper)

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
    def on_delete_with_key(self, option: str, func: _KeyUpdater, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def on_delete_with_key(self, option: str, func: _KeyUpdater, /, *, use_key: Hashable, use_override: bool = True) -> None:
        ...

    def on_delete_with_key(
        self,
        option: str,
        func: _KeyUpdater | None = None,
        /,
        *,
        use_key: Any = _NO_DEFAULT,
        use_override: bool = True,
    ) -> Callable[[_KeyUpdaterVar], _KeyUpdaterVar] | None:
        self.__check_locked()

        def wrapper_decorator(func: Callable[..., Any], use_key: Hashable) -> Callable[..., Any]:
            return lambda self: func(self, use_key)

        decorator = self.__make_option_key_decorator(
            option,
            self.on_delete,
            wrapper_decorator,
            use_key=use_key,
            use_override=bool(use_override),
            no_object=False,
            allow_section_options=True,
        )

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
        func: _KeyUpdater,
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
            use_key = _NO_DEFAULT
        return self.on_delete_with_key(option, func, use_key=use_key, use_override=use_override)

    @overload
    def add_value_validator(
        self, option: str, /, *, use_override: bool = True
    ) -> Callable[[_ValueValidatorVar], _ValueValidatorVar]:
        ...

    @overload
    def add_value_validator(self, option: str, func: _ValueValidator, /, *, use_override: bool = True) -> None:
        ...

    def add_value_validator(
        self,
        option: str,
        func: _ValueValidator | None = None,
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_ValueValidatorVar], _ValueValidatorVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        if isinstance(func, type):
            raise TypeError("Use value_validator_static() to check types")

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _ValueValidator, /) -> None:
            value_validator_list = template.value_validator.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in value_validator_list:
                raise OptionError(option, "Function already registered")
            value_validator_list.append(wrapper)

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
    def add_value_validator_static(self, option: str, func: _StaticValueValidator, /) -> None:
        ...

    @overload
    def add_value_validator_static(
        self,
        option: str,
        /,
        *,
        predicate: Callable[[Any], bool | TypeGuard[Any]],
        exception: type[BaseException] = ValueError,
        message: str | None = None,
    ) -> None:
        ...

    def add_value_validator_static(
        self,
        option: str,
        func: _StaticValueValidator | type | Sequence[type] | None = None,
        /,
        *,
        accept_none: bool = False,
        predicate: Callable[[Any], bool | TypeGuard[Any]] | None = None,
        exception: type[BaseException] = ValueError,
        message: str | None = None,
    ) -> Callable[[_StaticValueValidatorVar], _StaticValueValidatorVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        if func is not None and predicate is not None:
            raise TypeError("Bad parameters")

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _StaticValueValidator, /) -> None:
            value_validator_list = template.value_validator.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=False, no_object=True)
            if wrapper in value_validator_list:
                raise OptionError(option, "Function already registered")
            value_validator_list.append(wrapper)

        if predicate is not None:
            decorator(_make_predicate_validator(predicate, exception, message))
            return None

        if isinstance(func, (type, Sequence)):
            _type: type | tuple[type, ...] = func if isinstance(func, type) else tuple(func)

            if isinstance(_type, tuple):
                if not _type or any(not isinstance(t, type) for t in _type):
                    raise TypeError("Invalid types argument")
                if len(_type) == 1:
                    _type = _type[0]

            decorator(_make_type_checker(_type, accept_none))
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
    def add_value_converter_on_get(self, option: str, func: _ValueConverter, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter_on_get(
        self,
        option: str,
        func: _ValueConverter | None = None,
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        if isinstance(func, type):
            raise TypeError("Use add_value_converter_on_set_static() to convert value using type")

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _ValueConverter, /) -> None:
            value_converter_list = template.value_converter_on_get.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)

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
    def add_value_converter_on_get_static(self, option: str, func: _StaticValueConverter, /) -> None:
        ...

    def add_value_converter_on_get_static(
        self,
        option: str,
        func: _StaticValueConverter | type | None = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _StaticValueConverter, /) -> None:
            value_converter_list = template.value_converter_on_get.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=False, no_object=True)
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)

        if isinstance(func, type):

            if issubclass(func, Enum):
                raise TypeError("Use add_enum_converter() instead for enum conversions")

            decorator(_make_value_converter(func, accept_none))
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
    def add_value_converter_on_set(self, option: str, func: _ValueConverter, /, *, use_override: bool = True) -> None:
        ...

    def add_value_converter_on_set(
        self,
        option: str,
        func: _ValueConverter | None = None,
        /,
        *,
        use_override: bool = True,
    ) -> Callable[[_ValueConverterVar], _ValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        if isinstance(func, type):
            raise TypeError("Use add_value_converter_on_set_static() to convert value using type")

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _ValueConverter, /) -> None:
            value_converter_list = template.value_converter_on_set.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=bool(use_override))
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)

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
    def add_value_converter_on_set_static(self, option: str, func: _StaticValueConverter, /) -> None:
        ...

    def add_value_converter_on_set_static(
        self,
        option: str,
        func: _StaticValueConverter | type | None = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Callable[[_StaticValueConverterVar], _StaticValueConverterVar] | None:
        self.__check_locked()
        template: _ConfigInfoTemplate = self.__template

        @self.__option_decorator(option, allow_section_options=False)
        def decorator(option: str, func: _StaticValueConverter, /) -> None:
            value_converter_list = template.value_converter_on_set.setdefault(option, [])
            wrapper = _make_function_wrapper(func, use_override=False, no_object=True)
            if wrapper in value_converter_list:
                raise OptionError(option, "Function already registered")
            value_converter_list.append(wrapper)

        if isinstance(func, type):

            if issubclass(func, Enum):
                raise TypeError("Use add_enum_converter() instead for enum conversions")

            decorator(_make_value_converter(func, accept_none))
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
            if not _ALLOWED_ALIASES_PATTERN.match(alias):
                raise InvalidAliasError(alias, "Forbidden alias format")
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
            if isinstance(descriptor, _ConfigProperty) and (descriptor.fset is not None or descriptor.fdel is not None):
                raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            if (
                template.option_update_hooks.get(option)
                or template.option_value_update_hooks.get(option)
                or template.option_delete_hooks.get(option)
            ):
                raise OptionError(option, "Trying to flag option as read-only with registered update/delete hooks")
            template.value_descriptor[option] = _ReadOnlyOptionBuildPayload(descriptor)

    def __make_option_decorator(
        self,
        option: str,
        decorator_body: Callable[[str, _Func], None],
        *,
        allow_section_options: bool,
    ) -> Callable[[_FuncVar], _FuncVar]:
        def decorator(func: _FuncVar, /) -> _FuncVar:
            self.__check_locked()
            if m := _OPTIONS_IN_SECTION_PATTERN.match(option):
                if not allow_section_options:
                    raise ConfigurationError(f"{option!r}: section options forbidden")
                self.check_section_validity(m["section"])
            else:
                self.check_option_validity(option, use_alias=False)
            decorator_body(option, func)
            return func

        return decorator

    def __option_decorator(
        self,
        option: str,
        allow_section_options: bool,
    ) -> Callable[[Callable[[str, _Func], None]], Callable[[_FuncVar], _FuncVar]]:
        def decorator(func: Any) -> Any:
            return self.__make_option_decorator(option, func, allow_section_options=allow_section_options)

        return decorator

    def __make_option_key_decorator(
        self,
        option: str,
        decorator_body: Callable[[str, _WrappedFunctionWrapper], None],
        wrapper_factory: Callable[[_Func, Hashable], _Func],
        *,
        use_key: Hashable,
        use_override: bool,
        no_object: bool,
        allow_section_options: bool,
    ) -> Callable[[_FuncVar], _FuncVar]:
        @self.__option_decorator(option, allow_section_options=allow_section_options)
        def decorator(option: str, func: _Func, /, *, use_key: Hashable = use_key) -> None:
            if use_key is _NO_DEFAULT:
                use_key = option
            else:
                hash(use_key)
            unique_key: Hashable = (option, use_key)

            wrapper = _WrappedFunctionWrapper(
                func,
                unique_key,
                lambda func: wrapper_factory(func, use_key),
                use_override=bool(use_override),
                no_object=bool(no_object),
            )
            decorator_body(option, wrapper)

        return decorator

    def __make_option_key_from_callable_decorator(
        self,
        option: str,
        decorator_body: Callable[[str, _Func, Hashable], None],
        key_factory: Callable[[str], Hashable],
    ) -> Callable[[_FuncVar], _FuncVar]:
        def decorator(func: _FuncVar) -> _FuncVar:
            self.__check_locked()
            decorator_body(option, func, key_factory(option))
            return func

        return decorator

    def __make_section_decorator(
        self,
        section: str,
        decorator_body: Callable[[str, _Func], None],
    ) -> Callable[[_FuncVar], _FuncVar]:
        def decorator(func: _FuncVar, /) -> _FuncVar:
            self.__check_locked()
            self.check_section_validity(section)
            decorator_body(section, func)
            return func

        return decorator

    def __section_decorator(self, section: str) -> Callable[[Callable[[str, _Func], None]], Callable[[_FuncVar], _FuncVar]]:
        def decorator(func: Any) -> Any:
            return self.__make_section_decorator(section, func)

        return decorator

    def __check_locked(self) -> None:
        if self.__info is not None:
            raise TypeError("Attempt to modify template after the class creation")

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
        self.__doc__: str | None = None

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
        config_template: ConfigurationTemplate = getattr(self.__owner, self.__config_name)
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


@final
class SectionProperty(Generic[_T], Object):
    __slots__ = (
        "__name",
        "__owner",
        "__config_name",
        "__doc__",
    )

    def __init__(self, name: str | None = None) -> None:
        super().__init__()
        self.__doc__: str | None = None
        self.__owner: type
        self.__name: str
        if name is not None:
            self.__name = name

    def __set_name__(self, owner: type, name: str, /) -> None:
        if len(name) == 0:
            raise ValueError("Attribute name must not be empty")
        with suppress(AttributeError):
            if self.__name != name:
                raise ValueError(f"Assigning {self.__name!r} config attribute to {name}")
        self.__owner = owner
        self.__name = name
        config: ConfigurationTemplate = _retrieve_configuration(owner)
        if config.name is None:
            raise TypeError("SectionProperty must be declared after the ConfigurationTemplate object")
        config.check_section_validity(name)
        self.__config_name: str = config.name

    @overload
    def __get__(self, obj: None, objtype: type | None = ..., /) -> SectionProperty[_T]:
        ...

    @overload
    def __get__(self, obj: object, objtype: type | None = ..., /) -> Configuration[_T]:
        ...

    def __get__(self, obj: object, objtype: type | None = None, /) -> SectionProperty[_T] | Configuration[_T]:
        if obj is None:
            return self

        name: str = self.__name
        config_template: ConfigurationTemplate = getattr(self.__owner, self.__config_name)
        config: Configuration[Any] = config_template.__get__(obj, objtype)

        return config.section(name)

    def __set__(self, obj: Any, value: Configuration[_T], /) -> NoReturn:
        raise AttributeError("Read-only attribute")

    def __delete__(self, obj: Any, /) -> NoReturn:
        raise AttributeError("Read-only attribute")

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
@dataclass(frozen=True, eq=False)  # TODO (3.11): slots=True, weakref_slot=True
class Section(Generic[_T, _S], Object):
    name: str
    original_config: Callable[[_T], Configuration[_S]]
    include_options: Set[str] = field(default_factory=frozenset)
    exclude_options: Set[str] = field(default_factory=frozenset)

    __cache_lock: RLock = field(init=False, repr=False, default_factory=RLock)
    __cache: WeakKeyDictionary[Configuration[_T], Configuration[_S]] = field(
        init=False,
        repr=False,
        default_factory=WeakKeyDictionary,
    )

    def __post_init__(self) -> None:
        if options_conflict := set(self.include_options).intersection(self.exclude_options):
            raise ConfigurationError(f"{', '.join(map(repr, options_conflict))} force included and excluded")

    def config(self, parent: Configuration[_T]) -> Configuration[_S]:
        cache: WeakKeyDictionary[Configuration[_T], Configuration[_S]] = self.__cache
        try:
            section_config = cache[parent]
        except KeyError:
            with self.__cache_lock:
                try:
                    section_config = cache[parent]
                except KeyError:
                    weakref_callback = self._make_section_weakref_callback(parent)
                    cache[parent] = section_config = Configuration._from_section(self, parent, weakref_callback)
        return section_config

    def _make_section_weakref_callback(self, parent: Configuration[_T]) -> Callable[[Any], None]:
        selfref = weakref(self)
        parentref = weakref(parent)

        def callback(_: Any) -> None:
            self = selfref()
            parent = parentref()
            if self is not None and parent is not None:
                with self.__cache_lock:
                    self.__cache.pop(parent, None)

        return callback


@final
@dataclass(frozen=True, eq=False, slots=True)
class ConfigurationInfo(Object, Generic[_T]):
    options: Set[str]
    _: KW_ONLY
    sections: Sequence[Section[_T, Any]] = field(default_factory=tuple)
    option_value_update_hooks: Mapping[str, Set[Callable[[_T, Any], None]]] = field(default_factory=_default_mapping)
    option_delete_hooks: Mapping[str, Set[Callable[[_T], None]]] = field(default_factory=_default_mapping)
    option_update_hooks: Mapping[str, Set[Callable[[_T], None]]] = field(default_factory=_default_mapping)
    section_update_hooks: Mapping[str, Set[Callable[[_T], None]]] = field(default_factory=_default_mapping)
    main_object_update_hooks: Set[Callable[[_T], None]] = field(default_factory=frozenset)
    value_converter_on_get: Mapping[str, Sequence[Callable[[_T, Any], Any]]] = field(default_factory=_default_mapping)
    value_converter_on_set: Mapping[str, Sequence[Callable[[_T, Any], Any]]] = field(default_factory=_default_mapping)
    value_validator: Mapping[str, Sequence[Callable[[_T, Any], None]]] = field(default_factory=_default_mapping)
    value_descriptor: Mapping[str, _Descriptor] = field(default_factory=_default_mapping)
    aliases: Mapping[str, str] = field(default_factory=_default_mapping)
    readonly_options: Set[str] = field(default_factory=frozenset)

    _sections_map: MappingProxyType[str, Section[_T, Any]] = field(init=False, repr=False)

    __hash__ = None  # type: ignore[assignment]

    class __ReadOnlyOptionWrapper:
        def __init__(self, default_descriptor: _Descriptor) -> None:
            self.__descriptor_get = default_descriptor.__get__

        def __get__(self, obj: object, objtype: type | None = None, /) -> Any:
            return self.__descriptor_get(obj, objtype)

    def __post_init__(self) -> None:
        setattr = object.__setattr__
        setattr(self, "_sections_map", MappingProxyType({s.name: s for s in self.sections}))
        if len(self._sections_map) != len(self.sections):
            raise ConfigurationError("Section name duplicate")

    def get_section(self, name: str) -> Section[_T, Any]:
        try:
            return self._sections_map[name]
        except KeyError:
            raise UnknownSectionError(name) from None

    def filter(
        self,
        *,
        include_options: Set[str] | None = None,
        exclude_options: Set[str] | None = None,
    ) -> ConfigurationInfo[_T]:
        from collections import defaultdict
        from dataclasses import replace

        if not include_options and not exclude_options:
            return replace(self)

        new_options: set[str] = set()
        new_section_include_options: defaultdict[str, set[str]] = defaultdict(set)
        new_section_exclude_options: defaultdict[str, set[str]] = defaultdict(set)
        exclude_sections: set[str] = set()

        if include_options is None:
            include_options = set()
        if exclude_options is None:
            exclude_options = set()

        for section in self.sections:
            new_section_include_options[section.name].update(section.include_options)
            new_section_exclude_options[section.name].update(section.exclude_options)

        if not include_options:
            new_options.update(self.options)

        for option in include_options:
            if m := _OPTIONS_IN_SECTION_PATTERN.match(option):
                section_name, option = m.group("section", "option")
                self.check_section_validity(section_name)
                new_section_include_options[section_name].add(option)
            else:
                self.check_option_validity(option)
                new_options.add(option)

        for option in exclude_options:
            if m := _OPTIONS_IN_SECTION_PATTERN.match(option):
                section_name, option = m.group("section", "option")
                self.check_section_validity(section_name)
                new_section_exclude_options[section_name].add(option)
            elif m := _EXCLUDE_SECTION_PATTERN.match(option):
                section_name = m.group("section")
                self.check_section_validity(section_name)
                if m.group("subsection") == "*":
                    exclude_sections.add(section_name)
                else:
                    new_section_exclude_options[section_name].add(m.group("subsection"))
            else:
                self.check_option_validity(option)
                new_options.discard(option)

        return replace(
            self,
            options=frozenset(new_options),
            sections=tuple(
                replace(
                    section,
                    include_options=new_section_include_options[section.name],
                    exclude_options=new_section_exclude_options[section.name],
                )
                for section in self.sections
                if section.name not in exclude_sections
            ),
        )

    def check_option_validity(self, option: str, *, use_alias: bool = False) -> str:
        if use_alias:
            option = self.aliases.get(option, option)
        if option not in self.options or option in self._sections_map:
            raise UnknownOptionError(option)
        return option

    def is_option_valid(self, option: str, *, use_alias: bool = False) -> bool:
        try:
            self.check_option_validity(option, use_alias=use_alias)
        except UnknownOptionError:
            return False
        return True

    def check_section_validity(self, section: str) -> str:
        if section not in self._sections_map:
            raise UnknownSectionError(section)
        return section

    def is_section_valid(self, section: str) -> bool:
        try:
            self.check_section_validity(section)
        except UnknownSectionError:
            return False
        return True

    def get_all_options(self, parent: Configuration[_T]) -> frozenset[str]:
        return frozenset(self.options).union(
            _OPTIONS_IN_SECTION_FMT.format(section=section.name, option=option)
            for section in self.sections
            for option in section.config(parent).get_all_options()
        )

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

    def get_options_update_hooks(self, *options: str) -> Set[Callable[[_T], None]]:
        get_hooks = self.option_update_hooks.get
        return set(chain.from_iterable(get_hooks(option, ()) for option in set(options)))

    def get_options_delete_hooks(self, *options: str) -> Set[Callable[[_T], None]]:
        get_hooks = self.option_delete_hooks.get
        return set(chain.from_iterable(get_hooks(option, ()) for option in set(options)))

    def get_sections_update_hooks(self, *options: str) -> Set[Callable[[_T], None]]:
        sections = {m["section"] for m in filter(None, map(_OPTIONS_IN_SECTION_PATTERN.match, options))}
        get_hooks = self.section_update_hooks.get
        return set(chain.from_iterable(get_hooks(section, ()) for section in sections))


del _default_mapping


@final
@dataclass(frozen=True, eq=False, slots=True, kw_only=True)
class _BoundSection(Generic[_T], Object):
    name: str
    parent: Configuration[_T]


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


class Configuration(NonCopyable, Generic[_T]):
    __update_stack: ClassVar[dict[object, set[str]]] = dict()
    __init_context: ClassVar[set[object]] = set()
    __update_context: ClassVar[dict[object, _UpdateRegister]] = dict()
    __lock_cache: ClassVar[WeakKeyDictionary[object, RLock]] = WeakKeyDictionary()
    __default_lock: ClassVar[RLock] = RLock()

    __slots__ = ("__info", "__obj", "__sections", "__weakref__")

    class __OptionUpdateContext(NamedTuple):
        first_call: bool
        register: _UpdateRegister
        sections: Sequence[Configuration.__SectionUpdateContext]  # type: ignore[misc]

    class __SectionUpdateContext(NamedTuple):
        option_context: Configuration.__OptionUpdateContext
        section: _BoundSection[Any]

    def __init__(self, obj: _T | weakref[_T], info: ConfigurationInfo[_T]) -> None:
        self.__obj: Callable[[], _T | None]
        if isinstance(obj, weakref):
            self.__obj = obj
        else:
            weakref(obj)  # Even if we store a strong reference, the object MUST be weak-referenceable
            self.__obj = lambda obj=obj: obj  # type: ignore[misc]
        self.__info: ConfigurationInfo[_T] = info
        self.__sections: Sequence[_BoundSection[Any]] = ()

    @staticmethod
    def _from_section(
        section: Section[_T, _S],
        parent: Configuration[_T],
        weakref_callback: Callable[[weakref[_S]], Any] | None = None,
    ) -> Configuration[_S]:

        parent.info.check_section_validity(section.name)

        section_config: Configuration[_S] = section.original_config(parent.__self__)

        section_obj = section_config.__self__
        section_info = section_config.info

        self = Configuration(
            weakref(section_obj, weakref_callback) if section_config.has_weakref() else section_obj,
            section_info.filter(include_options=section.include_options, exclude_options=section.exclude_options),
        )
        self.__sections = tuple(prepend(_BoundSection(name=section.name, parent=parent), section_config.__sections))

        return self

    @reprlib.recursive_repr()
    def __repr__(self) -> str:
        option_dict = self.as_dict(sorted_keys=True)
        return f"{type(self).__name__}({self.__self__!r}, {', '.join(f'{k}={v!r}' for k, v in option_dict.items())})"

    def get_all_options(self) -> frozenset[str]:
        return self.__info.get_all_options(self)

    @overload
    def get(self, option: str) -> Any:
        ...

    @overload
    def get(self, option: str, default: _DT) -> Any | _DT:
        ...

    def get(self, option: str, default: Any = _NO_DEFAULT) -> Any:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        section, option = self._parse_option(option)

        value: Any
        with self.__lazy_lock(obj):
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.get(option, default)

            descriptor = info.get_value_descriptor(option, type(obj))

            try:
                value = descriptor.__get__(obj, type(obj))
            except AttributeError as exc:
                if default is _NO_DEFAULT:
                    if isinstance(exc, UnregisteredOptionError):
                        raise
                    raise UnregisteredOptionError(option) from exc
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
            } | {section.name: section.config(self).as_dict(sorted_keys=sorted_keys) for section in info.sections}

    def set(self, option: str, value: Any) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        section, option, updating_option = self._parse_option_with_format(option)

        with self.__updating_option(obj, updating_option, info, sections=self.__sections) as update_context:
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.set(option, value)

            descriptor = info.get_value_setter(option, type(obj))

            for value_validator in info.value_validator.get(option, ()):
                value_validator(obj, value)
            for value_converter in info.value_converter_on_set.get(option, ()):
                value = value_converter(obj, value)

            if update_context:
                try:
                    actual_value = descriptor.__get__(obj, type(obj))
                except AttributeError:
                    pass
                else:
                    if actual_value is value or actual_value == value:
                        return

            descriptor.__set__(obj, value)

            if update_context:
                self.__apply_value_update_hooks(option, value, update_context)

    def only_set(self, option: str, value: Any) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        section, option = self._parse_option(option)

        with self.__lazy_lock(obj):
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.only_set(option, value)

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
        section, option, updating_option = self._parse_option_with_format(option)

        with self.__updating_option(obj, updating_option, info, sections=self.__sections) as update_context:
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.delete(option)

            descriptor = info.get_value_deleter(option, type(obj))

            descriptor.__delete__(obj)

            if update_context:
                self.__option_deleted(option, update_context)

    def only_delete(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        section, option = self._parse_option(option)

        with self.__lazy_lock(obj):
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.only_delete(option)

            descriptor = info.get_value_deleter(option, type(obj))

            descriptor.__delete__(obj)

    def __delitem__(self, option: str, /) -> None:
        try:
            return self.delete(option)
        except OptionError as exc:
            raise KeyError(option) from exc

    def update(self, **kwargs: Any) -> None:
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
        options = list(map(self._parse_option_without_split, kwargs))
        if sorted(options) != sorted(set(options)):
            raise TypeError("Multiple aliases to the same option given")

        from collections import defaultdict

        section_kwargs: defaultdict[str, dict[str, Any]] = defaultdict(dict)

        with self.__updating_many_options(obj, *options, info=self.__info, sections=self.__sections):
            set_value = self.set
            for option, value in kwargs.items():
                section, option = self._parse_option(option)
                if section:
                    section_kwargs[section][option] = value
                    continue
                set_value(option, value)
            info: ConfigurationInfo[_T] = self.__info
            for section in section_kwargs:
                section_config = info.get_section(section).config(self)
                section_config.update(**section_kwargs[section])

    def reset(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        section, option, updating_option = self._parse_option_with_format(option)

        with self.__updating_option(obj, updating_option, info, sections=self.__sections) as update_context:
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.reset(option)

            descriptor = info.get_value_setter(option, type(obj))

            try:
                value: Any = descriptor.__get__(obj, type(obj))
            except UnregisteredOptionError:
                raise
            except AttributeError as exc:
                raise UnregisteredOptionError(option) from exc

            for value_converter in info.value_converter_on_get.get(option, ()):
                value = value_converter(obj, value)

            for value_validator in info.value_validator.get(option, ()):
                value_validator(obj, value)

            for value_converter in info.value_converter_on_set.get(option, ()):
                value = value_converter(obj, value)

            descriptor.__set__(obj, value)

            if update_context:
                self.__apply_value_update_hooks(option, value, update_context)

    def only_reset(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info
        section, option = self._parse_option(option)

        with self.__lazy_lock(obj):
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.only_reset(option)

            descriptor = info.get_value_setter(option, type(obj))

            try:
                value: Any = descriptor.__get__(obj, type(obj))
            except UnregisteredOptionError:
                raise
            except AttributeError as exc:
                raise UnregisteredOptionError(option) from exc

            for value_converter in info.value_converter_on_get.get(option, ()):
                value = value_converter(obj, value)

            for value_validator in info.value_validator.get(option, ()):
                value_validator(obj, value)

            for value_converter in info.value_converter_on_set.get(option, ()):
                value = value_converter(obj, value)

            descriptor.__set__(obj, value)

    @contextmanager
    def initialization(self) -> Iterator[None]:
        if self.__sections:
            raise InitializationError("A section configuration cannot be in initialization context")

        obj: _T = self.__self__

        if obj in Configuration.__init_context:
            yield
            return

        with self.__lazy_lock(obj):
            if obj in Configuration.__update_stack:
                raise InitializationError("Cannot use initialization context while updating an option value")

            with ExitStack() as stack:
                Configuration.__init_context.add(obj)
                stack.callback(Configuration.__init_context.discard, obj)
                yield
                Configuration.__update_context.pop(obj, None)
                update_register = _UpdateRegister()
                info: ConfigurationInfo[_T] = self.__info
                for option in info.options:
                    descriptor = info.get_value_descriptor(option, type(obj))
                    try:
                        value: Any = descriptor.__get__(obj, type(obj))
                    except AttributeError:
                        update_register.has_been_deleted(option)
                    else:
                        for value_updater in info.option_value_update_hooks.get(option, ()):
                            value_updater(obj, value)
                        update_register.has_new_value(option)
                for option_deleted in info.get_options_delete_hooks(*update_register.deleted):
                    option_deleted(obj)
                for option_updater in info.get_options_update_hooks(*update_register.modified):
                    option_updater(obj)
                for main_updater in info.main_object_update_hooks:
                    main_updater(obj)

    @final
    def has_initialization_context(self) -> bool:
        return self.__self__ in Configuration.__init_context

    @final
    def is_updating_options(self) -> bool:
        return self.__self__ in Configuration.__update_context

    @final
    def is_updating_option(self, option: str) -> bool:
        return option in Configuration.__update_stack.get(self.__self__, ())

    def section(self, section: str) -> Configuration[Any]:
        info: ConfigurationInfo[_T] = self.__info
        section = info.check_section_validity(section)
        return info.get_section(section).config(self)

    def update_option(self, option: str) -> None:
        option = self._parse_option_without_split(option)
        return self.__update_single_option(option)

    def update_options(self, *options: str) -> None:
        return self.__update_options(*set(map(self._parse_option_without_split, options)))

    def update_section(self, section: str) -> None:
        return self.section(section).update_object()

    def update_object(self) -> None:
        info: ConfigurationInfo[_T] = self.__info
        return self.__update_options(*info.get_all_options(self))

    def has_weakref(self) -> bool:
        return isinstance(self.__obj, weakref)

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

    def _parse_option(self, option: str) -> tuple[str | None, str]:
        info: ConfigurationInfo[_T] = self.__info
        section: str | None = None

        if m := _OPTIONS_IN_SECTION_PATTERN.match(option):
            section, option = map(str, m.group("section", "option"))
            section = info.check_section_validity(section)
        else:
            option = info.check_option_validity(option, use_alias=True)
        return section, option

    def _parse_option_with_format(self, option: str) -> tuple[str | None, str, str]:
        section, option = self._parse_option(option)
        return section, option, _OPTIONS_IN_SECTION_FMT.format(section=section, option=option) if section else option

    def _parse_option_without_split(self, option: str) -> str:
        return self._parse_option_with_format(option)[2]

    def __apply_value_update_hooks(self, option: str, value: Any, update_context: __OptionUpdateContext) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info

        for value_updater in info.option_value_update_hooks.get(option, ()):
            value_updater(obj, value)

        update_context.register.has_new_value(option)

        for section_context in update_context.sections:
            section = section_context.section
            section_option = _OPTIONS_IN_SECTION_FMT.format(section=section.name, option=option)
            section.parent.__apply_value_update_hooks(section_option, value, section_context.option_context)

    def __option_deleted(self, option: str, update_context: __OptionUpdateContext) -> None:
        update_context.register.has_been_deleted(option)

        for section_context in update_context.sections:
            section = section_context.section
            section_option = _OPTIONS_IN_SECTION_FMT.format(section=section.name, option=option)
            section.parent.__option_deleted(section_option, section_context.option_context)

    def __update_options(self, *options: str) -> None:
        nb_options = len(options)
        if nb_options < 1:
            return
        if nb_options == 1:
            return self.__update_single_option(options[0])

        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info

        from collections import defaultdict

        objtype: type = type(obj)
        with self.__updating_many_options(obj, *options, info=info, sections=self.__sections) as update_contexts:
            section_update: defaultdict[str, set[str]] = defaultdict(set)

            for option, context in update_contexts.items():
                if not context.first_call:
                    continue

                section, option = self._parse_option(option)
                if section:
                    section_update[section].add(option)
                    continue

                descriptor = info.get_value_descriptor(option, objtype)
                try:
                    value: Any = descriptor.__get__(obj, objtype)
                except AttributeError:
                    self.__option_deleted(option, context)
                else:
                    self.__apply_value_update_hooks(option, value, context)

            for section, section_options in section_update.items():
                section_config = info.get_section(section).config(self)
                section_config.update_options(*section_options)

    def __update_single_option(self, option: str) -> None:
        obj: _T = self.__self__
        info: ConfigurationInfo[_T] = self.__info

        with self.__updating_option(obj, option, info, sections=self.__sections) as update_context:
            if not update_context or not update_context.first_call:
                return

            section, option = self._parse_option(option)
            if section:
                section_config = info.get_section(section).config(self)
                return section_config.update_option(option)

            descriptor = info.get_value_descriptor(option, type(obj))
            try:
                value: Any = descriptor.__get__(obj, type(obj))
            except AttributeError:
                self.__option_deleted(option, update_context)
            else:
                self.__apply_value_update_hooks(option, value, update_context)

    @classmethod
    @contextmanager
    def __updating_option(
        cls,
        obj: object,
        option: str,
        info: ConfigurationInfo[Any],
        *,
        sections: Sequence[_BoundSection[Any]],
    ) -> Iterator[__OptionUpdateContext | None]:
        UpdateContext = cls.__OptionUpdateContext

        with cls.__lazy_lock(obj), cls.__updating_section_option(sections, option) as sections_context:
            if obj in cls.__init_context:
                yield None
                return

            update_register = cls.__update_context.setdefault(obj, _UpdateRegister())
            update_stack: set[str] = cls.__update_stack.setdefault(obj, set())
            if option in update_stack:
                yield UpdateContext(first_call=False, register=update_register, sections=sections_context)
                return

            def cleanup(obj: object) -> None:
                update_stack.discard(option)
                if not update_stack:
                    cls.__update_stack.pop(obj, None)

            update_stack.add(option)
            with ExitStack() as stack:
                stack.callback(cleanup, obj)
                yield UpdateContext(first_call=True, register=update_register, sections=sections_context)
            if update_stack:
                return
            update_register = cls.__update_context.pop(obj, update_register)
            if not update_register:
                return
            for option_deleted in info.get_options_delete_hooks(*update_register.deleted):
                option_deleted(obj)
            for option_updater in info.get_options_update_hooks(*update_register.modified):
                option_updater(obj)
            for section_updater in info.get_sections_update_hooks(*update_register.modified, *update_register.deleted):
                section_updater(obj)
            for main_updater in info.main_object_update_hooks:
                main_updater(obj)

    @classmethod
    @contextmanager
    def __updating_many_options(
        cls,
        obj: object,
        *options: str,
        info: ConfigurationInfo[Any],
        sections: Sequence[_BoundSection[Any]],
    ) -> Iterator[dict[str, __OptionUpdateContext]]:
        if len(options) < 1:  # No need to take the lock and init something
            yield {}
            return

        with cls.__lazy_lock(obj), ExitStack() as stack:
            yield {
                option: context
                for option in options
                if (context := stack.enter_context(cls.__updating_option(obj, option, info, sections=sections))) is not None
            }

    @classmethod
    @contextmanager
    def __updating_section_option(
        cls,
        sections: Sequence[_BoundSection[Any]],
        option: str,
    ) -> Iterator[Sequence[__SectionUpdateContext]]:
        if not sections:
            yield ()
            return

        UpdateContext = cls.__SectionUpdateContext

        with ExitStack() as stack:
            yield tuple(
                UpdateContext(option_context=context, section=section)
                for section in sections
                if (
                    context := stack.enter_context(
                        cls.__updating_option(
                            section.parent.__self__,
                            _OPTIONS_IN_SECTION_FMT.format(section=section.name, option=option),
                            section.parent.__info,
                            sections=section.parent.__sections,
                        )
                    )
                )
            )

    @classmethod
    def __lazy_lock(cls, obj: object) -> RLock:
        lock_cache = cls.__lock_cache
        lock: RLock | None = lock_cache.get(obj)
        if lock is None:
            with cls.__default_lock:
                lock = lock_cache.get(obj)
                if lock is None:
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
        except (OSError, TypeError):
            pass
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


@_no_type_check_cache
def _make_predicate_validator(
    predicate: Callable[[Any], bool | TypeGuard[Any]],
    exception: type[BaseException],
    message: str | None,
    /,
) -> Callable[[Any], None]:
    if not message:
        message = "Invalid value"

    def predicate_validator(val: Any) -> None:
        if not predicate(val):
            raise exception(message)

    return predicate_validator


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
    def __init__(
        self,
        known_options: Sequence[str],
        parents: Sequence[_ConfigInfoTemplate],
    ) -> None:
        self.parents: tuple[_ConfigInfoTemplate, ...] = tuple(parents)
        self.options: frozenset[str] = frozenset(known_options)
        self.sections: dict[str, _SectionBuildPayload] = dict()
        self.main_update_hooks: set[Callable[[object], None]] = set()
        self.option_update_hooks: dict[str, set[Callable[[object], None]]] = dict()
        self.option_delete_hooks: dict[str, set[Callable[[object], None]]] = dict()
        self.option_value_update_hooks: dict[str, set[Callable[[object, Any], None]]] = dict()
        self.section_update_hooks: dict[str, set[Callable[[object], None]]] = dict()
        self.value_descriptor: dict[str, _Descriptor] = dict()
        self.value_converter_on_get: dict[str, list[Callable[[object, Any], Any]]] = dict()
        self.value_converter_on_set: dict[str, list[Callable[[object, Any], Any]]] = dict()
        self.value_validator: dict[str, list[Callable[[object, Any], None]]] = dict()
        self.aliases: dict[str, str] = dict()

        merge_dict = self.__merge_dict
        merge_updater_dict = self.__merge_updater_dict
        merge_sections_dict = self.__merge_sections_dict
        for p in parents:
            self.options |= p.options
            merge_sections_dict(self.sections, p.sections)
            self.main_update_hooks |= p.main_update_hooks
            merge_updater_dict(self.option_update_hooks, p.option_update_hooks)
            merge_updater_dict(self.option_delete_hooks, p.option_delete_hooks)
            merge_updater_dict(self.option_value_update_hooks, p.option_value_update_hooks)
            merge_updater_dict(self.section_update_hooks, p.section_update_hooks)
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

        for section in self.sections:
            if section in self.options:
                raise ConfigurationError(f"{section!r}: An option and a section shares the same name")

        self.parent_descriptors: frozenset[_Descriptor] = frozenset(self.value_descriptor.values())

    @staticmethod
    def __merge_dict(
        d1: dict[_KT, _VT],
        d2: dict[_KT, _VT],
        /,
        *,
        on_conflict: Literal["override", "raise", "skip"] | Callable[[_KT, _VT, _VT], _VT],
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

    @classmethod
    def __merge_sections_dict(
        cls,
        d1: dict[str, _SectionBuildPayload],
        d2: dict[str, _SectionBuildPayload],
    ) -> None:
        def section_conflict(key: str, s1: _SectionBuildPayload, s2: _SectionBuildPayload) -> _SectionBuildPayload:
            try:
                return s1.merge(s2)
            except ConfigurationError as exc:
                raise ConfigurationError(f"Conflict of setting 'sections' for {key!r} key: {exc}") from None

        return cls.__merge_dict(d1, d2, on_conflict=section_conflict, setting="sections")

    def build(self, owner: type) -> ConfigurationInfo[Any]:
        self.__intern_build_all_wrappers(owner)
        self.__set_default_value_descriptors(owner)

        return ConfigurationInfo(
            options=self.__build_options_set(),
            sections=self.__build_sections_list(),
            option_value_update_hooks=self.__build_option_value_update_hooks_dict(),
            option_delete_hooks=self.__build_option_delete_hooks_dict(),
            option_update_hooks=self.__build_option_update_hooks_dict(),
            section_update_hooks=self.__build_section_update_hooks_dict(),
            main_object_update_hooks=self.__build_main_object_update_hooks_set(),
            value_converter_on_get=self.__build_value_converter_dict(on="get"),
            value_converter_on_set=self.__build_value_converter_dict(on="set"),
            value_validator=self.__build_value_validator_dict(),
            value_descriptor=self.__build_value_descriptor_dict(owner),
            aliases=self.__build_aliases_dict(),
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

        def build_update_hooks_wrappers(attr_name: str) -> None:
            hooks_dict: dict[str, set[Callable[[object], None]]] = getattr(self, attr_name)
            setattr(
                self,
                attr_name,
                {option: set(build_wrapper_if_needed(func) for func in func_set) for option, func_set in hooks_dict.items()},
            )

        self.main_update_hooks = set(build_wrapper_if_needed(func) for func in self.main_update_hooks)
        build_update_hooks_wrappers("option_update_hooks")
        build_update_hooks_wrappers("option_delete_hooks")
        build_update_hooks_wrappers("option_value_update_hooks")
        build_update_hooks_wrappers("section_update_hooks")
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

    def __build_options_set(self) -> frozenset[str]:
        return frozenset(self.options)

    def __build_sections_list(self) -> Sequence[Section[object, Any]]:
        return tuple(
            Section(
                name,
                section.func,
                include_options=frozenset(section.include_options),
                exclude_options=frozenset(section.exclude_options),
            )
            for name, section in self.sections.items()
        )

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

    def __build_section_update_hooks_dict(self) -> MappingProxyType[str, frozenset[Callable[[object], None]]]:
        return MappingProxyType(
            {
                option: frozenset(filtered_hooks)
                for option, hooks in self.section_update_hooks.items()
                if len((filtered_hooks := hooks.difference(self.main_update_hooks))) > 0
            }
        )

    def __build_main_object_update_hooks_set(self) -> frozenset[Callable[[object], None]]:
        return frozenset(self.main_update_hooks)

    def __build_value_converter_dict(
        self, *, on: Literal["get", "set"]
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
                if underlying_descriptor is None:
                    underlying_descriptor = _PrivateAttributeOptionProperty()
                    underlying_descriptor.__set_name__(owner, option)
                    descriptor.set_new_descriptor(underlying_descriptor)
                descriptor = underlying_descriptor
            value_descriptors[option] = descriptor

        return MappingProxyType(value_descriptors)

    def __build_aliases_dict(self) -> MappingProxyType[str, str]:
        return MappingProxyType(self.aliases.copy())

    def __build_readonly_options_set(self) -> frozenset[str]:
        return frozenset(
            option for option, descriptor in self.value_descriptor.items() if isinstance(descriptor, _ReadOnlyOptionBuildPayload)
        )


class _ConfigInitializer:

    __slots__ = ("__func__", "__config_name")

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

        if not config_name:
            raise TypeError("__set_name__() not called (probably because of decorators above @initializer)")

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
    if TYPE_CHECKING:

        def getter(self, __fget: Callable[[Any], Any]) -> _ConfigProperty:
            ...

        def setter(self, __fset: Callable[[Any, Any], None]) -> _ConfigProperty:
            ...

        def deleter(self, __fdel: Callable[[Any], None]) -> _ConfigProperty:
            ...


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


@dataclass(eq=True, unsafe_hash=True)
class _SectionBuildPayload:
    func: Callable[[Any], Configuration[Any]]
    include_options: tuple[str, ...]
    exclude_options: tuple[str, ...]

    def __post_init__(self) -> None:
        for attr in ("include_options", "exclude_options"):
            object.__setattr__(self, attr, tuple(sorted(set(map(str, getattr(self, attr))))))
        if options_conflict := set(self.include_options).intersection(self.exclude_options):
            raise ConfigurationError(f"{', '.join(map(repr, options_conflict))} force included and excluded")

    def merge(self, other: _SectionBuildPayload) -> _SectionBuildPayload:
        from dataclasses import replace

        for s1, s2 in ((self, other), (other, self)):
            if options_conflict := set(s1.include_options).intersection(s2.exclude_options):
                raise ConfigurationError(f"{', '.join(map(repr, options_conflict))} force included in self and excluded in other")

        changes: dict[str, Any] = {}

        for name in ["include_options", "exclude_options"]:
            if getattr(self, name) is None and getattr(other, name) is None:
                continue
            changes[name] = tuple(chain(getattr(self, name), getattr(other, name)))

        for name in ["func"]:
            if getattr(self, name) != getattr(other, name):
                raise ConfigurationError("config getters are different")

        return replace(self, **changes)
