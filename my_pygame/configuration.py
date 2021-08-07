# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    Generic,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)
from copy import deepcopy, Error as CopyError


_T = TypeVar("_T")

_Updater = TypeVar("_Updater", bound=Union[Callable[[Any], None], Callable[[], None]])
_ValueUpdater = TypeVar("_ValueUpdater", bound=Union[Callable[[Any, str, Any], None], Callable[[str, Any], None]])
_ValueValidator = TypeVar("_ValueValidator", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])


def _make_function_wrapper(func: Any) -> Callable[..., Any]:
    if getattr(func, "__boundconfiguration_wrapper__", False) and callable(func):
        return cast(Callable[..., Any], func)

    def wrapper(obj: Any, /, *args: Any, **kwargs: Any) -> Any:
        try:
            _func = getattr(func, "__get__")(obj, type(obj))
            if not callable(_func):
                raise AttributeError
            _func_name: str = _func.__name__
            if _func_name != "<lambda>":
                _sub_func = getattr(obj, _func_name, _func)
                if _sub_func is not _func and callable(_sub_func):
                    _func = _sub_func
        except AttributeError:
            try:
                return func(obj, *args, **kwargs)
            except TypeError as exc:
                try:
                    return func(*args, **kwargs)
                except TypeError as subexc:
                    raise subexc from exc
        return _func(*args, **kwargs)

    setattr(wrapper, "__boundconfiguration_wrapper__", True)
    return wrapper


class OptionError(Exception):
    pass


class UnknownOptionError(OptionError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Unknown config option {name!r}")


class UnregisteredOptionError(OptionError):
    def __init__(self, name: str) -> None:
        super().__init__(f"Unregistered option {name!r}")


class EmptyOptionNameError(OptionError):
    def __init__(self) -> None:
        super().__init__("Empty string option given")


class Configuration:
    class Infos:
        def __init__(self, known_options: Sequence[str], autocopy: bool) -> None:
            self.options: FrozenSet[str] = frozenset(known_options)
            self.update: Optional[Callable[[Any], None]] = None
            self.value_update: Dict[str, Callable[[Any, str, Any], None]] = dict()
            self.value_validator: Dict[str, Callable[[Any, Any], Any]] = dict()
            self.autocopy: bool = autocopy
            self.value_autocopy_get: Dict[str, bool] = dict()
            self.value_autocopy_set: Dict[str, bool] = dict()
            self.attribute_class_owner: Dict[str, type] = dict()
            self.owner: Optional[type] = None

    @overload
    def __init__(self, *, autocopy: bool = False) -> None:
        ...

    @overload
    def __init__(self, *, autocopy: bool = False, parent: Union[Configuration, Sequence[Configuration]]) -> None:
        ...

    @overload
    def __init__(self, *known_options: str, autocopy: bool = False) -> None:
        ...

    @overload
    def __init__(
        self, *known_options: str, autocopy: bool = False, parent: Union[Configuration, Sequence[Configuration]]
    ) -> None:
        ...

    def __init__(
        self, *known_options: str, autocopy: bool = False, parent: Union[Configuration, Sequence[Configuration], None] = None
    ) -> None:
        if any(not option for option in known_options):
            raise ValueError("Configuration option must not be empty")
        infos: Configuration.Infos
        if parent is None:
            infos = Configuration.Infos(known_options, autocopy)
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
            infos = deepcopy(main_parent.__infos)
            infos.options = infos.options.union(opt for p in parent for opt in p.__infos.options).union(known_options)
            for parent_infos in (p.__infos for p in parent):
                infos.value_update = parent_infos.value_update | infos.value_update
                infos.value_validator = parent_infos.value_validator | infos.value_validator
                infos.value_autocopy_get = parent_infos.value_autocopy_get | infos.value_autocopy_get
                infos.value_autocopy_set = parent_infos.value_autocopy_set | infos.value_autocopy_set
                infos.attribute_class_owner = parent_infos.attribute_class_owner | infos.attribute_class_owner

        self.__infos: Configuration.Infos = infos

    def __set_name__(self, owner: type, name: str) -> None:
        infos: Configuration.Infos = self.__infos
        if infos.owner is None:
            infos.owner = owner
        attribute_class_owner: Dict[str, type] = infos.attribute_class_owner
        for option in infos.options:
            attribute_class_owner[option] = attribute_class_owner.get(option, owner)
        for attr in dir(owner):
            obj: Any = getattr(owner, attr)
            if isinstance(obj, ConfigAttribute) and obj.get_config() is not self:
                new_obj: ConfigAttribute[Any] = ConfigAttribute(self)
                setattr(owner, attr, new_obj)
                new_obj.__set_name__(owner, attr)

    def known_options(self) -> FrozenSet[str]:
        return self.__infos.options

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
        if isinstance(arg1, bool) and not kwargs:
            self.__infos.autocopy = arg1
        elif isinstance(arg1, str) and ("copy_on_get" in kwargs or "copy_on_set" in kwargs):
            options: FrozenSet[str] = self.__infos.options
            if options and arg1 not in options:
                raise UnknownOptionError(arg1)
            if "copy_on_get" in kwargs:
                copy_on_get: Optional[bool] = kwargs["copy_on_get"]
                if copy_on_get is None:
                    self.__infos.value_autocopy_get.pop(arg1, None)
                else:
                    self.__infos.value_autocopy_get[arg1] = bool(copy_on_get)
            if "copy_on_set" in kwargs:
                copy_on_set: Optional[bool] = kwargs["copy_on_set"]
                if copy_on_set is None:
                    self.__infos.value_autocopy_set.pop(arg1, None)
                else:
                    self.__infos.value_autocopy_set[arg1] = bool(copy_on_set)
        else:
            raise TypeError("Invalid argument")

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Configuration:
        ...

    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> _BoundConfiguration:
        ...

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Union[Configuration, _BoundConfiguration]:
        if obj is None:
            return self
        infos: Configuration.Infos = self.__infos
        owner: Optional[type] = infos.owner
        specific_owner: Optional[type] = None
        if owner is not None:
            if objtype is None or objtype is type(obj):
                objtype = owner
            else:
                specific_owner = objtype
        elif objtype is None:
            objtype = type(obj)
        return _BoundConfiguration(obj, objtype, infos, specific_owner)

    @overload
    def get_updater(self) -> Optional[Callable[[Any], None]]:
        ...

    @overload
    def get_updater(self, option: str) -> Optional[Callable[[Any, str, Any], None]]:
        ...

    def get_updater(self, option: Optional[str] = None) -> Union[Callable[[Any], None], Callable[[Any, str, Any], None], None]:
        if option is None:
            return self.__infos.update
        options: FrozenSet[str] = self.__infos.options
        if options and option not in options:
            raise UnknownOptionError(option)
        return self.__infos.value_update.get(option)

    @overload
    def updater(self, arg: _Updater, /) -> _Updater:
        ...

    @overload
    def updater(self, arg: None, /) -> None:
        ...

    @overload
    def updater(self, arg: str, /) -> Callable[[_ValueUpdater], _ValueUpdater]:
        ...

    @overload
    def updater(self, arg: str, func: Optional[_ValueUpdater], /) -> Optional[_ValueUpdater]:
        ...

    def updater(
        self, arg: Union[_Updater, str, None], /, *func_args: Optional[_ValueUpdater]
    ) -> Union[_Updater, Callable[[_ValueUpdater], _ValueUpdater], Optional[_ValueUpdater]]:
        if isinstance(arg, str):
            options: FrozenSet[str] = self.__infos.options
            if not arg:
                raise EmptyOptionNameError()
            if options and arg not in options:
                raise UnknownOptionError(arg)

            if not func_args:
                config_name: str = arg

                def decorator(func: _ValueUpdater) -> _ValueUpdater:
                    self.__infos.value_update[config_name] = _make_function_wrapper(func)
                    return func

                return decorator

            if len(func_args) > 1:
                raise TypeError("Invalid arguments")
            func: Optional[_ValueUpdater] = func_args[0]
            if func is None:
                self.__infos.value_update.pop(arg, None)
            else:
                self.__infos.value_update[arg] = _make_function_wrapper(func)
            return func

        self.__infos.update = _make_function_wrapper(arg) if arg is not None else None
        return arg

    def get_validator(self, option: str) -> Optional[Callable[[Any, Any], Any]]:
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise OptionError(option)
        return self.__infos.value_validator.get(option)

    @overload
    def validator(self, option: str, /) -> Callable[[_ValueValidator], _ValueValidator]:
        ...

    @overload
    def validator(self, option: str, func: type, /) -> type:
        ...

    @overload
    def validator(self, option: str, func: Tuple[type, ...], /) -> Tuple[type, ...]:
        ...

    @overload
    def validator(self, option: str, func: Optional[_ValueValidator], /) -> Optional[_ValueValidator]:
        ...

    def validator(
        self, option: str, /, *func_args: Optional[Union[_ValueValidator, type, Tuple[type, ...]]]
    ) -> Union[Callable[[_ValueValidator], _ValueValidator], _ValueValidator, type, Tuple[type, ...], None]:
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise OptionError(option)

        if not func_args:

            def decorator(func: _ValueValidator) -> _ValueValidator:
                self.__infos.value_validator[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[Union[_ValueValidator, type, Tuple[type, ...]]] = func_args[0]
        if func is None:
            self.__infos.value_validator.pop(option, None)
        elif isinstance(func, (type, tuple)):
            _type: Union[type, Tuple[type, ...]] = func
            if isinstance(_type, tuple):
                if not _type:
                    raise TypeError(f"Empty tuple of types given")
                if len(_type) == 1:
                    _type = _type[0]

            @staticmethod  # type: ignore[misc]
            def type_checker(val: Any) -> Any:
                if not isinstance(val, _type):
                    expected: str
                    if isinstance(_type, type):
                        expected = repr(_type.__qualname__)
                    else:
                        expected = f"one of those: ({', '.join(repr(t.__qualname__) for t in _type)})"
                    raise TypeError(f"Invalid value type. expected {expected}, got {type(val).__qualname__!r}")
                return val

            self.__infos.value_validator[option] = _make_function_wrapper(type_checker)
        else:
            self.__infos.value_validator[option] = _make_function_wrapper(func)
        return func


class ConfigAttribute(Generic[_T]):
    def __init__(self, config: Configuration) -> None:
        self.__name: str = str()
        self.__config = config.__get__
        self.__known_options: FrozenSet[str] = config.known_options()

    def __set_name__(self, owner: type, name: str) -> None:
        if len(name) == 0:
            raise ValueError(f"Attribute name must not be empty")
        known_options: FrozenSet[str] = self.__known_options
        if known_options and name not in known_options:
            raise ValueError(f"Invalid attribute name {name!r}: Not known by configuration object")
        self.__name = name

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> ConfigAttribute[_T]:
        ...

    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> _T:
        ...

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Union[_T, ConfigAttribute[_T]]:
        if obj is None:
            return self
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = self.__config(obj, objtype)
        try:
            value: _T = config.get(name)
        except OptionError as e:
            raise AttributeError(str(e)) from None
        return value

    def __set__(self, obj: Any, value: _T) -> None:
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = self.__config(obj)
        config.set(name, value)

    def __delete__(self, obj: Any) -> None:
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = self.__config(obj)
        try:
            config.remove(name)
        except OptionError as e:
            raise AttributeError(str(e)) from None

    def get_config(self) -> Configuration:
        return self.__config(None)


class _BoundConfiguration:
    def __init__(self, obj: Any, objtype: type, infos: Configuration.Infos, specific_owner: Optional[type] = None) -> None:
        self.__obj: Any = obj
        self.__type: type = objtype
        self.__infos: Configuration.Infos = infos
        self.__owner: Optional[type] = specific_owner

    def known_options(self) -> FrozenSet[str]:
        return self.__infos.options

    def __getitem__(self, option: str) -> Any:
        return self.get(option)

    @overload
    def get(self, option: str) -> Any:
        ...

    @overload
    def get(self, option: str, copy: bool) -> Any:
        ...

    def get(self, option: str, copy: Optional[bool] = None) -> Any:
        if not option:
            raise EmptyOptionNameError()
        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        if options and option not in options:
            raise UnknownOptionError(option)
        try:
            value: Any = getattr(self.__obj, self.__get_attribute(option))
        except AttributeError:
            raise UnregisteredOptionError(option) from None
        if copy is None:
            copy = infos.value_autocopy_get.get(option, infos.autocopy)
        if copy:
            try:
                return deepcopy(value)
            except CopyError:
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
        if not option:
            raise EmptyOptionNameError()

        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        if options and option not in options:
            raise UnknownOptionError(option)

        if copy is None:
            copy = infos.value_autocopy_set.get(option, infos.autocopy)

        obj: Any = self.__obj
        update: Optional[Callable[[Any], None]] = infos.update
        value_update: Optional[Callable[[Any, str, Any], None]] = infos.value_update.get(option)
        value_validator: Optional[Callable[[Any, Any], Any]] = infos.value_validator.get(option)
        attribute: str = self.__get_attribute(option)

        def copy_value(value: Any) -> Any:
            if not copy:
                return value
            try:
                return deepcopy(value)
            except CopyError:
                return value

        if callable(value_validator):
            value = value_validator(obj, value)
        need_update: bool = False
        try:
            actual_value: Any = getattr(obj, attribute)
            if actual_value != value:
                raise AttributeError
        except AttributeError:
            value = copy_value(value)
            setattr(obj, attribute, value)
            need_update = True

        if need_update:
            if callable(value_update):
                value_update(obj, option, value)
            if callable(update):
                update(obj)

    def __delitem__(self, option: str) -> None:
        return self.remove(option)

    def remove(self, option: str) -> None:
        if not option:
            raise EmptyOptionNameError()
        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        obj: Any = self.__obj
        update: Optional[Callable[[Any], None]] = infos.update
        if options and option not in options:
            raise UnknownOptionError(option)
        try:
            delattr(obj, self.__get_attribute(option))
        except AttributeError:
            raise UnregisteredOptionError(option) from None
        else:
            if callable(update):
                update(obj)

    def __call__(self, *, __copy: Optional[Union[bool, Dict[str, bool]]] = None, **kwargs: Any) -> None:
        if not kwargs:
            raise TypeError("No config params given")
        infos: Configuration.Infos = self.__infos
        autocopy: bool = infos.autocopy
        options: FrozenSet[str] = infos.options
        obj: Any = self.__obj
        update: Optional[Callable[[Any], None]] = infos.update
        value_update_get: Callable[[str], Optional[Callable[[Any, str, Any], None]]] = infos.value_update.get
        value_validator_get: Callable[[str], Optional[Callable[[Any, Any], Any]]] = infos.value_validator.get
        get_attribute: Callable[[str], str] = self.__get_attribute

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
                return deepcopy(value)
            except CopyError:
                return value

        need_update: bool = False
        values: List[Tuple[str, Any]] = list()
        value_updates: List[Tuple[str, Any, Callable[[Any, str, Any], None]]] = list()

        for option, value in kwargs.items():
            if options and option not in options:
                raise UnknownOptionError(option)
            value_validator: Optional[Callable[[Any, Any], None]] = value_validator_get(option)
            if callable(value_validator):
                value = value_validator(obj, value)
            attribute: str = get_attribute(option)
            try:
                actual_value: Any = getattr(obj, attribute)
                if actual_value != value:
                    raise AttributeError
            except AttributeError:
                value = copy_value(option, value)
                values.append((attribute, value))
                need_update = True
                value_update: Optional[Callable[[Any, str, Any], None]] = value_update_get(option)
                if callable(value_update):
                    value_updates.append((option, value, value_update))

        for attribute, value in values:
            setattr(obj, attribute, value)
        if need_update:
            for option, value, updater in value_updates:
                updater(obj, option, value)
            if callable(update):
                update(obj)

    def __get_attribute(self, option: str) -> str:
        objtype: type = self.__type
        owner: type
        infos: Configuration.Infos = self.__infos
        attribute_class_owner: Dict[str, type] = infos.attribute_class_owner
        if attribute_class_owner:
            specific_owner: Optional[type] = self.__owner
            if specific_owner is not None:
                owner = specific_owner
            elif objtype is infos.owner:
                owner = attribute_class_owner.get(option, objtype)
            else:
                owner = objtype
        else:
            owner = objtype
        return f"_{owner.__name__}__{option}"
