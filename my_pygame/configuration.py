# -*- coding: Utf-8 -*

from __future__ import annotations
from functools import wraps
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
    TypeVar,
    Union,
    cast,
    overload,
)
from copy import deepcopy
from contextlib import ExitStack, contextmanager


_T = TypeVar("_T")

_Func = TypeVar("_Func", bound=Callable[..., Any])
_Updater = TypeVar("_Updater", bound=Union[Callable[[Any], None], Callable[[], None]])
_ValueUpdater = TypeVar("_ValueUpdater", bound=Union[Callable[[Any, str, Any], None], Callable[[str, Any], None]])
_NoNameValueUpdater = TypeVar("_NoNameValueUpdater", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])
_ValueValidator = TypeVar("_ValueValidator", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])
_ValueGetter = TypeVar("_ValueGetter", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])


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


def _make_function_wrapper(func: Any, *, already_wrapper: bool = False, check_override: bool = True) -> Callable[..., Any]:
    if getattr(func, "__boundconfiguration_wrapper__", False) and callable(func):
        return cast(Callable[..., Any], func)

    if already_wrapper:
        wrapper: Callable[..., Any] = func
    elif not getattr(func, "__no_object__", False):

        @wraps(func)
        def wrapper(self: object, /, *args: Any, **kwargs: Any) -> Any:
            try:
                _func = getattr(func, "__get__")(self, type(self))
                if not callable(_func):
                    raise TypeError
                if check_override:
                    _func_name: str = _func.__name__
                    if _func_name != "<lambda>":
                        _sub_func = getattr(self, _func_name, _func)
                        if _sub_func is not _func and callable(_sub_func):
                            _func = _sub_func
            except (AttributeError, TypeError):
                try:
                    return func(self, *args, **kwargs)
                except TypeError as exc:
                    try:
                        return func(*args, **kwargs)
                    except TypeError as subexc:
                        raise subexc from exc
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
    class config_initializer_method:
        def __init__(self, func: Callable[..., Any], obj: object, cls: Optional[type], config: Configuration) -> None:
            self.__func__: Callable[..., Any] = _make_function_wrapper(func, check_override=False)
            self.__self__: object = obj
            self.__type: Optional[type] = cls
            self.__config: Callable[[object, Optional[type]], _BoundConfiguration] = config.__get__

        def __repr__(self) -> str:
            return f"<{type(self).__name__} object at {id(self):#x}>"

        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            func: Callable[..., Any] = self.__func__
            obj: object = self.__self__
            cls: Optional[type] = self.__type
            bound_config: _BoundConfiguration = self.__config(obj, cls)
            with bound_config.initialization():
                return func(obj, *args, **kwargs)

    def __init__(self, func: Callable[..., Any]) -> None:
        self.__func__: Callable[..., Any] = func

    def __get__(self, obj: object, objtype: Optional[type] = None) -> Callable[..., Any]:
        func: Callable[..., Any] = self.__func__
        if obj is None:
            try:
                func = getattr(func, "__get__")(None, objtype)
            except (AttributeError, TypeError):
                pass
            return func
        cls: type = objtype if objtype is not None else type(obj)
        config: Configuration = _retrieve_configuration(cls)
        return self.config_initializer_method(func, obj, objtype, config)


def initializer(func: _Func) -> _Func:
    return cast(_Func, _ConfigInitializer(func))


def no_object(func: _Func) -> _Func:
    setattr(func, "__no_object__", True)
    return func


class Configuration:
    class Infos:
        def __init__(self, known_options: Sequence[str], autocopy: bool) -> None:
            self.options: FrozenSet[str] = frozenset(known_options)
            self.update: Optional[Callable[[object], None]] = None
            self.value_getter: Dict[str, Callable[[object, Any], Any]] = dict()
            self.value_update: Dict[str, Callable[[object, str, Any], None]] = dict()
            self.value_validator: Dict[str, Callable[[object, Any], Any]] = dict()
            self.autocopy: bool = autocopy
            self.value_autocopy_get: Dict[str, bool] = dict()
            self.value_autocopy_set: Dict[str, bool] = dict()
            self.attribute_class_owner: Dict[str, type] = dict()
            self.owner: Optional[type] = None

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
            infos = deepcopy(main_parent.__infos)
            infos.options = infos.options.union(opt for p in parent for opt in p.__infos.options).union(known_options)
            for parent_infos in (p.__infos for p in parent):
                infos.value_getter = parent_infos.value_getter | infos.value_getter
                infos.value_update = parent_infos.value_update | infos.value_update
                infos.value_validator = parent_infos.value_validator | infos.value_validator
                infos.value_autocopy_get = parent_infos.value_autocopy_get | infos.value_autocopy_get
                infos.value_autocopy_set = parent_infos.value_autocopy_set | infos.value_autocopy_set
                infos.attribute_class_owner = parent_infos.attribute_class_owner | infos.attribute_class_owner
            if autocopy is not None:
                infos.autocopy = autocopy

        self.__infos: Configuration.Infos = infos
        self.__no_parent_ownership: Set[str] = set()
        self.__bound_class: Optional[type] = None

    def __set_name__(self, owner: type, name: str) -> None:
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
        for obj in vars(owner).values():
            if isinstance(obj, ConfigAttribute) and infos.options:
                attr_name: str = obj.name
                if attr_name and attr_name not in infos.options:
                    raise UnknownOptionError(attr_name)
            elif isinstance(obj, Configuration) and obj is not self:
                raise TypeError(f"A class can't have several {Configuration.__name__!r} objects")
        _register_configuration(owner, self)

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

    def remove_parent_ownership(self, option: str) -> None:
        if not option:
            raise EmptyOptionNameError()
        infos: Configuration.Infos = self.__infos
        if infos.options and option not in infos.options:
            raise UnknownOptionError(option)
        self.__no_parent_ownership.add(option)
        if self.__bound_class is not None and infos.options:
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
        bound_references: Dict[object, _BoundConfiguration] = self.__references
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

    def get_option_getter(self, option: str) -> Optional[Callable[[object, Any], Any]]:
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise UnknownOptionError(option)
        return self.__infos.value_getter.get(option)

    @overload
    def getter(self, option: str, /) -> Callable[[_ValueGetter], _ValueGetter]:
        ...

    @overload
    def getter(self, option: str, func: _ValueGetter, /) -> _ValueGetter:
        ...

    @overload
    def getter(self, option: str, func: None, /) -> None:
        ...

    def getter(
        self, option: str, /, *func_args: Union[_ValueGetter, None]
    ) -> Union[Callable[[_ValueGetter], _ValueGetter], _ValueGetter, None]:
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise UnknownOptionError(option)

        if not func_args:

            def decorator(func: _ValueGetter) -> _ValueGetter:
                self.__infos.value_getter[option] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[_ValueGetter] = func_args[0]
        if func is None:
            self.__infos.value_getter.pop(option, None)
        else:
            self.__infos.value_getter[option] = _make_function_wrapper(func)
        return func

    @overload
    def get_updater(self) -> Optional[Callable[[object], None]]:
        ...

    @overload
    def get_updater(self, option: str) -> Optional[Callable[[object, str, Any], None]]:
        ...

    def get_updater(
        self, option: Optional[str] = None
    ) -> Union[Callable[[object], None], Callable[[object, str, Any], None], None]:
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
    def updater(self, arg: str, func: _ValueUpdater, /) -> _ValueUpdater:
        ...

    @overload
    def updater(self, arg: str, func: None, /) -> None:
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

    @overload
    def updater_no_name(self, option: str, /) -> Callable[[_NoNameValueUpdater], _NoNameValueUpdater]:
        ...

    @overload
    def updater_no_name(self, option: str, func: _NoNameValueUpdater, /) -> _NoNameValueUpdater:
        ...

    def updater_no_name(
        self, option: str, func: Optional[_NoNameValueUpdater] = None, /
    ) -> Union[_NoNameValueUpdater, Callable[[_NoNameValueUpdater], _NoNameValueUpdater]]:
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise UnknownOptionError(option)

        def decorator(func: _NoNameValueUpdater) -> _NoNameValueUpdater:
            _func = _make_function_wrapper(func)

            @wraps(func)
            def wrapper(self: object, /, name: str, value: Any) -> Any:
                return _func(self, value)

            self.updater(option, _make_function_wrapper(wrapper, already_wrapper=True))
            return func

        if func is None:
            return decorator
        return decorator(func)

    def get_validator(self, option: str) -> Optional[Callable[[object, Any], Any]]:
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise UnknownOptionError(option)
        return self.__infos.value_validator.get(option)

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
        options: FrozenSet[str] = self.__infos.options
        if not option:
            raise EmptyOptionNameError()
        if options and option not in options:
            raise UnknownOptionError(option)

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

            self.__infos.value_validator[option] = _make_function_wrapper(type_checker)
        elif isinstance(func, type) and convert:
            _value_type: type = func

            @no_object
            def value_convert(val: Any) -> Any:
                return _value_type(val)

            self.__infos.value_validator[option] = _make_function_wrapper(value_convert)
        else:
            self.__infos.value_validator[option] = _make_function_wrapper(func)
        return func


class ConfigTemplate(Configuration):
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
        self.__name: str = str()

    def __set_name__(self, owner: type, name: str) -> None:
        if len(name) == 0:
            raise ValueError(f"Attribute name must not be empty")
        self.__name = name
        config: Configuration = _retrieve_configuration(owner)
        if name not in config.known_options():
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
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        cls: type = objtype if objtype is not None else type(obj)
        config: _BoundConfiguration = _retrieve_configuration(cls).__get__(obj, objtype)
        try:
            value: _T = config.get(name)
        except OptionError as e:
            raise AttributeError(str(e)) from None
        return value

    def __set__(self, obj: object, value: _T) -> None:
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = _retrieve_configuration(type(obj)).__get__(obj)
        config.set(name, value)

    def __delete__(self, obj: object) -> None:
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = _retrieve_configuration(type(obj)).__get__(obj)
        try:
            config.remove(name)
        except OptionError as e:
            raise AttributeError(str(e)) from None

    @property
    def name(self) -> str:
        return self.__name


class _BoundConfiguration:
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
        self.__explicit_update_call: bool = False
        self.__explicit_value_update_call: bool = False
        self.__init_context: bool = False
        self.__update_register: Optional[Dict[str, None]] = None

    def known_options(self) -> FrozenSet[str]:
        return self.__infos.options

    @contextmanager
    def initialization(self) -> Iterator[_BoundConfiguration]:
        if self.__init_context:
            yield self
            return

        def cleanup() -> None:
            self.__update_call = True
            self.__explicit_update_call = False
            self.__explicit_value_update_call = False
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
            if not update_register and not self.__explicit_update_call:
                return
            infos: Configuration.Infos = self.__infos
            get_attribute = self.__get_attribute
            if update_register or self.__explicit_value_update_call:
                for option in (opt for opt in update_register if opt in infos.value_update):
                    updater_func: Callable[[object, str, Any], None] = infos.value_update[option]
                    try:
                        value: Any = getattr(bound_obj, get_attribute(option))
                    except AttributeError as exc:
                        raise UnregisteredOptionError(option) from exc
                    updater_func(bound_obj, option, value)
            update: Optional[Callable[[object], None]] = infos.update
            if callable(update):
                update(bound_obj)

    def has_initialization_context(self) -> bool:
        return self.__init_context

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
        obj: object = self.__obj
        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        if options and option not in options:
            raise UnknownOptionError(option)
        try:
            value: Any = getattr(obj, self.__get_attribute(option))
        except AttributeError as exc:
            raise UnregisteredOptionError(option) from exc
        getter: Optional[Callable[[object, Any], Any]] = infos.value_getter.get(option)
        if callable(getter):
            value = getter(obj, value)
        if copy is None:
            copy = infos.value_autocopy_get.get(option, infos.autocopy)
        if copy:
            try:
                return deepcopy(value)
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
        if not option:
            raise EmptyOptionNameError()

        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        if options and option not in options:
            raise UnknownOptionError(option)

        if copy is None:
            copy = infos.value_autocopy_set.get(option, infos.autocopy)

        obj: object = self.__obj
        update: Optional[Callable[[object], None]] = infos.update
        value_update: Optional[Callable[[object, str, Any], None]] = infos.value_update.get(option)
        value_validator: Optional[Callable[[object, Any], Any]] = infos.value_validator.get(option)
        update_register: Optional[Dict[str, None]] = self.__update_register
        attribute: str = self.__get_attribute(option)

        def copy_value(value: Any) -> Any:
            if not copy:
                return value
            try:
                return deepcopy(value)
            except:
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
            if update_register is not None:
                update_register[option] = None

        if need_update and self.__update_call:
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
        obj: object = self.__obj
        update: Optional[Callable[[object], None]] = infos.update
        update_register: Optional[Dict[str, None]] = self.__update_register
        if options and option not in options:
            raise UnknownOptionError(option)
        try:
            delattr(obj, self.__get_attribute(option))
        except AttributeError as exc:
            raise UnregisteredOptionError(option) from exc
        else:
            if update_register is not None:
                update_register.pop(option, None)
            if self.__update_call and callable(update):
                update(obj)

    def update(self, call_value_updaters: bool = True) -> None:
        if not self.__update_call:
            self.__explicit_update_call = True
            self.__explicit_value_update_call = call_value_updaters
            return
        obj: object = self.__obj
        infos: Configuration.Infos = self.__infos
        update: Optional[Callable[[object], None]] = infos.update
        if call_value_updaters:
            get_attribute: Callable[[str], str] = self.__get_attribute
            for option, value_updater in infos.value_update.items():
                try:
                    value_updater(obj, option, getattr(obj, get_attribute(option)))
                except AttributeError as exc:
                    raise UnregisteredOptionError(option) from exc
        if callable(update):
            update(obj)

    def __call__(self, *, __copy: Optional[Union[bool, Dict[str, bool]]] = None, **kwargs: Any) -> None:
        if not kwargs:
            raise TypeError("No config params given")
        infos: Configuration.Infos = self.__infos
        autocopy: bool = infos.autocopy
        options: FrozenSet[str] = infos.options
        obj: object = self.__obj
        update: Optional[Callable[[object], None]] = infos.update
        value_update_get: Callable[[str], Optional[Callable[[object, str, Any], None]]] = infos.value_update.get
        value_validator_get: Callable[[str], Optional[Callable[[object, Any], Any]]] = infos.value_validator.get
        get_attribute: Callable[[str], str] = self.__get_attribute
        update_register: Optional[Dict[str, None]] = self.__update_register

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
            except:
                return value

        need_update: bool = False
        values: List[Tuple[str, str, Any]] = list()
        value_updates: List[Tuple[str, Any, Callable[[object, str, Any], None]]] = list()

        for option, value in kwargs.items():
            if options and option not in options:
                raise UnknownOptionError(option)
            value_validator: Optional[Callable[[object, Any], None]] = value_validator_get(option)
            if callable(value_validator):
                value = value_validator(obj, value)
            attribute: str = get_attribute(option)
            try:
                actual_value: Any = getattr(obj, attribute)
                if actual_value != value:
                    raise AttributeError
            except AttributeError:
                value = copy_value(option, value)
                values.append((option, attribute, value))
                need_update = True
                value_update: Optional[Callable[[object, str, Any], None]] = value_update_get(option)
                if callable(value_update):
                    value_updates.append((option, value, value_update))

        for option, attribute, value in values:
            setattr(obj, attribute, value)
            if update_register is not None:
                update_register[option] = None
        if need_update and self.__update_call:
            for option, value, updater in value_updates:
                updater(obj, option, value)
            if callable(update):
                update(obj)

    def __get_attribute(self, option: str) -> str:
        objtype: type = self.__type
        owner: type
        infos: Configuration.Infos = self.__infos
        attribute_class_owner: Dict[str, type] = infos.attribute_class_owner
        specific_owner: Optional[type] = self.__owner
        if infos.options:
            if specific_owner is not None:
                owner = specific_owner
            elif objtype is infos.owner:
                owner = attribute_class_owner.get(option, objtype)
            else:
                owner = objtype
        else:
            owner = objtype if specific_owner is None else specific_owner
        return f"_{owner.__name__}__{option}"
