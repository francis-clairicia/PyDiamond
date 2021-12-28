# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Configuration module"""

from __future__ import annotations

__all__ = [
    "BoundConfiguration",
    "ConfigError",
    "Configuration",
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
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from contextlib import ExitStack, contextmanager, suppress
from copy import copy, deepcopy
from enum import Enum
from functools import cache, wraps
from types import BuiltinFunctionType, BuiltinMethodType, MethodType
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    FrozenSet,
    Generic,
    Iterable,
    Iterator,
    List,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
    runtime_checkable,
)

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
_NoDefault: Any = object()


class ConfigError(Exception):
    pass


class OptionError(ConfigError):
    def __init__(self, /, name: str, message: str) -> None:
        if name:
            message = f"{name!r}: {message}"
        super().__init__(message)
        self.name: str = name


class UnknownOptionError(OptionError):
    def __init__(self, /, name: str) -> None:
        super().__init__(name, "Unknown config option")


class UnregisteredOptionError(OptionError):
    def __init__(self, /, name: str) -> None:
        super().__init__(name, "Unregistered option")


class EmptyOptionNameError(OptionError):
    def __init__(self, /) -> None:
        super().__init__("", "Empty string option given")


class InvalidAliasError(OptionError):
    def __init__(self, /, name: str, message: str) -> None:
        super().__init__(name, message)


class InitializationError(ConfigError):
    def __init__(self, message: str) -> None:
        super().__init__(message)


def initializer(func: _Func) -> _Func:
    return cast(_Func, _ConfigInitializer(func))


class Configuration:
    __update_stack: ClassVar[Dict[object, List[str]]] = dict()
    __init_context: ClassVar[Dict[object, _InitializationRegister]] = dict()

    def __init__(
        self,
        /,
        *known_options: str,
        autocopy: Optional[bool] = None,
        parent: Optional[Union[Configuration, Sequence[Configuration]]] = None,
    ) -> None:
        if any(not option for option in known_options):
            raise ValueError("Configuration option must not be empty")
        if parent is None:
            parent = []
        elif isinstance(parent, Configuration):
            parent = [parent]
        else:
            parent = list(dict.fromkeys(parent))

        self.__all_parents: Tuple[Configuration, ...] = tuple(parent)
        self.__info: _ConfigInfo = _ConfigInfo(known_options, autocopy, list(p.__info for p in parent))
        self.__no_parent_ownership: Set[str] = set()
        self.__bound_class: Optional[type] = None

    def __repr__(self, /) -> str:
        return f"{type(self).__name__}({{{', '.join(repr(s) for s in sorted(self.known_options()))}}})"

    def __set_name__(self, owner: type, name: str, /) -> None:
        if self.__bound_class is not None:
            raise TypeError(f"This configuration object is bound to an another class: {self.__bound_class.__name__!r}")
        if getattr(owner, name) is not self:
            raise AttributeError("The attribute name does not correspond")
        self.__bound_class = owner
        info: _ConfigInfo = self.__info
        attribute_class_owner: Dict[str, type] = info.attribute_class_owner
        no_parent_ownership: Set[str] = self.__no_parent_ownership
        for option in info.options:
            if option in no_parent_ownership:
                attribute_class_owner[option] = owner
            else:
                attribute_class_owner[option] = attribute_class_owner.get(option, owner)
            descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
            if hasattr(descriptor, "__set_name__"):
                getattr(descriptor, "__set_name__")(attribute_class_owner[option], option)
        former_config: Optional[Configuration] = _register_configuration(owner, self)
        for obj in _all_members(owner).values():
            if isinstance(obj, OptionAttribute):
                with suppress(AttributeError):
                    self.check_option_validity(obj.name)
            elif isinstance(obj, Configuration) and obj is not self:
                _register_configuration(owner, former_config)
                raise TypeError(f"A class can't have several {Configuration.__name__!r} objects")

    def known_options(self, /) -> FrozenSet[str]:
        return self.__info.options

    def known_aliases(self, /) -> FrozenSet[str]:
        return frozenset(self.__info.aliases)

    def check_option_validity(self, /, option: str, *, use_alias: bool = False) -> str:
        info = self.__info
        if use_alias:
            option = info.aliases.get(option, option)
        if option not in info.options:
            if not option:
                raise EmptyOptionNameError()
            raise UnknownOptionError(option)
        return option

    def is_option_valid(self, /, option: str, *, use_alias: bool = False) -> bool:
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
        info: _ConfigInfo = self.__info
        if isinstance(arg1, bool) and not kwargs:
            info.autocopy = arg1
        elif isinstance(arg1, str) and ("copy_on_get" in kwargs or "copy_on_set" in kwargs):
            self.check_option_validity(arg1)
            if "copy_on_get" in kwargs:
                copy_on_get: Optional[bool] = kwargs["copy_on_get"]
                if copy_on_get is None:
                    info.value_autocopy_get.pop(arg1, None)
                else:
                    info.value_autocopy_get[arg1] = bool(copy_on_get)
            if "copy_on_set" in kwargs:
                copy_on_set: Optional[bool] = kwargs["copy_on_set"]
                if copy_on_set is None:
                    info.value_autocopy_set.pop(arg1, None)
                else:
                    info.value_autocopy_set[arg1] = bool(copy_on_set)
        else:
            raise TypeError("Invalid argument")

    def remove_parent_ownership(self, /, option: str) -> None:
        self.check_option_validity(option)
        info: _ConfigInfo = self.__info
        self.__no_parent_ownership.add(option)
        if self.__bound_class is not None:
            info.attribute_class_owner[option] = self.__bound_class
            descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
            if hasattr(descriptor, "__set_name__"):
                getattr(descriptor, "__set_name__")(self.__bound_class, option)

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None, /) -> Configuration:
        ...

    @overload
    def __get__(self, obj: _T, objtype: Optional[type] = None, /) -> BoundConfiguration[_T]:
        ...

    def __get__(self, obj: Optional[_T], objtype: Optional[type] = None, /) -> Union[Configuration, BoundConfiguration[_T]]:
        if obj is None:
            return self
        if objtype is not None and objtype is not type(obj):
            config = _retrieve_configuration(objtype)
        else:
            config = self
        return BoundConfiguration(config, obj)

    @overload
    def get(self, /, obj: object, option: str) -> Any:
        ...

    @overload
    def get(self, /, obj: object, option: str, default: _DT) -> Union[Any, _DT]:
        ...

    def get(self, /, obj: object, option: str, default: _DT = _NoDefault) -> Any:
        option = self.check_option_validity(option, use_alias=True)
        info: _ConfigInfo = self.__info
        descr: Optional[_Descriptor] = info.value_descriptors.get(option)
        value: Any
        try:
            if isinstance(descr, _Descriptor):
                value = descr.__get__(obj, type(obj))
            else:
                get_private_attribute = self.__get_option_private_attribute
                try:
                    value = getattr(obj, get_private_attribute(option, type(obj)))
                except AttributeError as exc:
                    raise UnregisteredOptionError(option) from exc
        except OptionError:
            if default is _NoDefault:
                raise
            return default
        if info.enum_return_value.get(option, False) and isinstance(value, Enum):
            return value.value
        if info.value_autocopy_get.get(option, info.autocopy):
            copy_func = info.get_copy_func(type(value))
            with suppress(Exception):
                value = copy_func(value)
        return value

    def has_key(self, obj: object, option: str) -> bool:
        missing = object()
        return self.get(obj, option, missing) is not missing

    def set(self, /, obj: object, option: str, value: Any) -> None:
        option = self.check_option_validity(option, use_alias=True)
        info: _ConfigInfo = self.__info
        descr: Optional[_Descriptor] = info.value_descriptors.get(option)
        value_validator: Optional[Callable[[object, Any], None]] = info.value_validator.get(option)
        converter: Optional[Callable[[object, Any], Any]] = info.value_converter.get(option)
        actual_value: Any
        MISSING: Any = object()

        if callable(value_validator):
            value_validator(obj, value)
        converter_applied: bool = False
        if callable(converter):
            value = converter(obj, value)
            converter_applied = True

        if isinstance(descr, _Descriptor):
            if not isinstance(descr, _MutableDescriptor):
                raise OptionError(option, "Cannot be set")
            _descr: _MutableDescriptor = descr

            def set_value(value: Any) -> None:
                with self.__updating_option(obj, option):
                    _descr.__set__(obj, value)

            try:
                actual_value = descr.__get__(obj, type(obj))
            except (AttributeError, UnregisteredOptionError):
                actual_value = MISSING
        else:
            if option in info.readonly:
                raise OptionError(option, "Cannot be set")
            get_private_attribute = self.__get_option_private_attribute

            def set_value(value: Any) -> None:
                setattr(obj, get_private_attribute(option, type(obj)), value)

            try:
                actual_value = getattr(obj, get_private_attribute(option, type(obj)), MISSING)
            except (AttributeError, UnregisteredOptionError):
                actual_value = MISSING

        if actual_value is MISSING or actual_value != value:
            if not converter_applied and info.value_autocopy_set.get(option, info.autocopy):
                copy_func = info.get_copy_func(type(value))
                with suppress(Exception):
                    value = copy_func(value)
            set_value(value)
            if self.has_initialization_context(obj):
                register = Configuration.__init_context[obj]
                register[option] = value
                return
            for value_update in info.get_option_value_update_funcs(option):
                value_update(obj, value)
            update_stack = Configuration.__update_stack.get(obj, [])
            if option in update_stack:
                return
            main_update_list: List[Callable[[object], None]] = list(info.get_main_update_funcs())
            for update in info.get_option_update_funcs(option):
                if update in main_update_list:
                    continue
                with self.__updating_option(obj, option):
                    update(obj)
            if not update_stack:
                for main_update in main_update_list:
                    main_update(obj)

    def delete(self, /, obj: object, option: str) -> None:
        option = self.check_option_validity(option, use_alias=True)
        info: _ConfigInfo = self.__info
        descr = info.value_descriptors.get(option)
        if isinstance(descr, _Descriptor):
            if not isinstance(descr, _RemovableDescriptor):
                raise OptionError(option, "Cannot be deleted")
            with self.__updating_option(obj, option):
                descr.__delete__(obj)
        else:
            if option in info.readonly:
                raise OptionError(option, "Cannot be deleted")
            get_private_attribute = self.__get_option_private_attribute
            try:
                delattr(obj, get_private_attribute(option, type(obj)))
            except AttributeError as exc:
                raise UnregisteredOptionError(option) from exc

        if self.has_initialization_context(obj):
            register = Configuration.__init_context[obj]
            register.pop(option, None)
            return

        update_stack = Configuration.__update_stack.get(obj, [])
        if option in update_stack:
            return
        main_update_list: List[Callable[[object], None]] = list(info.get_main_update_funcs())
        for update in info.get_option_update_funcs(option):
            if update in main_update_list:
                continue
            with self.__updating_option(obj, option):
                update(obj)
        if not update_stack:
            for main_update in main_update_list:
                main_update(obj)

    def __call__(self, /, __obj: object, **kwargs: Any) -> None:
        if not kwargs:
            return
        if self.has_initialization_context(__obj):
            for option, value in kwargs.items():
                self.set(__obj, option, value)
            return

        info: _ConfigInfo = self.__info
        need_update: List[str] = []
        MISSING: Any = object()

        @contextmanager
        def check_if_update_needed(option: str) -> Iterator[None]:
            nonlocal need_update
            if option in need_update:
                yield
                return
            former_value: Any = self.get(__obj, option, MISSING)
            yield
            actual_value: Any = self.get(__obj, option, MISSING)
            if actual_value is not MISSING and (former_value is MISSING or actual_value != former_value):
                need_update.append(option)

        for option, value in kwargs.items():
            with self.__updating_option(__obj, option), check_if_update_needed(option):
                self.set(__obj, option, value)
        if not need_update:
            return
        update_stack = Configuration.__update_stack.get(__obj, [])
        main_update_list: List[Callable[[object], None]] = list(info.get_main_update_funcs())
        for option in filter(lambda opt: opt in need_update and opt not in update_stack, kwargs):
            for update in info.get_option_update_funcs(option):
                if update in main_update_list:
                    continue
                with self.__updating_option(__obj, option):
                    update(__obj)
        if not update_stack:
            for main_update in main_update_list:
                main_update(__obj)

    def update_all_options(self, /, obj: object) -> None:
        objtype: type = type(obj)
        info: _ConfigInfo = self.__info
        get_private_attribute = self.__get_option_private_attribute

        for option in info.options:
            actual_descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
            value: Any
            with suppress(AttributeError, UnregisteredOptionError):
                if actual_descriptor is not None:
                    value = actual_descriptor.__get__(obj, objtype)
                else:
                    value = getattr(obj, get_private_attribute(option, objtype))
                for value_update in info.get_option_value_update_funcs(option):
                    value_update(obj, value)
        main_update_list: List[Callable[[object], None]] = list(info.get_main_update_funcs())
        for option in info.options:
            for update in info.get_option_update_funcs(option):
                if update in main_update_list:
                    continue
                update(obj)
        for main_update in main_update_list:
            main_update(obj)

    def update_option(self, /, obj: object, option: str) -> None:
        objtype: type = type(obj)
        info: _ConfigInfo = self.__info
        get_private_attribute = self.__get_option_private_attribute

        self.check_option_validity(option)
        actual_descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
        value: Any
        with suppress(AttributeError, UnregisteredOptionError):
            if actual_descriptor is not None:
                value = actual_descriptor.__get__(obj, objtype)
            else:
                value = getattr(obj, get_private_attribute(option, objtype))
            for value_update in info.get_option_value_update_funcs(option):
                value_update(obj, value)
        main_update_list: List[Callable[[object], None]] = list(info.get_main_update_funcs())
        for update in info.get_option_update_funcs(option):
            if update in main_update_list:
                continue
            update(obj)
        for main_update in main_update_list:
            main_update(obj)

    @contextmanager
    def initialization(self, /, obj: object) -> Iterator[None]:
        if self.has_initialization_context(obj):
            yield
            return

        if obj in Configuration.__update_stack:
            raise InitializationError("Cannot use initialization context while updating an option value")

        def cleanup() -> None:
            Configuration.__init_context.pop(obj, None)

        with ExitStack() as stack:
            initialization_register: _InitializationRegister = {}
            Configuration.__init_context[obj] = initialization_register
            stack.callback(cleanup)
            yield
            info: _ConfigInfo = self.__info
            for option, value in initialization_register.items():
                for value_update in info.get_option_value_update_funcs(option):
                    value_update(obj, value)
            main_update_list: List[Callable[[object], None]] = list(info.get_main_update_funcs())
            for option in initialization_register:
                for update in info.get_option_update_funcs(option):
                    if update in main_update_list:
                        continue
                    with self.__updating_option(obj, option):
                        update(obj)
            for main_update in main_update_list:
                main_update(obj)

    @staticmethod
    def has_initialization_context(obj: object) -> bool:
        return obj in Configuration.__init_context

    @overload
    def getter(self, option: str, /, *, use_override: bool = True) -> Callable[[_Getter], _Getter]:
        ...

    @overload
    def getter(self, option: str, func: _Getter, /, *, use_override: bool = True) -> None:
        ...

    def getter(
        self, option: str, func: Optional[_Getter] = None, /, *, use_override: bool = True
    ) -> Optional[Callable[[_Getter], _Getter]]:
        self.check_option_validity(option)
        info: _ConfigInfo = self.__info
        actual_descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
        if actual_descriptor is not None and not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: Optional[_ConfigProperty] = actual_descriptor

        def decorator(func: _Getter, /) -> _Getter:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            if actual_property is None:
                info.value_descriptors[option] = _ConfigProperty(wrapper)
            else:
                info.value_descriptors[option] = actual_property.getter(wrapper)
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def getter_key(self, option: str, /, *, use_override: bool = True) -> Callable[[_KeyGetter], _KeyGetter]:
        ...

    @overload
    def getter_key(self, option: str, /, *, use_key: str, use_override: bool = True) -> Callable[[_KeyGetter], _KeyGetter]:
        ...

    @overload
    def getter_key(self, option: str, func: _KeyGetter, /, *, use_override: bool = True) -> None:
        ...

    @overload
    def getter_key(self, option: str, func: _KeyGetter, /, *, use_key: str, use_override: bool = True) -> None:
        ...

    def getter_key(
        self, option: str, func: Optional[_KeyGetter] = None, /, *, use_key: Optional[str] = None, use_override: bool = True
    ) -> Optional[Callable[[_KeyGetter], _KeyGetter]]:
        def decorator(func: _KeyGetter, /) -> _KeyGetter:
            key: str = use_key if use_key is not None else option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.getter(option, _wrap_function_wrapper(func, lambda self: wrapper(self, key)))
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
        self.check_option_validity(option)
        info: _ConfigInfo = self.__info
        if option in info.readonly:
            raise OptionError(option, "Read-only option")
        actual_descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing setter for this option which has no getter")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _Setter, /) -> _Setter:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            info.value_descriptors[option] = actual_property.setter(wrapper)
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
        def decorator(func: _KeySetter, /) -> _KeySetter:
            key: str = use_key if use_key is not None else option
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
        self.check_option_validity(option)
        info: _ConfigInfo = self.__info
        if option in info.readonly:
            raise OptionError(option, "Read-only option")
        actual_descriptor: Optional[_Descriptor] = info.value_descriptors.get(option)
        if actual_descriptor is None:
            raise OptionError(option, "Attributing deleter for this option which has no getter")
        if not isinstance(actual_descriptor, _ConfigProperty):
            raise OptionError(option, f"Already bound to a descriptor: {type(actual_descriptor).__name__}")
        actual_property: _ConfigProperty = actual_descriptor

        def decorator(func: _Deleter, /) -> _Deleter:
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            info.value_descriptors[option] = actual_property.deleter(wrapper)
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
        def decorator(func: _KeyDeleter, /) -> _KeyDeleter:
            key: str = use_key if use_key is not None else option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.deleter(option, _wrap_function_wrapper(func, lambda self: wrapper(self, key)))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    def use_descriptor(self, /, option: str, descriptor: _Descriptor) -> None:
        self.check_option_validity(option)
        info: _ConfigInfo = self.__info
        if option in info.value_descriptors:
            actual_descriptor: _Descriptor = info.value_descriptors[option]
            if isinstance(actual_descriptor, _ConfigProperty):
                raise OptionError(option, "Already uses custom getter register with getter() method")
            raise OptionError(option, "Already bound to a descriptor: {type(actual_descriptor).__name__}")
        if option in info.readonly and isinstance(descriptor, (_MutableDescriptor, _RemovableDescriptor)):
            if not isinstance(descriptor, property) or descriptor.fset is not None or descriptor.fdel is not None:
                raise OptionError(option, "Read-only option")
        info.value_descriptors[option] = descriptor
        if self.__bound_class is not None and hasattr(descriptor, "__set_name__"):
            getattr(descriptor, "__set_name__")(info.attribute_class_owner[option], option)

    @overload
    def main_update(self, func: _Updater, /, *, use_override: bool = True) -> _Updater:
        ...

    @overload
    def main_update(self, /, *, use_override: bool = True) -> Callable[[_Updater], _Updater]:
        ...

    def main_update(
        self, func: Optional[_Updater] = None, /, *, use_override: bool = True
    ) -> Union[_Updater, Callable[[_Updater], _Updater]]:
        info: _ConfigInfo = self.__info

        def decorator(func: _Updater, /) -> _Updater:
            if info.main_update is not None:
                raise ConfigError("Already has main updater")
            info.main_update = _make_function_wrapper(func, check_override=bool(use_override))
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
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)

        def decorator(func: _Updater, /) -> _Updater:
            if option in info.self_update:
                raise OptionError(option, "Already has updater")
            info.update[option] = _make_function_wrapper(func, check_override=bool(use_override))
            info.self_update[option] = info.update[option]
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
        def decorator(func: _KeyUpdater, /) -> _KeyUpdater:
            key: str = use_key if use_key is not None else option
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
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)

        def decorator(func: _ValueUpdater, /) -> _ValueUpdater:
            if option in info.self_value_update:
                raise OptionError(option, "Already has updater")
            info.value_update[option] = _make_function_wrapper(func, check_override=bool(use_override))
            info.self_value_update[option] = info.value_update[option]
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
        def decorator(func: _KeyValueUpdater, /) -> _KeyValueUpdater:
            key: str = use_key if use_key is not None else option
            wrapper = _make_function_wrapper(func, check_override=bool(use_override))
            self.on_update_value(option, _wrap_function_wrapper(func, lambda self, value: wrapper(self, key, value)))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def value_validator(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueValidator], _ValueValidator]:
        ...

    @overload
    def value_validator(self, option: str, func: _ValueValidator, /, *, use_override: bool = True) -> None:
        ...

    def value_validator(
        self,
        option: str,
        func: Optional[_ValueValidator] = None,
        /,
        *,
        use_override: bool = True,
    ) -> Optional[Callable[[_ValueValidator], _ValueValidator]]:
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use value_validator_static() to check types")

        def decorator(func: _ValueValidator, /) -> _ValueValidator:
            info.value_validator[option] = _make_function_wrapper(func, check_override=bool(use_override))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def value_validator_static(self, option: str, /) -> Callable[[_StaticValueValidator], _StaticValueValidator]:
        ...

    @overload
    def value_validator_static(self, option: str, objtype: type, /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def value_validator_static(self, option: str, objtypes: Sequence[type], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def value_validator_static(self, option: str, func: _StaticValueValidator, /) -> None:
        ...

    def value_validator_static(
        self,
        option: str,
        func: Optional[Union[_StaticValueValidator, type, Sequence[type]]] = None,
        /,
        *,
        accept_none: bool = False,
    ) -> Optional[Callable[[_StaticValueValidator], _StaticValueValidator]]:
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)

        def decorator(func: _StaticValueValidator, /) -> _StaticValueValidator:
            info.value_validator[option] = _make_function_wrapper(func, check_override=False, no_object=True)
            return func

        if isinstance(func, (type, Sequence)):
            _type: Union[type, Tuple[type, ...]] = func if isinstance(func, type) else tuple(func)

            if isinstance(_type, tuple):
                if not _type or any(not isinstance(t, type) for t in _type):
                    raise TypeError("Invalid types argument")
                if len(_type) == 1:
                    _type = _type[0]

            def type_checker(val: Any, /) -> None:
                if (accept_none and val is None) or isinstance(val, _type):
                    return
                expected: str
                if isinstance(_type, type):
                    expected = repr(_type.__qualname__)
                else:
                    expected = f"one of those: ({', '.join(repr(t.__qualname__) for t in _type)})"
                cls: type = type(val)
                got: str = repr(cls.__qualname__ if cls.__module__ != object.__module__ else val)
                raise TypeError(f"Invalid value type. expected {expected}, got {got}")

            decorator(cast(_StaticValueValidator, type_checker))
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def value_converter(self, option: str, /, *, use_override: bool = True) -> Callable[[_ValueConverter], _ValueConverter]:
        ...

    @overload
    def value_converter(self, option: str, func: _ValueConverter, /, *, use_override: bool = True) -> None:
        ...

    def value_converter(
        self,
        option: str,
        func: Optional[_ValueConverter] = None,
        /,
        *,
        use_override: bool = True,
    ) -> Optional[Callable[[_ValueConverter], _ValueConverter]]:
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)

        if isinstance(func, type):
            raise TypeError("Use value_converter_static() to convert value using type")

        def decorator(func: _ValueConverter) -> _ValueConverter:
            info.value_converter[option] = _make_function_wrapper(func, check_override=bool(use_override))
            return func

        if func is None:
            return decorator
        decorator(func)
        return None

    @overload
    def value_converter_static(self, option: str, /) -> Callable[[_StaticValueConverter], _StaticValueConverter]:
        ...

    @overload
    def value_converter_static(self, option: str, convert_to_type: Type[Any], /, *, accept_none: bool = False) -> None:
        ...

    @overload
    def value_converter_static(self, option: str, func: _StaticValueConverter, /) -> None:
        ...

    def value_converter_static(
        self, option: str, func: Optional[Union[_StaticValueConverter, type]] = None, /, *, accept_none: bool = False
    ) -> Optional[Callable[[_StaticValueConverter], _StaticValueConverter]]:
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)

        def decorator(func: _StaticValueConverter, /) -> _StaticValueConverter:
            info.value_converter[option] = _make_function_wrapper(func, check_override=False, no_object=True)
            return func

        if isinstance(func, type):
            _type: Callable[[Any], Any] = func

            def value_converter(val: Any) -> Any:
                if accept_none and val is None:
                    return None
                return _type(val)

            decorator(cast(_StaticValueConverter, value_converter))
            return None

        if func is None:
            return decorator
        decorator(func)
        return None

    def enum(self, /, option: str, enum: Type[Enum], *, return_value: bool = False) -> None:
        self.value_converter_static(option, enum)
        self.__info.enum_return_value[option] = bool(return_value)

    def set_alias(self, /, option: str, alias: str) -> None:
        info: _ConfigInfo = self.__info
        self.check_option_validity(option)
        if not isinstance(alias, str):
            raise InvalidAliasError(alias, "Invalid type")
        if alias == option:
            raise InvalidAliasError(alias, "Same name with option")
        if not alias:
            raise InvalidAliasError(alias, "Empty string alias")
        if alias in info.options:
            raise InvalidAliasError(alias, "Alias name is a configuration option")
        aliases: Dict[str, str] = info.aliases
        if alias in aliases:
            raise InvalidAliasError(alias, f"Already bound to option {aliases[alias]!r}")
        aliases[alias] = option

    def remove_alias(self, /, alias: str) -> None:
        aliases: Dict[str, str] = self.__info.aliases
        aliases.pop(alias)

    def remove_all_aliases(self, /, option: str) -> None:
        self.check_option_validity(option)
        aliases: Dict[str, str] = self.__info.aliases
        for alias, opt in list(aliases.items()):
            if opt == option:
                aliases.pop(alias)

    def register_copy_func(self, /, cls: type, func: Callable[[Any], Any], *, allow_subclass: bool = False) -> None:
        if not isinstance(cls, type):
            raise TypeError("'cls' argument must be a type")
        if not callable(func):
            raise TypeError("'func' is not callable")
        info: _ConfigInfo = self.__info
        info.value_copy[cls] = func
        info.value_copy_allow_subclass[cls] = bool(allow_subclass)

    def remove_copy_func(self, /, cls: type) -> None:
        info: _ConfigInfo = self.__info
        info.value_copy.pop(cls, None)
        info.value_copy_allow_subclass.pop(cls, None)

    def readonly(self, /, *options: str) -> None:
        info: _ConfigInfo = self.__info
        parents: Tuple[Configuration, ...] = self.__parents__
        for option in options:
            self.check_option_validity(option)
            if not parents or not any(option in p.known_options() for p in parents):
                descriptor = info.value_descriptors.get(option)
                if not isinstance(descriptor, (_MutableDescriptor, _RemovableDescriptor)):
                    continue
                if not isinstance(descriptor, property) or descriptor.fset is not None or descriptor.fdel is not None:
                    raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            info.readonly.add(option)

    def __get_option_private_attribute(self, /, option: str, objtype: type) -> str:
        owner: type
        infos: _ConfigInfo = self.__info
        config_owner: Optional[type] = self.__bound_class
        if objtype is config_owner:
            owner = infos.attribute_class_owner.get(option, objtype)
        else:
            owner = objtype
        return f"_{owner.__name__}__{option}"

    @staticmethod
    @contextmanager
    def __updating_option(obj: object, option: str) -> Iterator[None]:
        if Configuration.has_initialization_context(obj):
            yield
            return

        update_stack: List[str]
        Configuration.__update_stack[obj] = update_stack = Configuration.__update_stack.get(obj, [])
        if option in update_stack:
            yield
            return

        def cleanup() -> None:
            with suppress(ValueError):
                update_stack.remove(option)
            if not update_stack:
                Configuration.__update_stack.pop(obj, None)

        with ExitStack() as stack:
            stack.callback(cleanup)
            update_stack.append(option)
            yield

    @property
    def __parents__(self) -> Tuple[Configuration, ...]:
        return self.__all_parents


class OptionAttribute(Generic[_T]):
    def __set_name__(self, owner: type, name: str, /) -> None:
        if len(name) == 0:
            raise ValueError("Attribute name must not be empty")
        with suppress(AttributeError):
            if self.__name != name:
                raise ValueError(f"Assigning {self.__name!r} config attribute to {name}")
        self.__name: str = name
        config: Configuration = _retrieve_configuration(owner)
        config.check_option_validity(name, use_alias=True)

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None, /) -> OptionAttribute[_T]:
        ...

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> _T:
        ...

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Union[_T, OptionAttribute[_T]]:
        if obj is None:
            return self
        name: str = self.__name
        config: Configuration = _retrieve_configuration(objtype if objtype is not None else type(obj))
        try:
            value: _T = config.get(obj, name)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from exc
        return value

    def __set__(self, obj: object, value: _T, /) -> None:
        name: str = self.__name
        config: Configuration = _retrieve_configuration(type(obj))
        try:
            config.set(obj, name, value)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from exc

    def __delete__(self, obj: object, /) -> None:
        name: str = self.__name
        config: Configuration = _retrieve_configuration(type(obj))
        try:
            config.delete(obj, name)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from exc

    @property
    def name(self, /) -> str:
        return self.__name


_InitializationRegister = Dict[str, Any]


class BoundConfiguration(MutableMapping[str, Any], Generic[_T]):
    def __init__(self, /, config: Configuration, obj: _T) -> None:
        super().__init__()
        self.__config: Callable[[], Configuration] = lambda: config
        self.__obj: _T = obj

    def __iter__(self, /) -> Iterator[str]:
        return iter(self.known_options())

    def __len__(self, /) -> int:
        return len(self.known_options())

    def known_options(self, /) -> FrozenSet[str]:
        config = self.__config()
        return config.known_options()

    def known_aliases(self, /) -> FrozenSet[str]:
        config = self.__config()
        return config.known_aliases()

    def check_option_validity(self, /, option: str, *, use_alias: bool = False) -> str:
        config = self.__config()
        return config.check_option_validity(option, use_alias=use_alias)

    def is_option_valid(self, /, option: str, *, use_alias: bool = False) -> bool:
        config = self.__config()
        return config.is_option_valid(option, use_alias=use_alias)

    def __getitem__(self, option: str, /) -> Any:
        try:
            return self.get(option)
        except OptionError as exc:
            raise KeyError from exc

    @overload
    def get(self, option: str, /) -> Any:
        ...

    @overload
    def get(self, option: str, default: _DT, /) -> Union[Any, _DT]:
        ...

    def get(self, option: str, default: _DT = _NoDefault, /) -> Union[Any, _DT]:
        config = self.__config()
        obj = self.__obj
        return config.get(obj, option, default)

    def __setitem__(self, option: str, value: Any, /) -> None:
        try:
            self.set(option, value)
        except OptionError as exc:
            raise KeyError from exc

    def set(self, /, option: str, value: Any) -> None:
        config = self.__config()
        obj = self.__obj
        return config.set(obj, option, value)

    def __delitem__(self, option: str, /) -> None:
        try:
            return self.delete(option)
        except OptionError as exc:
            raise KeyError from exc

    def delete(self, /, option: str) -> None:
        config = self.__config()
        obj = self.__obj
        return config.delete(obj, option)

    def __call__(self, /, **kwargs: Any) -> None:
        config = self.__config()
        obj = self.__obj
        return config(obj, **kwargs)

    @overload
    def update(self, __m: Mapping[str, Any], /, **kwargs: Any) -> None:
        ...

    @overload
    def update(self, __m: Iterable[Tuple[str, Any]], /, **kwargs: Any) -> None:
        ...

    @overload
    def update(self, /, **kwargs: Any) -> None:
        ...

    def update(self, __m: Union[Mapping[str, Any], Iterable[Tuple[str, Any]]] = (), /, **kwargs: Any) -> None:
        options: Dict[str, Any] = {}
        if isinstance(__m, Mapping):
            for key in __m:
                options[key] = __m[key]
        else:
            for key, value in __m:
                options[key] = value
        options.update(kwargs)
        config = self.__config()
        obj = self.__obj
        if not options:
            return config.update_all_options(obj)
        return config(obj, **options)

    def update_all_options(self, /) -> None:
        config = self.__config()
        obj = self.__obj
        return config.update_all_options(obj)

    def update_option(self, /, option: str) -> None:
        config = self.__config()
        obj = self.__obj
        return config.update_option(obj, option)

    @contextmanager
    def initialization(self, /) -> Iterator[None]:
        config = self.__config()
        obj = self.__obj
        with config.initialization(obj) as out:
            yield out

    def has_initialization_context(self, /) -> bool:
        obj = self.__obj
        return Configuration.has_initialization_context(obj)

    @property
    def __self__(self, /) -> _T:
        return self.__obj


def _no_type_check_cache(func: _Func) -> _Func:
    return cast(_Func, cache(func))


@_no_type_check_cache
def _make_function_wrapper(func: Any, *, check_override: bool = True, no_object: bool = False) -> Callable[..., Any]:
    if getattr(func, "__boundconfiguration_wrapper__", False):
        return cast(Callable[..., Any], func)

    if not isinstance(func, (BuiltinFunctionType, BuiltinMethodType)):

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            _func: Callable[..., Any]
            if no_object and callable(func):
                _func = func
            else:
                _func = getattr(func, "__get__", lambda *args: func)(self, type(self))
                if _func is func and not no_object:
                    _func = MethodType(func, self)
            if check_override and _can_be_overriden(_func):
                _func = getattr(self, _func.__name__, _func)
            return _func(*args, **kwargs)

    else:

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

    setattr(wrapper, "__boundconfiguration_wrapper__", True)
    return wrapper


_LAMBDA_FUNC_NAME = (lambda: None).__name__


def _can_be_overriden(func: Callable[..., Any]) -> bool:
    name: str = func.__name__
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
    return _make_function_wrapper(wrapper, check_override=False)


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


def _all_members(cls: type) -> Dict[str, Any]:
    mro: List[type] = _get_cls_mro(cls)
    mro.reverse()
    members: Dict[str, Any] = dict()
    for cls in mro:
        members.update(vars(cls))
    return members


def _register_configuration(cls: type, config: Optional[Configuration]) -> Optional[Configuration]:
    if not isinstance(cls, type):
        raise TypeError(f"{cls} is not a type")
    former_config: Optional[Configuration] = None
    with suppress(TypeError):
        former_config = _retrieve_configuration(cls)
    if isinstance(config, Configuration):
        setattr(cls, "_bound_configuration_", config)
    else:
        with suppress(AttributeError):
            delattr(cls, "_bound_configuration_")
    return former_config


def _retrieve_configuration(cls: type) -> Configuration:
    try:
        if not isinstance(cls, type):
            raise TypeError(f"{cls} is not a type")
        config: Configuration = getattr(cls, "_bound_configuration_")
        if not isinstance(config, Configuration):
            raise AttributeError
    except AttributeError:
        raise TypeError(f"{cls.__name__} does not have a {Configuration.__name__} object") from None
    return config


@runtime_checkable
class _Descriptor(Protocol):
    def __get__(self, obj: object, objtype: Optional[type], /) -> Any:
        pass


@runtime_checkable
class _MutableDescriptor(_Descriptor, Protocol):
    def __set__(self, obj: object, value: Any, /) -> None:
        pass


@runtime_checkable
class _RemovableDescriptor(_Descriptor, Protocol):
    def __delete__(self, obj: object, /) -> None:
        pass


_KT = TypeVar("_KT")
_VT = TypeVar("_VT")


class _ConfigInfo:
    def __init__(self, /, known_options: Sequence[str], autocopy: Optional[bool], parents: Sequence[_ConfigInfo]) -> None:
        def merge_dict(
            d1: Dict[_KT, _VT], d2: Dict[_KT, _VT], /, *, on_conflict: Literal["override", "raise", "skip"], setting: str
        ) -> None:
            for key, value in d2.items():
                if key in d1:
                    if d1[key] == value or on_conflict == "skip":
                        continue
                    if on_conflict == "raise":
                        raise ConfigError(f"Conflict of setting {setting!r} for {key!r}")
                d1[key] = value

        self.parents: Tuple[_ConfigInfo, ...] = tuple(parents)
        self.options: FrozenSet[str] = frozenset(known_options)
        self.main_update: Optional[Callable[[object], None]] = None
        self.value_descriptors: Dict[str, _Descriptor] = dict()
        self.update: Dict[str, Callable[[object], None]] = dict()
        self.self_update: Dict[str, Callable[[object], None]] = dict()
        self.value_converter: Dict[str, Callable[[object, Any], Any]] = dict()
        self.value_update: Dict[str, Callable[[object, Any], None]] = dict()
        self.self_value_update: Dict[str, Callable[[object, Any], None]] = dict()
        self.value_validator: Dict[str, Callable[[object, Any], None]] = dict()
        self.autocopy: bool = autocopy or False
        self.value_autocopy_get: Dict[str, bool] = dict()
        self.value_autocopy_set: Dict[str, bool] = dict()
        self.attribute_class_owner: Dict[str, type] = dict()
        self.aliases: Dict[str, str] = dict()
        self.value_copy: Dict[type, Callable[[Any], Any]] = dict()
        self.value_copy_allow_subclass: Dict[type, bool] = dict()
        self.enum_return_value: Dict[str, bool] = dict()
        self.readonly: Set[str] = set()

        checked_readonly_options: List[str] = []
        for p in parents:
            self.options |= p.options
            merge_dict(self.value_descriptors, p.value_descriptors, on_conflict="raise", setting="descriptor")
            merge_dict(self.value_converter, p.value_converter, on_conflict="raise", setting="value_converter")
            merge_dict(self.value_validator, p.value_validator, on_conflict="raise", setting="value_validator")
            if autocopy is not None:
                self.autocopy |= p.autocopy
            merge_dict(self.value_autocopy_get, p.value_autocopy_get, on_conflict="skip", setting="autocopy_get")
            merge_dict(self.value_autocopy_set, p.value_autocopy_set, on_conflict="skip", setting="autocopy_set")
            merge_dict(self.attribute_class_owner, p.attribute_class_owner, on_conflict="skip", setting="class_owner")
            merge_dict(self.aliases, p.aliases, on_conflict="raise", setting="aliases")
            merge_dict(self.value_copy, p.value_copy, on_conflict="raise", setting="value_copy_func")
            merge_dict(
                self.value_copy_allow_subclass, p.value_copy_allow_subclass, on_conflict="raise", setting="copy_allow_subclass"
            )
            merge_dict(self.enum_return_value, p.enum_return_value, on_conflict="raise", setting="enum_return_value")
            readonly = self.readonly | p.readonly
            for option in filter(lambda option: option not in checked_readonly_options, readonly):
                checked_readonly_options.append(option)
                descriptor = self.value_descriptors.get(option)
                if not isinstance(descriptor, (_MutableDescriptor, _RemovableDescriptor)):
                    continue
                if not isinstance(descriptor, property) or descriptor.fset is not None or descriptor.fdel is not None:
                    raise OptionError(option, "Trying to flag option as read-only with custom setter/deleter")
            self.readonly = readonly

    def get_main_update_funcs(self, /) -> Iterator[Callable[[object], None]]:
        def get_iterator() -> Iterator[Callable[[object], None]]:
            for parent in self.parents:
                yield from parent.get_main_update_funcs()
            main_update = self.main_update
            if callable(main_update):
                yield main_update

        yield from dict.fromkeys(get_iterator())

    def get_option_update_funcs(self, /, option: str) -> Iterator[Callable[[object], None]]:
        def get_iterator() -> Iterator[Callable[[object], None]]:
            for parent in self.parents:
                yield from parent.get_option_update_funcs(option)
            update_func = self.update.get(option)
            if callable(update_func):
                yield update_func

        yield from dict.fromkeys(get_iterator())

    def get_option_value_update_funcs(self, /, option: str) -> Iterator[Callable[[object, Any], None]]:
        def get_iterator() -> Iterator[Callable[[object, Any], None]]:
            for parent in self.parents:
                yield from parent.get_option_value_update_funcs(option)
            update_func = self.value_update.get(option)
            if callable(update_func):
                yield update_func

        yield from dict.fromkeys(get_iterator())

    def get_copy_func(self, /, cls: type) -> Callable[[Any], Any]:
        try:
            return self.value_copy[cls]
        except KeyError:
            if self.value_copy_allow_subclass.get(cls, False):
                for _type, func in self.value_copy.items():
                    if issubclass(cls, _type):
                        return func
        return _copy_object


def _copy_object(obj: _T) -> _T:
    try:
        return deepcopy(obj)
    except:
        return copy(obj)


class _ConfigInitializer:
    def __init__(self, /, func: Callable[..., Any]) -> None:
        self.__func__: Callable[..., Any] = func

    @property
    def __call__(self, /) -> Callable[..., Any]:
        return self.__func__

    def __getattr__(self, /, name: str) -> Any:
        func: Any = self.__func__
        return getattr(func, name)

    def __get__(self, obj: object, objtype: Optional[type] = None, /) -> Callable[..., Any]:
        func: Callable[..., Any] = self.__func__
        try:
            func_get = getattr(func, "__get__")
        except AttributeError:
            if obj is not None:
                func = MethodType(func, obj)
        else:
            func = func_get(obj, objtype)
        if obj is None:
            return func
        config: Configuration = _retrieve_configuration(objtype if objtype is not None else type(obj))

        @wraps(self.__func__)
        def config_initializer(self: object, /, *args: Any, **kwargs: Any) -> Any:
            with config.initialization(self):
                return func(*args, **kwargs)

        return MethodType(config_initializer, obj)

    @property
    def __wrapped__(self) -> Callable[..., Any]:
        return self.__func__


class _ConfigProperty(property):
    pass


import copyreg

copyreg.pickle(_ConfigProperty, lambda p: (_ConfigProperty, (p.fget, p.fset, p.fdel, p.__doc__)))  # type: ignore

del copyreg
