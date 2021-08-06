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


class Configuration:
    class Infos:
        options: FrozenSet[str]
        update: Optional[Callable[[Any], None]]
        value_update: Dict[str, Callable[[Any, str, Any], None]]
        value_validator: Dict[str, Callable[[Any, Any], Any]]
        autocopy: bool
        value_autocopy_get: Dict[str, bool]
        value_autocopy_set: Dict[str, bool]

    @overload
    def __init__(self, *, autocopy: bool = False) -> None:
        ...

    @overload
    def __init__(self, *known_options: str, autocopy: bool = False) -> None:
        ...

    def __init__(self, *known_options: str, autocopy: bool = False) -> None:
        if any(not option for option in known_options):
            raise ValueError("Configuration option must not be empty")
        self.__infos: Configuration.Infos = Configuration.Infos()
        self.__infos.options = frozenset(known_options)
        self.__infos.update = None
        self.__infos.value_update = dict()
        self.__infos.value_validator = dict()
        self.__infos.autocopy = autocopy
        self.__infos.value_autocopy_get = dict()
        self.__infos.value_autocopy_set = dict()
        self.__owner: Optional[type] = None

    def copy(self, *added_known_options: str) -> Configuration:
        c: Configuration = Configuration()
        c.__infos = deepcopy(self.__infos)
        c.__infos.options = frozenset((*c.__infos.options, *added_known_options))
        return c

    def __set_name__(self, owner: type, name: str) -> None:
        self.__owner = owner
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
    def set_autocopy(self, name: str, /, *, copy_on_get: Optional[bool]) -> None:
        ...

    @overload
    def set_autocopy(self, name: str, /, *, copy_on_set: Optional[bool]) -> None:
        ...

    @overload
    def set_autocopy(self, name: str, /, *, copy_on_get: Optional[bool], copy_on_set: Optional[bool]) -> None:
        ...

    def set_autocopy(self, arg1: Union[bool, str], /, **kwargs: Optional[bool]) -> None:
        if isinstance(arg1, bool) and not kwargs:
            self.__infos.autocopy = arg1
        elif isinstance(arg1, str) and ("copy_on_get" in kwargs or "copy_on_set" in kwargs):
            options: FrozenSet[str] = self.__infos.options
            if options and arg1 not in options:
                raise KeyError(f"Unknown config option {arg1!r}")
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
        owner: Optional[type] = self.__owner
        if owner is not None:
            if objtype is None or objtype is type(obj):
                objtype = owner
        elif objtype is None:
            objtype = type(obj)
        return _BoundConfiguration(obj, objtype, self.__infos)

    @overload
    def get_updater(self) -> Optional[Callable[[Any], None]]:
        ...

    @overload
    def get_updater(self, name: str) -> Optional[Callable[[Any, str, Any], None]]:
        ...

    def get_updater(self, name: Optional[str] = None) -> Union[Callable[[Any], None], Callable[[Any, str, Any], None], None]:
        if name is None:
            return self.__infos.update
        options: FrozenSet[str] = self.__infos.options
        if options and name not in options:
            raise KeyError(f"Unknown config option {name!r}")
        return self.__infos.value_update.get(name)

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
            if options and arg not in options:
                raise KeyError(f"Unknown config option {arg!r}")

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

    def get_validator(self, name: str) -> Optional[Callable[[Any, Any], Any]]:
        options: FrozenSet[str] = self.__infos.options
        if options and name not in options:
            raise KeyError(f"Unknown config option {name!r}")
        return self.__infos.value_validator.get(name)

    @overload
    def validator(self, name: str, /) -> Callable[[_ValueValidator], _ValueValidator]:
        ...

    @overload
    def validator(self, name: str, func: type, /) -> type:
        ...

    @overload
    def validator(self, name: str, func: Tuple[type, ...], /) -> Tuple[type, ...]:
        ...

    @overload
    def validator(self, name: str, func: Optional[_ValueValidator], /) -> Optional[_ValueValidator]:
        ...

    def validator(
        self, name: str, /, *func_args: Optional[Union[_ValueValidator, type, Tuple[type, ...]]]
    ) -> Union[Callable[[_ValueValidator], _ValueValidator], _ValueValidator, type, Tuple[type, ...], None]:
        options: FrozenSet[str] = self.__infos.options
        if options and name not in options:
            raise KeyError(f"Unknown config option {name!r}")

        if not func_args:

            def decorator(func: _ValueValidator) -> _ValueValidator:
                self.__infos.value_validator[name] = _make_function_wrapper(func)
                return func

            return decorator

        if len(func_args) > 1:
            raise TypeError("Invalid arguments")
        func: Optional[Union[_ValueValidator, type, Tuple[type, ...]]] = func_args[0]
        if func is None:
            self.__infos.value_validator.pop(name, None)
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

            self.__infos.value_validator[name] = _make_function_wrapper(type_checker)
        else:
            self.__infos.value_validator[name] = _make_function_wrapper(func)
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
        except KeyError as e:
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
        config.remove(name)

    def get_config(self) -> Configuration:
        return self.__config(None)


class _BoundConfiguration:
    def __init__(self, obj: Any, objtype: type, infos: Configuration.Infos) -> None:
        self.__obj: Any = obj
        self.__type: type = objtype
        self.__infos: Configuration.Infos = infos

    def known_options(self) -> FrozenSet[str]:
        return self.__infos.options

    def __getitem__(self, name: str) -> Any:
        return self.get(name)

    @overload
    def get(self, name: str) -> Any:
        ...

    @overload
    def get(self, name: str, copy: bool) -> Any:
        ...

    def get(self, name: str, copy: Optional[bool] = None) -> Any:
        if not name:
            raise KeyError("Empty string option")
        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        if options and name not in options:
            raise KeyError(f"Unknown option {name!r}")
        try:
            value: Any = getattr(self.__obj, f"_{self.__type.__name__}__{name}")
        except AttributeError:
            raise KeyError(f"Unregistered option {name!r}") from None
        if copy is None:
            copy = infos.value_autocopy_get.get(name, infos.autocopy)
        if copy:
            try:
                return deepcopy(value)
            except CopyError:
                pass
        return value

    def __setitem__(self, name: str, value: Any) -> None:
        return self.set(name, value)

    @overload
    def set(self, name: str, value: Any) -> None:
        ...

    @overload
    def set(self, name: str, value: Any, copy: bool) -> None:
        ...

    def set(self, name: str, value: Any, copy: Optional[bool] = None) -> None:
        if not name:
            raise KeyError("Empty string option")

        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        if options and name not in options:
            raise KeyError(f"Unknown config option {name!r}")

        if copy is None:
            copy = infos.value_autocopy_set.get(name, infos.autocopy)

        obj: Any = self.__obj
        objtype: type = self.__type
        update: Optional[Callable[[Any], None]] = infos.update
        value_update: Optional[Callable[[Any, str, Any], None]] = infos.value_update.get(name)
        value_validator: Optional[Callable[[Any, Any], Any]] = infos.value_validator.get(name)
        attribute: str = f"_{objtype.__name__}__{name}"

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
                value_update(obj, name, value)
            if callable(update):
                update(obj)

    def __delitem__(self, name: str) -> None:
        return self.remove(name)

    def remove(self, name: str) -> None:
        if not name:
            raise KeyError("Empty string option")
        infos: Configuration.Infos = self.__infos
        options: FrozenSet[str] = infos.options
        obj: Any = self.__obj
        objtype: type = self.__type
        update: Optional[Callable[[Any], None]] = infos.update
        if options and name not in options:
            raise KeyError(f"Unknown option {name!r}")
        try:
            delattr(obj, f"_{objtype.__name__}__{name}")
        except AttributeError:
            raise KeyError(f"Unregistered option {name!r}") from None
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
        objtype: type = self.__type
        update: Optional[Callable[[Any], None]] = infos.update
        value_update_get: Callable[[str], Optional[Callable[[Any, str, Any], None]]] = infos.value_update.get
        value_validator_get: Callable[[str], Optional[Callable[[Any, Any], Any]]] = infos.value_validator.get

        def copy_value(name: str, value: Any) -> Any:
            copy: bool
            if __copy is None:
                copy = infos.value_autocopy_set.get(name, autocopy)
            elif isinstance(__copy, bool):
                copy = __copy
            else:
                copy = __copy.get(name, infos.value_autocopy_set.get(name, autocopy))
            if not copy:
                return value
            try:
                return deepcopy(value)
            except CopyError:
                return value

        need_update: bool = False
        values: List[Tuple[str, Any]] = list()
        value_updates: List[Tuple[str, Any, Callable[[Any, str, Any], None]]] = list()

        for name, value in kwargs.items():
            if options and name not in options:
                raise KeyError(f"Unknown config option {name!r}")
            value_validator: Optional[Callable[[Any, Any], None]] = value_validator_get(name)
            if callable(value_validator):
                value = value_validator(obj, value)
            attribute: str = f"_{objtype.__name__}__{name}"
            try:
                actual_value: Any = getattr(obj, attribute)
                if actual_value != value:
                    raise AttributeError
            except AttributeError:
                value = copy_value(name, value)
                values.append((attribute, value))
                need_update = True
                value_update: Optional[Callable[[Any, str, Any], None]] = value_update_get(name)
                if callable(value_update):
                    value_updates.append((name, value, value_update))

        for attribute, value in values:
            setattr(obj, attribute, value)
        if need_update:
            for name, value, updater in value_updates:
                updater(obj, name, value)
            if callable(update):
                update(obj)


if __name__ == "__main__":

    class Configurable:
        config = Configuration("a", "b", "c", "d", autocopy=True)
        config.set_autocopy("d", copy_on_get=False, copy_on_set=False)

        a: ConfigAttribute[int] = ConfigAttribute(config)
        b: ConfigAttribute[int] = ConfigAttribute(config)
        c: ConfigAttribute[int] = ConfigAttribute(config)
        d: ConfigAttribute[Dict[str, int]] = ConfigAttribute(config)

        @config.updater("a")
        @config.updater("b")
        @config.updater("c")
        def _on_update_field(self, name: str, val: int) -> None:
            print(f"{self}: {name} set to {val}")

        config.updater("d", lambda self, name, val: print((self, name, val)))

        @config.validator("a")
        @config.validator("b")
        @config.validator("c")
        @staticmethod
        def __valid_int(val: Any) -> int:
            return max(int(val), 0)

        config.validator("d", dict)

        @config.updater
        def _update(self) -> None:
            print("Update object")

    class SubConfigurable(Configurable):
        config = Configurable.config.copy()

        @config.updater("a")
        def __special_case_a(self, name: str, val: int) -> None:
            print(f"----------Special case for {name}--------")
            self._on_update_field(name, val)

        def _update(self) -> None:
            super()._update()
            print("Subfunction update")

    def main() -> None:
        c = SubConfigurable()
        c.config["a"] = 4
        c.config(a=6, b=5, c=-9)
        print(c.config.known_options())
        print(c.config["a"])
        c.config.set("a", 6)
        c.config(a=6, b=5, c=-12)

        c.a += 2
        print(c.a)

        c.d = d = {"a": 5}
        print(c.d is d)

    main()
