# -*- coding: Utf-8 -*

from __future__ import annotations
from functools import cache, wraps
from operator import truth
from types import BuiltinFunctionType, BuiltinMethodType
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Generic,
    Iterator,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    overload,
)
from enum import Enum
from copy import deepcopy
from contextlib import ExitStack, contextmanager, suppress

__all__ = [
    "Configuration",
    "ConfigTemplate",
    "ConfigAttribute",
    "no_object",
    "initializer",
    "OptionError",
    "UnknownOptionError",
    "UnregisteredOptionError",
    "EmptyOptionNameError",
    "InvalidAliasError",
]


_T = TypeVar("_T")

_Func = TypeVar("_Func", bound=Callable[..., Any])
_Updater = TypeVar("_Updater", bound=Union[Callable[[Any], None], Callable[[], None]])
_Getter = TypeVar("_Getter", bound=Union[Callable[[Any, str], Any], Callable[[str], Any]])
_Setter = TypeVar("_Setter", bound=Union[Callable[[Any, str, Any], None], Callable[[str, Any], None]])
_Deleter = TypeVar("_Deleter", bound=Union[Callable[[Any, str], None], Callable[[str], None]])
_NoNameGetter = TypeVar("_NoNameGetter", bound=Union[Callable[[Any], Any], Callable[[], Any]])
_NoNameSetter = TypeVar("_NoNameSetter", bound=Union[Callable[[Any, Any], None], Callable[[Any], None]])
_NoNameDeleter = TypeVar("_NoNameDeleter", bound=Union[Callable[[Any], None], Callable[[], None]])
_ValueUpdater = TypeVar("_ValueUpdater", bound=Union[Callable[[Any, str, Any], None], Callable[[str, Any], None]])
_NoNameValueUpdater = TypeVar("_NoNameValueUpdater", bound=Union[Callable[[Any, Any], None], Callable[[Any], None]])
_ValueValidator = TypeVar("_ValueValidator", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])
_ValueConverter = TypeVar("_ValueConverter", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])


class OptionError(Exception):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(message)
        self.name: str = name


class UnknownOptionError(OptionError):
    def __init__(self, name: str) -> None:
        super().__init__(name, f"Unknown config option {name!r}")


class UnregisteredOptionError(OptionError):
    def __init__(self, name: str) -> None:
        super().__init__(name, f"Unregistered option {name!r}")


class EmptyOptionNameError(OptionError):
    def __init__(self) -> None:
        super().__init__("", "Empty string option given")


class InvalidAliasError(OptionError):
    def __init__(self, name: str, message: str) -> None:
        super().__init__(name, message)


def initializer(func: _Func) -> _Func:
    return cast(_Func, _ConfigInitializer(func))


def no_object(func: _Func) -> _Func:
    setattr(func, "__no_object__", True)
    return func


class Configuration:
    class Infos:
        def __init__(self, known_options: Sequence[str], autocopy: bool) -> None:
            self.options: FrozenSet[str] = frozenset(known_options)
            self.main_update: Optional[Callable[[object], None]] = None
            self.update: Dict[str, Callable[[object], None]] = dict()
            self.value_getter: Dict[str, Callable[[object, str], Any]] = dict()
            self.value_setter: Dict[str, Callable[[object, str, Any], None]] = dict()
            self.value_deleter: Dict[str, Callable[[object, str], None]] = dict()
            self.value_converter: Dict[str, Callable[[object, Any], Any]] = dict()
            self.value_update: Dict[str, Callable[[object, str, Any], None]] = dict()
            self.value_validator: Dict[str, Callable[[object, Any], Any]] = dict()
            self.autocopy: bool = autocopy
            self.value_autocopy_get: Dict[str, bool] = dict()
            self.value_autocopy_set: Dict[str, bool] = dict()
            self.attribute_class_owner: Dict[str, type] = dict()
            self.owner: Optional[type] = None
            self.aliases: Dict[str, str] = dict()
            self.copy: Dict[type, Callable[[Any], Any]] = dict()
            self.copy_allow_subclass: Set[type] = set()
            self.use_converter_on_set: Dict[str, bool] = dict()
            self.readonly: Set[str] = set()

        def __or__(self, rhs: Configuration.Infos) -> Configuration.Infos:
            if not isinstance(rhs, type(self)):
                return NotImplemented
            other: Configuration.Infos = deepcopy(self)
            other |= rhs
            return other

        def __ior__(self, rhs: Configuration.Infos) -> Configuration.Infos:
            if not isinstance(rhs, type(self)):
                return NotImplemented
            self.options |= rhs.options
            self.update |= rhs.update
            self.value_getter |= rhs.value_getter
            self.value_setter |= rhs.value_setter
            self.value_deleter |= rhs.value_deleter
            self.value_converter |= rhs.value_converter
            self.value_update |= rhs.value_update
            self.value_validator |= rhs.value_validator
            self.value_autocopy_get |= rhs.value_autocopy_get
            self.value_autocopy_set |= rhs.value_autocopy_set
            self.attribute_class_owner |= rhs.attribute_class_owner
            self.aliases |= rhs.aliases
            self.copy |= rhs.copy
            self.copy_allow_subclass |= rhs.copy_allow_subclass
            self.use_converter_on_set |= rhs.use_converter_on_set
            self.readonly |= rhs.readonly
            return self

        def get_copy_func(self, cls: type) -> Callable[[Any], Any]:
            try:
                return self.copy[cls]
            except KeyError:
                if cls in self.copy_allow_subclass:
                    for t, func in self.copy.items():
                        if issubclass(cls, t):
                            return func
            return deepcopy

        def has_getter_setter_deleter(self, option: str) -> bool:
            return option in self.value_getter or option in self.value_setter or option in self.value_deleter

    __references: Dict[object, _BoundConfiguration] = dict()

    @overload
    def __init__(self, *known_options: str, autocopy: bool = False) -> None:
        ...

    @overload
    def __init__(self, *known_options: str, parent: Union[Configuration, Sequence[Configuration]]) -> None:
        ...

    @overload
    def __init__(self, *known_options: str, autocopy: bool, parent: Union[Configuration, Sequence[Configuration]]) -> None:
        ...

    def __init__(
        self,
        *known_options: str,
        autocopy: Optional[bool] = None,
        parent: Union[Configuration, Sequence[Configuration], None] = None,
    ) -> None:
        if any(not option for option in known_options):
            raise ValueError("Configuration option must not be empty")
        infos: Configuration.Infos
        __parents__: List[Configuration] = []
        if parent is None:
            infos = Configuration.Infos(known_options, bool(autocopy))
        else:
            main_parent: Configuration
            if isinstance(parent, Configuration):
                main_parent = parent
                parent = []
            else:
                parent = list(set(parent))
                if not parent:
                    raise TypeError("parent: Invalid argument: Empty sequence")
                main_parent = parent.pop(0)
            __parents__.append(main_parent)
            __parents__.extend(parent)
            infos = deepcopy(main_parent.__infos)
            infos.options |= set(known_options)
            for parent_infos in (p.__infos for p in parent):
                infos = parent_infos | infos
            if autocopy is not None:
                infos.autocopy = autocopy

        self.__parents__: Tuple[Configuration, ...] = tuple(__parents__)
        self.__infos: Configuration.Infos = infos
        self.__no_parent_ownership: Set[str] = set()
        self.__bound_class: Optional[type] = None

    def __set_name__(self, owner: type, name: str) -> None:
        def all_members(cls: type) -> Dict[str, Any]:
            try:
                mro: List[type] = list(getattr(cls, "__mro__"))
            except AttributeError:

                def getmro(cls: type) -> List[type]:
                    mro = [cls]
                    for base in cls.__bases__:
                        mro.extend(getmro(base))
                    return mro

                mro = getmro(cls)
            mro.reverse()
            members: Dict[str, Any] = dict()
            for someClass in mro:
                members.update(vars(someClass))
            return members

        if self.__bound_class is not None:
            raise TypeError(f"This configuration object is bound to an another class: {self.__bound_class.__name__!r}")
        infos: Configuration.Infos = self.__infos
        if infos.owner is None:
            infos.owner = owner
        self.__bound_class = owner
        attribute_class_owner: Dict[str, type] = infos.attribute_class_owner
        no_parent_ownership: Set[str] = self.__no_parent_ownership
        for option in infos.options:
            if option in no_parent_ownership:
                attribute_class_owner[option] = owner
            else:
                attribute_class_owner[option] = attribute_class_owner.get(option, owner)
        _register_configuration(owner, self)
        all_options: FrozenSet[str] = frozenset((*infos.options, *infos.aliases))
        for obj in all_members(owner).values():
            if isinstance(obj, ConfigAttribute):
                with suppress(AttributeError):
                    config_attr_name: str = obj.name
                    if config_attr_name and config_attr_name not in all_options:
                        raise UnknownOptionError(config_attr_name)
            elif isinstance(obj, Configuration) and obj is not self:
                raise TypeError(f"A class can't have several {Configuration.__name__!r} objects")

    def known_options(self) -> FrozenSet[str]:
        return self.__infos.options

    def known_aliases(self) -> FrozenSet[str]:
        return frozenset(self.__infos.aliases)

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
        infos: Configuration.Infos = self.__infos
        if isinstance(arg1, bool) and not kwargs:
            infos.autocopy = arg1
        elif isinstance(arg1, str) and ("copy_on_get" in kwargs or "copy_on_set" in kwargs):
            if arg1 not in infos.options:
                raise UnknownOptionError(arg1)
            if "copy_on_get" in kwargs:
                copy_on_get: Optional[bool] = kwargs["copy_on_get"]
                if copy_on_get is None:
                    infos.value_autocopy_get.pop(arg1, None)
                else:
                    infos.value_autocopy_get[arg1] = bool(copy_on_get)
            if "copy_on_set" in kwargs:
                copy_on_set: Optional[bool] = kwargs["copy_on_set"]
                if copy_on_set is None:
                    infos.value_autocopy_set.pop(arg1, None)
                else:
                    infos.value_autocopy_set[arg1] = bool(copy_on_set)
        else:
            raise TypeError("Invalid argument")

    def remove_parent_ownership(self, option: str) -> None:
        if not option:
            raise EmptyOptionNameError()
        infos: Configuration.Infos = self.__infos
        if option not in infos.options:
            raise UnknownOptionError(option)
        self.__no_parent_ownership.add(option)
        if self.__bound_class is not None:
            infos.attribute_class_owner[option] = self.__bound_class

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Configuration:
        ...

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None) -> _BoundConfiguration:
        ...

    def __get__(self, obj: object, objtype: Optional[type] = None) -> Union[Configuration, _BoundConfiguration]:
        if obj is None:
            return self
        if self.__bound_class is None:
            raise TypeError(f"{self} not bound to a class")
        bound_references: Dict[object, _BoundConfiguration] = Configuration.__references
        try:
            return bound_references[obj]
        except KeyError:
            infos: Configuration.Infos = self.__infos
            owner: Optional[type] = infos.owner
            specific_owner: Optional[type] = None
            if owner is not None:
                if objtype is None or objtype is type(obj):
                    objtype = owner
                else:
                    specific_owner = objtype
            else:
                if objtype is None:
                    objtype = type(obj)
                elif objtype is not type(obj):
                    specific_owner = objtype
            return _BoundConfiguration(obj, objtype, infos, bound_references, specific_owner)

    def get_option_getter(self, option: str) -> Optional[Callable[[object, str], Any]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.value_getter.get(option)

    @overload
    def getter(self, option: str, /) -> Callable[[_Getter], _Getter]:
        ...

    @overload
    def getter(self, option: str, func: _Getter, /) -> _Getter:
        ...

    @overload
    def getter(self, option: str, func: None, /) -> None:
        ...

    def getter(self, option: str, /, *func_args: Union[_Getter, None]) -> Union[Callable[[_Getter], _Getter], _Getter, None]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _Getter) -> _Getter:
                infos.value_getter[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_Getter] = func_args[0]
        if func is None:
            infos.value_getter.pop(option, None)
        else:
            infos.value_getter[option] = _make_function_wrapper(func)
        return func

    @overload
    def getter_no_name(self, option: str, /) -> Callable[[_NoNameGetter], _NoNameGetter]:
        ...

    @overload
    def getter_no_name(self, option: str, func: _NoNameGetter, /) -> _NoNameGetter:
        ...

    def getter_no_name(
        self, option: str, func: Optional[_NoNameGetter] = None, /
    ) -> Union[_NoNameGetter, Callable[[_NoNameGetter], _NoNameGetter]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        def decorator(func: _NoNameGetter) -> _NoNameGetter:
            _func = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object, /, name: str) -> Any:
                return _func(self)

            self.getter(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if func is None:
            return decorator
        return decorator(func)

    def get_option_setter(self, option: str) -> Optional[Callable[[object, str, Any], None]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.value_setter.get(option)

    @overload
    def setter(self, option: str, /) -> Callable[[_Setter], _Setter]:
        ...

    @overload
    def setter(self, option: str, func: _Setter, /) -> _Setter:
        ...

    @overload
    def setter(self, option: str, func: None, /) -> None:
        ...

    def setter(self, option: str, /, *func_args: Union[_Setter, None]) -> Union[Callable[[_Setter], _Setter], _Setter, None]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _Setter) -> _Setter:
                infos.value_setter[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_Setter] = func_args[0]
        if func is None:
            infos.value_setter.pop(option, None)
        else:
            infos.value_setter[option] = _make_function_wrapper(func)
        return func

    @overload
    def setter_no_name(self, option: str, /) -> Callable[[_NoNameSetter], _NoNameSetter]:
        ...

    @overload
    def setter_no_name(self, option: str, func: _NoNameSetter, /) -> _NoNameSetter:
        ...

    def setter_no_name(
        self, option: str, func: Optional[_NoNameSetter] = None, /
    ) -> Union[_NoNameSetter, Callable[[_NoNameSetter], _NoNameSetter]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        def decorator(func: _NoNameSetter) -> _NoNameSetter:
            _func = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object, /, name: str, value: Any) -> Any:
                return _func(self, value)

            self.setter(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if func is None:
            return decorator
        return decorator(func)

    def get_option_deleter(self, option: str) -> Optional[Callable[[object, str], None]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.value_deleter.get(option)

    @overload
    def deleter(self, option: str, /) -> Callable[[_Deleter], _Deleter]:
        ...

    @overload
    def deleter(self, option: str, func: _Deleter, /) -> _Deleter:
        ...

    @overload
    def deleter(self, option: str, func: None, /) -> None:
        ...

    def deleter(self, option: str, /, *func_args: Union[_Deleter, None]) -> Union[Callable[[_Deleter], _Deleter], _Deleter, None]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _Deleter) -> _Deleter:
                infos.value_deleter[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_Deleter] = func_args[0]
        if func is None:
            infos.value_deleter.pop(option, None)
        else:
            infos.value_deleter[option] = _make_function_wrapper(func)
        return func

    @overload
    def deleter_no_name(self, option: str, /) -> Callable[[_NoNameDeleter], _NoNameDeleter]:
        ...

    @overload
    def deleter_no_name(self, option: str, func: _NoNameDeleter, /) -> _NoNameDeleter:
        ...

    def deleter_no_name(
        self, option: str, func: Optional[_NoNameDeleter] = None, /
    ) -> Union[_NoNameDeleter, Callable[[_NoNameDeleter], _NoNameDeleter]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        def decorator(func: _NoNameDeleter) -> _NoNameDeleter:
            _func = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object, /, name: str) -> None:
                _func(self)

            self.deleter(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if func is None:
            return decorator
        return decorator(func)

    def get_option_converter(self, option: str) -> Optional[Callable[[object, Any], Any]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.value_converter.get(option)

    @overload
    def converter(self, option: str, /, *, use_on_set: bool = False) -> Callable[[_ValueConverter], _ValueConverter]:
        ...

    @overload
    def converter(self, option: str, func: _ValueConverter, /, *, use_on_set: bool = False) -> _ValueConverter:
        ...

    @overload
    def converter(self, option: str, func: None, /) -> None:
        ...

    def converter(
        self, option: str, /, *func_args: Union[_ValueConverter, None], use_on_set: bool = False
    ) -> Union[Callable[[_ValueConverter], _ValueConverter], _ValueConverter, None]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _ValueConverter) -> _ValueConverter:
                infos.value_converter[option] = _make_function_wrapper(func)
                infos.use_converter_on_set[option] = truth(use_on_set)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_ValueConverter] = func_args[0]
        if func is None:
            infos.value_converter.pop(option, None)
            infos.use_converter_on_set.pop(option, None)
        else:
            infos.value_converter[option] = _make_function_wrapper(func)
            infos.use_converter_on_set[option] = truth(use_on_set)
        return func

    @overload
    def get_updater(self) -> Optional[Callable[[object], None]]:
        ...

    @overload
    def get_updater(self, option: str) -> Optional[Callable[[object], None]]:
        ...

    def get_updater(self, option: Optional[str] = None) -> Union[Callable[[object], None], None]:
        infos: Configuration.Infos = self.__infos
        if option is None:
            return infos.main_update
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.update.get(option)

    @overload
    def updater(self, arg: _Updater, /) -> _Updater:
        ...

    @overload
    def updater(self, arg: None, /) -> None:
        ...

    @overload
    def updater(self, arg: str, /) -> Callable[[_Updater], _Updater]:
        ...

    @overload
    def updater(self, arg: str, func: _Updater, /) -> _Updater:
        ...

    @overload
    def updater(self, arg: str, func: None, /) -> None:
        ...

    def updater(
        self, arg: Union[_Updater, str, None], /, *func_args: Optional[_Updater]
    ) -> Union[_Updater, Callable[[_Updater], _Updater], Optional[_Updater]]:
        if not self.__parents__:
            return self.override_updater(arg, *func_args)
        main_parent: Configuration = self.__parents__[0]
        infos: Configuration.Infos = self.__infos
        if not isinstance(arg, str):
            if arg is None:
                infos.main_update = main_parent.__infos.main_update
                return None
            if main_parent.__infos.main_update is None:
                return self.override_updater(arg, *func_args)

            parent_updater: Callable[[object], None] = main_parent.__infos.main_update
            updater_func: Callable[[object], None] = _make_function_wrapper(arg)

            @wraps(arg)
            def wrapper(self: object) -> None:
                parent_updater(self)
                updater_func(self)

            self.override_updater(_make_function_wrapper(wrapper, already_wrapper=True))
            return arg

        if not arg:
            raise EmptyOptionNameError()
        if arg not in infos.options:
            raise UnknownOptionError(arg)

        option: str = arg

        def decorator(func: _Updater) -> _Updater:
            if option not in infos.update:
                return self.override_updater(option, func)
            parent_updater: Callable[[object], None] = infos.update[option]
            updater_func: Callable[[object], None] = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object) -> None:
                parent_updater(self)
                updater_func(self)

            self.override_updater(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if not func_args:
            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_Updater] = func_args[0]

        if func is not None:
            return decorator(func)
        infos.update.pop(option, None)
        for parent_infos in (p.__infos for p in self.__parents__):
            if option in parent_infos.update:
                infos.update[option] = parent_infos.update[option]
                break
        return func

    @overload
    def override_updater(self, arg: _Updater, /) -> _Updater:
        ...

    @overload
    def override_updater(self, arg: None, /) -> None:
        ...

    @overload
    def override_updater(self, arg: str, /) -> Callable[[_Updater], _Updater]:
        ...

    @overload
    def override_updater(self, arg: str, func: _Updater, /) -> _Updater:
        ...

    @overload
    def override_updater(self, arg: str, func: None, /) -> None:
        ...

    def override_updater(
        self, arg: Union[_Updater, str, None], /, *func_args: Optional[_Updater]
    ) -> Union[_Updater, Callable[[_Updater], _Updater], Optional[_Updater]]:
        infos: Configuration.Infos = self.__infos
        if not isinstance(arg, str):
            infos.main_update = _make_function_wrapper(arg) if arg is not None else None
            return arg

        if not arg:
            raise EmptyOptionNameError()
        if arg not in infos.options:
            raise UnknownOptionError(arg)

        option: str = arg

        if not func_args:

            def decorator(func: _Updater) -> _Updater:
                infos.update[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_Updater] = func_args[0]
        if func is None:
            infos.update.pop(option, None)
        else:
            infos.update[option] = _make_function_wrapper(func)
        return func

    def get_value_updater(self, option: str) -> Union[Callable[[object, str, Any], None], None]:
        infos: Configuration.Infos = self.__infos
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.value_update.get(option)

    @overload
    def value_updater(self, option: str, /) -> Callable[[_ValueUpdater], _ValueUpdater]:
        ...

    @overload
    def value_updater(self, option: str, func: _ValueUpdater, /) -> _ValueUpdater:
        ...

    @overload
    def value_updater(self, option: str, func: None, /) -> None:
        ...

    def value_updater(
        self, option: str, /, *func_args: Optional[_ValueUpdater]
    ) -> Union[Callable[[_ValueUpdater], _ValueUpdater], Optional[_ValueUpdater]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        def decorator(func: _ValueUpdater) -> _ValueUpdater:
            if option not in infos.value_update:
                return self.override_value_updater(option, func)
            parent_updater: Callable[[object, str, Any], None] = infos.value_update[option]
            updater_func: Callable[[object, str, Any], None] = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object, option: str, value: Any) -> None:
                parent_updater(self, option, value)
                updater_func(self, option, value)

            self.override_value_updater(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if not func_args:
            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_ValueUpdater] = func_args[0]

        if func is not None:
            return decorator(func)
        infos.value_update.pop(option, None)
        for parent_infos in (p.__infos for p in self.__parents__):
            if option in parent_infos.value_update:
                infos.value_update[option] = parent_infos.value_update[option]
                break
        return func

    @overload
    def override_value_updater(self, option: str, /) -> Callable[[_ValueUpdater], _ValueUpdater]:
        ...

    @overload
    def override_value_updater(self, option: str, func: _ValueUpdater, /) -> _ValueUpdater:
        ...

    @overload
    def override_value_updater(self, option: str, func: None, /) -> None:
        ...

    def override_value_updater(
        self, option: str, /, *func_args: Optional[_ValueUpdater]
    ) -> Union[Callable[[_ValueUpdater], _ValueUpdater], Optional[_ValueUpdater]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _ValueUpdater) -> _ValueUpdater:
                infos.value_update[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_ValueUpdater] = func_args[0]
        if func is None:
            infos.value_update.pop(option, None)
        else:
            infos.value_update[option] = _make_function_wrapper(func)
        return func

    @overload
    def value_updater_no_name(
        self, option: str, /, *, override: bool = False
    ) -> Callable[[_NoNameValueUpdater], _NoNameValueUpdater]:
        ...

    @overload
    def value_updater_no_name(self, option: str, func: _NoNameValueUpdater, /, *, override: bool = False) -> _NoNameValueUpdater:
        ...

    def value_updater_no_name(
        self, option: str, func: Optional[_NoNameValueUpdater] = None, /, *, override: bool = False
    ) -> Union[_NoNameValueUpdater, Callable[[_NoNameValueUpdater], _NoNameValueUpdater]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        def decorator(func: _NoNameValueUpdater) -> _NoNameValueUpdater:
            _func = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object, /, name: str, value: Any) -> Any:
                return _func(self, value)

            if not override:
                self.value_updater(option, _make_function_wrapper(wrapper, already_wrapper=True))
            else:
                self.override_value_updater(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if func is None:
            return decorator
        return decorator(func)

    def get_validator(self, option: str) -> Optional[Callable[[object, Any], Any]]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        return infos.value_validator.get(option)

    @overload
    def validator(self, option: str, /) -> Callable[[_ValueValidator], _ValueValidator]:
        ...

    @overload
    def validator(self, option: str, func: type, /, *, convert: bool = False) -> type:
        ...

    @overload
    def validator(self, option: str, func: Tuple[type, ...], /) -> Tuple[type, ...]:
        ...

    @overload
    def validator(self, option: str, func: _ValueValidator, /) -> _ValueValidator:
        ...

    @overload
    def validator(self, option: str, func: None, /) -> None:
        ...

    def validator(
        self, option: str, /, *func_args: Union[_ValueValidator, type, Tuple[type, ...], None], convert: bool = False
    ) -> Union[Callable[[_ValueValidator], _ValueValidator], _ValueValidator, type, Tuple[type, ...], None]:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _ValueValidator) -> _ValueValidator:
                infos.value_validator[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[Union[_ValueValidator, type, Tuple[type, ...]]] = func_args[0]
        if func is None:
            infos.value_validator.pop(option, None)
        elif isinstance(func, tuple) or (isinstance(func, type) and not convert):
            _type: Union[type, Tuple[type, ...]] = func
            if isinstance(_type, tuple):
                if not _type or any(not isinstance(t, type) for t in _type):
                    raise TypeError(f"Invalid types argument")
                if len(_type) == 1:
                    _type = _type[0]

            @no_object
            def type_checker(val: Any) -> Any:
                if not isinstance(val, _type):
                    expected: str
                    if isinstance(_type, type):
                        expected = repr(_type.__qualname__)
                    else:
                        expected = f"one of those: ({', '.join(repr(t.__qualname__) for t in _type)})"
                    raise TypeError(f"Invalid value type. expected {expected}, got {type(val).__qualname__!r}")
                return val

            infos.value_validator[option] = _make_function_wrapper(type_checker)
        elif isinstance(func, type) and convert:
            _value_type: type = func

            @no_object
            def value_convert(val: Any) -> Any:
                return _value_type(val)

            infos.value_validator[option] = _make_function_wrapper(value_convert)
        else:
            infos.value_validator[option] = _make_function_wrapper(func)
        return func

    @overload
    def enum(self, option: str, enum: Type[Enum], *, return_value: bool = False) -> None:
        ...

    @overload
    def enum(self, option: str, enum: None) -> None:
        ...

    def enum(self, option: str, enum: Optional[Type[Enum]], *, return_value: bool = False) -> None:
        enum_config_wrapper_attr: str = "__enum_config_wrapper__"

        if enum is None:
            if getattr(self.get_option_converter(option), enum_config_wrapper_attr, False):
                self.converter(option, None)
            if getattr(self.get_validator(option), enum_config_wrapper_attr, False):
                self.validator(option, None)
            return

        enum_type: Type[Enum] = enum

        def enum_wrapper(func: _Func) -> _Func:
            setattr(func, enum_config_wrapper_attr, True)
            return func

        @no_object
        def enum_converter(enum: Enum) -> Any:
            return enum.value

        @no_object
        def enum_validator(val: Any) -> Enum:
            return enum_type(val)

        if return_value:
            self.converter(option, enum_wrapper(_make_function_wrapper(enum_converter)))
        self.validator(option, enum_wrapper(_make_function_wrapper(enum_validator)))

    def set_alias(self, option: str, alias: str) -> None:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        if not isinstance(alias, str):
            raise InvalidAliasError(alias, "Invalid type")
        if alias == option:
            return
        if not alias:
            raise InvalidAliasError(alias, "Empty string alias")
        if alias in infos.options:
            raise InvalidAliasError(alias, "Alias name is a configuration option")
        aliases: Dict[str, str] = infos.aliases
        if alias in aliases:
            if aliases[alias] != option:
                raise InvalidAliasError(alias, f"Already bound to option {aliases[alias]!r}")
        else:
            aliases[alias] = option

    def remove_alias(self, alias: str) -> None:
        aliases: Dict[str, str] = self.__infos.aliases
        aliases.pop(alias)

    def remove_all_aliases(self, option: str) -> None:
        infos: Configuration.Infos = self.__infos
        if not option:
            raise EmptyOptionNameError()
        if option not in infos.options:
            raise UnknownOptionError(option)
        aliases: Dict[str, str] = infos.aliases
        for alias, opt in list(aliases.items()):
            if opt == option:
                aliases.pop(alias)

    def register_copy_func(self, cls: type, func: Callable[[Any], Any], *, allow_subclass: bool = False) -> None:
        if not isinstance(cls, type):
            raise TypeError("'cls' argument must be a type")
        if not callable(func):
            raise TypeError("'func' is not callable")
        infos: Configuration.Infos = self.__infos
        infos.copy[cls] = func
        if allow_subclass:
            infos.copy_allow_subclass.add(cls)
        else:
            with suppress(KeyError):
                infos.copy_allow_subclass.remove(cls)

    def remove_copy_func(self, cls: type) -> None:
        infos: Configuration.Infos = self.__infos
        infos.copy.pop(cls, None)
        with suppress(KeyError):
            infos.copy_allow_subclass.remove(cls)

    def readonly(self, *options: str) -> None:
        infos: Configuration.Infos = self.__infos
        for option in options:
            if not option:
                raise EmptyOptionNameError()
            if option not in infos.options:
                raise UnknownOptionError(option)
            infos.readonly.add(option)


class ConfigTemplate(Configuration):
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

    @overload
    def __init__(self, *, autocopy: bool = False) -> None:
        ...

    @overload
    def __init__(self, *, parent: Union[Configuration, Sequence[Configuration]]) -> None:
        ...

    @overload
    def __init__(self, *, autocopy: bool, parent: Union[Configuration, Sequence[Configuration]]) -> None:
        ...

    def __init__(
        self,
        *,
        autocopy: Optional[bool] = None,
        parent: Union[Configuration, Sequence[Configuration], None] = None,
    ) -> None:
        super().__init__(autocopy=autocopy, parent=parent)  # type: ignore[arg-type]

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> ConfigTemplate:
        ...

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None) -> _BoundConfiguration:
        ...

    def __get__(self, obj: object, objtype: Optional[type] = None) -> Union[ConfigTemplate, _BoundConfiguration]:
        if obj is None:
            return self
        raise TypeError("Cannot use configuration template as descriptor")


class ConfigAttribute(Generic[_T]):
    def __init__(self) -> None:
        self.__name: str

    def __set_name__(self, owner: type, name: str) -> None:
        if len(name) == 0:
            raise ValueError(f"Attribute name must not be empty")
        self.__name = name
        config: Configuration = _retrieve_configuration(owner)
        if name not in config.known_options() and name not in config.known_aliases():
            raise UnknownOptionError(name)

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> ConfigAttribute[_T]:
        ...

    @overload
    def __get__(self, obj: object, objtype: Optional[type] = None) -> _T:
        ...

    def __get__(self, obj: object, objtype: Optional[type] = None) -> Union[_T, ConfigAttribute[_T]]:
        if obj is None:
            return self
        name: str = self.__name
        cls: type = objtype if objtype is not None else type(obj)
        config: _BoundConfiguration = _retrieve_configuration(cls).__get__(obj, objtype)
        try:
            value: _T = config.get(name)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from None
        return value

    def __set__(self, obj: object, value: _T) -> None:
        name: str = self.__name
        config: _BoundConfiguration = _retrieve_configuration(type(obj)).__get__(obj)
        try:
            config.set(name, value)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from None

    def __delete__(self, obj: object) -> None:
        name: str = self.__name
        config: _BoundConfiguration = _retrieve_configuration(type(obj)).__get__(obj)
        try:
            config.remove(name)
        except OptionError as exc:
            error: str = str(exc)
            raise AttributeError(error) from None

    @property
    def name(self) -> str:
        return self.__name


class _BoundConfiguration:
    __no_updater: Set[object] = set()

    def __init__(
        self,
        obj: object,
        objtype: type,
        infos: Configuration.Infos,
        bound_references: Dict[object, _BoundConfiguration],
        specific_owner: Optional[type] = None,
    ) -> None:
        self.__obj: object = obj
        self.__type: type = objtype
        self.__infos: Configuration.Infos = infos
        self.__owner: Optional[type] = specific_owner
        self.__references: Dict[object, _BoundConfiguration] = bound_references
        self.__update_call: bool = True
        self.__init_context: bool = False
        self.__update_register: Optional[Dict[str, None]] = None

    def known_options(self) -> FrozenSet[str]:
        return self.__infos.options

    def known_aliases(self) -> FrozenSet[str]:
        return frozenset(self.__infos.aliases)

    @contextmanager
    def initialization(self) -> Iterator[_BoundConfiguration]:
        if self.__init_context:
            yield self
            return

        def cleanup() -> None:
            self.__update_call = True
            self.__update_register = None
            self.__references.pop(bound_obj, None)
            self.__init_context = False

        bound_obj: object = self.__obj
        with ExitStack() as stack:
            stack.callback(cleanup)
            update_register: Dict[str, None] = dict()

            self.__init_context = True
            self.__update_register = update_register
            self.__update_call = False
            self.__references[bound_obj] = self
            yield self
            infos: Configuration.Infos = self.__infos
            getter: Dict[str, Callable[[object, str], Any]] = infos.value_getter
            get_attribute = self.__get_attribute
            if update_register:
                for option in (opt for opt in update_register if opt in infos.value_update):
                    value_updater_func: Callable[[object, str, Any], None] = infos.value_update[option]
                    value: Any
                    if option in getter:
                        value = getter[option](bound_obj, option)
                    else:
                        try:
                            value = getattr(bound_obj, get_attribute(option))
                        except AttributeError as exc:
                            raise UnregisteredOptionError(option) from exc
                    value_updater_func(bound_obj, option, value)
            if bound_obj in self.__no_updater:
                return
            main_update: Optional[Callable[[object], None]] = infos.main_update
            for updater_func in dict.fromkeys(func for opt, func in infos.update.items() if opt in update_register):
                if updater_func is not main_update:
                    updater_func(bound_obj)
            if callable(main_update):
                main_update(bound_obj)

    def has_initialization_context(self) -> bool:
        return self.__init_context

    @contextmanager
    def no_updater(self) -> Iterator[_BoundConfiguration]:
        obj: object = self.__obj
        if obj in self.__no_updater:
            yield self
            return

        def cleanup() -> None:
            self.__no_updater.remove(obj)

        self.__no_updater.add(obj)
        with ExitStack() as stack:
            stack.callback(cleanup)
            yield self

    def __getitem__(self, option: str) -> Any:
        return self.get(option)

    @overload
    def get(self, option: str) -> Any:
        ...

    @overload
    def get(self, option: str, copy: bool) -> Any:
        ...

    def get(self, option: str, copy: Optional[bool] = None) -> Any:
        infos: Configuration.Infos = self.__infos
        option = infos.aliases.get(option, option)
        if not option:
            raise EmptyOptionNameError()
        obj: object = self.__obj
        if option not in infos.options:
            raise UnknownOptionError(option)
        getter: Dict[str, Callable[[object, str], Any]] = infos.value_getter
        value: Any
        if option in getter:
            with self.no_updater():
                value = getter[option](obj, option)
        else:
            if infos.has_getter_setter_deleter(option):
                raise OptionError(option, "Cannot be get")
            try:
                value = getattr(obj, self.__get_attribute(option))
            except AttributeError as exc:
                raise UnregisteredOptionError(option) from exc
        converter: Optional[Callable[[object, Any], Any]] = infos.value_converter.get(option)
        if callable(converter):
            value = converter(obj, value)
        if copy is None:
            copy = infos.value_autocopy_get.get(option, infos.autocopy)
        if copy:
            try:
                return infos.get_copy_func(type(value))(value)
            except:
                pass
        return value

    def __setitem__(self, option: str, value: Any) -> None:
        return self.set(option, value)

    @overload
    def set(self, option: str, value: Any) -> None:
        ...

    @overload
    def set(self, option: str, value: Any, copy: bool) -> None:
        ...

    def set(self, option: str, value: Any, copy: Optional[bool] = None) -> None:
        infos: Configuration.Infos = self.__infos
        option = infos.aliases.get(option, option)
        if not option:
            raise EmptyOptionNameError()

        if option not in infos.options:
            raise UnknownOptionError(option)

        if copy is None:
            copy = infos.value_autocopy_set.get(option, infos.autocopy)

        obj: object = self.__obj
        main_update: Optional[Callable[[object], None]] = infos.main_update
        update: Optional[Callable[[object], None]] = infos.update.get(option)
        value_update: Optional[Callable[[object, str, Any], None]] = infos.value_update.get(option)
        value_validator: Optional[Callable[[object, Any], Any]] = infos.value_validator.get(option)
        converter: Optional[Callable[[object, Any], Any]] = infos.value_converter.get(option)
        update_register: Optional[Dict[str, None]] = self.__update_register
        attribute: str = self.__get_attribute(option)
        getter: Dict[str, Callable[[object, str], Any]] = infos.value_getter
        setter: Dict[str, Callable[[object, str, Any], None]] = infos.value_setter

        if option in infos.readonly or (option not in setter and infos.has_getter_setter_deleter(option)):
            raise OptionError(option, "Cannot be set")

        def copy_value(value: Any) -> Any:
            if not copy:
                return value
            try:
                return infos.get_copy_func(type(value))(value)
            except:
                return value

        if callable(value_validator):
            value = value_validator(obj, value)
        if infos.use_converter_on_set.get(option, False) and callable(converter):
            value = converter(obj, value)
        actual_value: Any
        try:
            if option in getter:
                actual_value = getter[option](obj, option)
            else:
                if infos.has_getter_setter_deleter(option):
                    raise AttributeError
                actual_value = getattr(obj, attribute)
            if actual_value != value:
                raise AttributeError
            return
        except (AttributeError, OptionError):
            value = copy_value(value)
            if option in setter:
                with self.no_updater():
                    setter[option](obj, option, value)
            else:
                setattr(obj, attribute, value)
            if update_register is not None:
                update_register[option] = None

        if self.__update_call:
            if callable(value_update):
                value_update(obj, option, value)
            if obj not in self.__no_updater:
                if callable(update) and update is not main_update:
                    update(obj)
                if callable(main_update):
                    main_update(obj)

    def __delitem__(self, option: str) -> None:
        return self.remove(option)

    def remove(self, option: str) -> None:
        infos: Configuration.Infos = self.__infos
        option = infos.aliases.get(option, option)
        if not option:
            raise EmptyOptionNameError()
        obj: object = self.__obj
        main_update: Optional[Callable[[object], None]] = infos.main_update
        update: Optional[Callable[[object], None]] = infos.update.get(option)
        update_register: Optional[Dict[str, None]] = self.__update_register
        deleter: Dict[str, Callable[[object, str], None]] = infos.value_deleter
        if option not in infos.options:
            raise UnknownOptionError(option)
        if option in infos.readonly or (option not in deleter and infos.has_getter_setter_deleter(option)):
            raise OptionError(option, "Cannot be deleted")
        if option in deleter:
            with self.no_updater():
                deleter[option](obj, option)
        else:
            try:
                delattr(obj, self.__get_attribute(option))
            except AttributeError as exc:
                raise UnregisteredOptionError(option) from exc
        if update_register is not None:
            update_register.pop(option, None)
        if self.__update_call and obj not in self.__no_updater:
            if callable(update) and update is not main_update:
                update(obj)
            if callable(main_update):
                main_update(obj)

    def update(self) -> None:
        if not self.__update_call:
            return
        obj: object = self.__obj
        if obj in self.__no_updater:
            return
        infos: Configuration.Infos = self.__infos
        main_update: Optional[Callable[[object], None]] = infos.main_update
        getter: Dict[str, Callable[[object, str], Any]] = infos.value_getter
        get_attribute: Callable[[str], str] = self.__get_attribute
        for option, value_updater in infos.value_update.items():
            if option in getter:
                value_updater(obj, option, getter[option](obj, option))
            else:
                try:
                    value_updater(obj, option, getattr(obj, get_attribute(option)))
                except AttributeError as exc:
                    raise UnregisteredOptionError(option) from exc
        for updater in dict.fromkeys(infos.update.values()):
            if updater is not main_update:
                updater(obj)
        if callable(main_update):
            main_update(obj)

    def __call__(self, *, __copy: Optional[Union[bool, Dict[str, bool]]] = None, **kwargs: Any) -> None:
        if not kwargs:
            return
        infos: Configuration.Infos = self.__infos
        autocopy: bool = infos.autocopy
        obj: object = self.__obj
        all_options: FrozenSet[str] = infos.options
        main_update: Optional[Callable[[object], None]] = infos.main_update
        update_get: Callable[[str], Optional[Callable[[object], None]]] = infos.update.get
        value_update_get: Callable[[str], Optional[Callable[[object, str, Any], None]]] = infos.value_update.get
        value_validator_get: Callable[[str], Optional[Callable[[object, Any], Any]]] = infos.value_validator.get
        value_converter_get: Callable[[str], Optional[Callable[[object, Any], Any]]] = infos.value_converter.get
        use_converter: Callable[[str], Optional[bool]] = infos.use_converter_on_set.get
        get_attribute: Callable[[str], str] = self.__get_attribute
        update_register: Optional[Dict[str, None]] = self.__update_register
        aliases: Dict[str, str] = infos.aliases
        getter: Dict[str, Callable[[object, str], Any]] = infos.value_getter
        setter: Dict[str, Callable[[object, str, Any], None]] = infos.value_setter
        readonly_option: Set[str] = infos.readonly

        def copy_value(option: str, value: Any) -> Any:
            copy: bool
            if __copy is None:
                copy = infos.value_autocopy_set.get(option, autocopy)
            elif isinstance(__copy, bool):
                copy = __copy
            else:
                copy = __copy.get(option, infos.value_autocopy_set.get(option, autocopy))
            if not copy:
                return value
            try:
                return infos.get_copy_func(type(value))(value)
            except:
                return value

        values: List[Tuple[str, str, Any]] = list()

        for option, value in kwargs.items():
            option = aliases.get(option, option)
            if option not in all_options:
                raise UnknownOptionError(option)
            if option in readonly_option:
                raise OptionError(option, "Cannot be set")
            value_validator: Optional[Callable[[object, Any], None]] = value_validator_get(option)
            if callable(value_validator):
                value = value_validator(obj, value)
            if use_converter(option):
                converter: Optional[Callable[[object, Any], Any]] = value_converter_get(option)
                if callable(converter):
                    value = converter(obj, value)
            attribute: str = get_attribute(option)
            try:
                actual_value: Any
                if option in getter:
                    actual_value = getter[option](obj, option)
                else:
                    if infos.has_getter_setter_deleter(option):
                        raise AttributeError
                    actual_value = getattr(obj, attribute)
                if actual_value != value:
                    raise AttributeError
            except (AttributeError, OptionError):
                if option not in setter and infos.has_getter_setter_deleter(option):
                    raise OptionError(option, "Cannot be set")
                value = copy_value(option, value)
                values.append((option, attribute, value))

        for option, attribute, value in values:
            if option in setter:
                with self.no_updater():
                    setter[option](obj, option, value)
            else:
                setattr(obj, attribute, value)
            if update_register is not None:
                update_register[option] = None
        if values and self.__update_call:
            for option, _, value in values:
                value_updater: Optional[Callable[[object, str, Any], None]] = value_update_get(option)
                if callable(value_updater):
                    value_updater(obj, option, value)
            if obj not in self.__no_updater:
                for updater in dict.fromkeys(update_get(opt) for opt, _, _ in values):
                    if callable(updater) and updater is not main_update:
                        updater(obj)
                if callable(main_update):
                    main_update(obj)

    def __get_attribute(self, option: str) -> str:
        objtype: type = self.__type
        owner: type
        infos: Configuration.Infos = self.__infos
        specific_owner: Optional[type] = self.__owner
        if specific_owner is not None:
            owner = specific_owner
        elif objtype is infos.owner:
            owner = infos.attribute_class_owner.get(option, objtype)
        else:
            owner = objtype
        return f"_{owner.__name__}__{option}"


def _no_type_check_cache(func: _Func) -> _Func:
    return cast(_Func, cache(func))


@_no_type_check_cache
def _make_function_wrapper(func: Any, *, already_wrapper: bool = False, check_override: bool = True) -> Callable[..., Any]:
    if getattr(func, "__boundconfiguration_wrapper__", False) and callable(func):
        return cast(Callable[..., Any], func)

    if already_wrapper:
        wrapper: Callable[..., Any] = func
    elif not getattr(func, "__no_object__", False) and not isinstance(func, (BuiltinFunctionType, BuiltinMethodType)):

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            try:
                get: Any = getattr(func, "__get__")
                if not callable(get):
                    raise TypeError("Not callable")
                _func = get(self, type(self))
                if not callable(_func):
                    raise TypeError("Not callable")
            except (AttributeError, TypeError) as exc:
                error: str = str(exc)
                raise TypeError(error)
            else:
                if check_override:
                    _func_name: str = _func.__name__
                    if _func_name != "<lambda>":
                        _sub_func = getattr(self, _func_name, _func)
                        if _sub_func is not _func and callable(_sub_func):
                            _func = _sub_func
            return _func(*args, **kwargs)

    else:

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

    setattr(wrapper, "__boundconfiguration_wrapper__", True)
    return wrapper


def _register_configuration(cls: type, config: Configuration) -> None:
    setattr(cls, "____configuration____", config)


def _retrieve_configuration(cls: type) -> Configuration:
    try:
        config: Configuration = getattr(cls, "____configuration____")
        if not isinstance(config, Configuration):
            raise AttributeError
    except AttributeError:
        raise TypeError(f"{cls.__name__} does not have a {Configuration.__name__} object") from None
    return config


class _ConfigInitializer:
    def __init__(self, func: Callable[..., Any]) -> None:
        self.__func__: Callable[..., Any] = func

    @property
    def __call__(self) -> Callable[..., Any]:
        return self.__func__

    def __getattr__(self, name: str) -> Any:
        func: Any = self.__func__
        return getattr(func, name)

    def __get__(self, obj: object, objtype: Optional[type] = None) -> Callable[..., Any]:
        func: Callable[..., Any] = self.__func__
        try:
            get: Any = getattr(func, "__get__")
            if not callable(get):
                raise TypeError
            func = get(obj, objtype)
        except (AttributeError, TypeError):
            if obj is not None:
                _func = func
                func = lambda *args, **kwargs: _func(obj, *args, **kwargs)
        if obj is None:
            return func
        cls: type = objtype if objtype is not None else type(obj)
        config: Configuration = _retrieve_configuration(cls)
        bound_config: _BoundConfiguration = config.__get__(obj, objtype)

        def config_initializer_method(*args: Any, **kwargs: Any) -> Any:
            with bound_config.initialization():
                return func(*args, **kwargs)

        return config_initializer_method
