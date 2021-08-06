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
    overload,
)
from copy import deepcopy, Error as CopyError


_T = TypeVar("_T")

_Updater = TypeVar("_Updater", bound=Union[Callable[[Any], None], Callable[[], None]])
_ValueUpdater = TypeVar("_ValueUpdater", bound=Union[Callable[[Any, str, Any], None], Callable[[str, Any], None]])
_ValueValidator = TypeVar("_ValueValidator", bound=Union[Callable[[Any, Any], Any], Callable[[Any], Any]])


def _make_function_wrapper(func: Any) -> Callable[..., Any]:
    def wrapper(obj: Any, /, *args: Any, **kwargs: Any) -> Any:
        try:
            _func = func.__get__(obj, type(obj))
            if not callable(_func):
                raise TypeError
            _func_name: str = _func.__name__
            if _func_name != "<lambda>":
                _sub_func = getattr(obj, _func_name, _func)
                if _sub_func is not _func and callable(_sub_func):
                    _func = _sub_func
        except (AttributeError, TypeError):
            return func(obj, *args, **kwargs)
        return _func(*args, **kwargs)

    return wrapper


class Configuration:
    class Infos:
        keys: FrozenSet[str]
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
    def __init__(self, *known_keys: str, autocopy: bool = False) -> None:
        ...

    def __init__(self, *known_keys: str, autocopy: bool = False) -> None:
        if any(not key for key in known_keys):
            raise ValueError("Configuration key must not be empty")
        self.__infos: Configuration.Infos = Configuration.Infos()
        self.__infos.keys = frozenset(known_keys)
        self.__infos.update = None
        self.__infos.value_update = dict()
        self.__infos.value_validator = dict()
        self.__infos.autocopy = autocopy
        self.__infos.value_autocopy_get = dict()
        self.__infos.value_autocopy_set = dict()
        self.__owner: Optional[type] = None

    def copy(self, *added_known_keys: str) -> Configuration:
        c: Configuration = Configuration(*self.__infos.keys, *added_known_keys, autocopy=self.__infos.autocopy)
        c.__infos.update = self.__infos.update
        c.__infos.value_update = self.__infos.value_update.copy()
        c.__infos.value_validator = self.__infos.value_validator.copy()
        c.__infos.value_autocopy_get = self.__infos.value_autocopy_get.copy()
        c.__infos.value_autocopy_set = self.__infos.value_autocopy_set.copy()
        return c

    def __set_name__(self, owner: type, name: str) -> None:
        self.__owner = owner
        for attr in dir(owner):
            obj: Any = getattr(owner, attr)
            if isinstance(obj, ConfigAttribute) and obj.get_config() is not self:
                new_obj: ConfigAttribute[Any] = ConfigAttribute(self)
                setattr(owner, attr, new_obj)
                new_obj.__set_name__(owner, attr)

    def known_keys(self) -> FrozenSet[str]:
        return self.__infos.keys

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
            keys: FrozenSet[str] = self.__infos.keys
            if keys and arg1 not in keys:
                raise KeyError(f"Unknown config key {arg1!r}")
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
    def updater(self, arg: _Updater) -> _Updater:
        ...

    @overload
    def updater(self, arg: str) -> Callable[[_ValueUpdater], _ValueUpdater]:
        ...

    def updater(self, arg: Union[_Updater, str]) -> Union[_Updater, Callable[[_ValueUpdater], _ValueUpdater]]:
        if isinstance(arg, str):
            config_name: str = arg

            def decorator(func: _ValueUpdater) -> _ValueUpdater:
                self.__infos.value_update[config_name] = _make_function_wrapper(func)
                return func

            return decorator

        self.__infos.update = _make_function_wrapper(arg)
        return arg

    def validator(self, config_name: str) -> Callable[[_ValueValidator], _ValueValidator]:
        def decorator(func: _ValueValidator) -> _ValueValidator:
            self.__infos.value_validator[config_name] = _make_function_wrapper(func)
            return func

        return decorator


class ConfigAttribute(Generic[_T]):
    def __init__(self, config: Configuration) -> None:
        self.__name: str = str()
        self.__config = config.__get__
        self.__known_keys: FrozenSet[str] = config.known_keys()

    def __set_name__(self, owner: type, name: str) -> None:
        if len(name) == 0:
            raise ValueError(f"Attribute name must not be empty")
        known_keys: FrozenSet[str] = self.__known_keys
        if known_keys and name not in known_keys:
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

    def known_keys(self) -> FrozenSet[str]:
        return self.__infos.keys

    @overload
    def get(self, name: str) -> Any:
        ...

    @overload
    def get(self, name: str, copy: bool) -> Any:
        ...

    def get(self, name: str, copy: Optional[bool] = None) -> Any:
        if not name:
            raise KeyError("Empty string key")
        infos: Configuration.Infos = self.__infos
        keys: FrozenSet[str] = infos.keys
        if keys and name not in keys:
            raise KeyError(f"Unknown key {name!r}")
        try:
            value: Any = getattr(self.__obj, f"_{self.__type.__name__}__{name}")
        except AttributeError:
            raise KeyError(f"Unregistered key {name!r}") from None
        if copy is None:
            copy = infos.value_autocopy_get.get(name, infos.autocopy)
        if copy:
            try:
                return deepcopy(value)
            except CopyError:
                pass
        return value

    @overload
    def set(self, name: str, value: Any) -> None:
        ...

    @overload
    def set(self, name: str, value: Any, copy: bool) -> None:
        ...

    def set(self, name: str, value: Any, copy: Optional[bool] = None) -> None:
        if not name:
            raise KeyError("Empty string key")

        infos: Configuration.Infos = self.__infos
        keys: FrozenSet[str] = infos.keys
        if keys and name not in keys:
            raise KeyError(f"Unknown config key {name!r}")

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

    def remove(self, name: str) -> None:
        if not name:
            raise KeyError("Empty string key")
        keys: FrozenSet[str] = self.__infos.keys
        if keys and name not in keys:
            raise KeyError(f"Unknown key {name!r}")
        try:
            delattr(self.__obj, f"_{self.__type.__name__}__{name}")
        except AttributeError:
            raise KeyError(f"Unregistered key {name!r}") from None

    def __call__(self, *, __copy: Optional[Union[bool, Dict[str, bool]]] = None, **kwargs: Any) -> None:
        if not kwargs:
            raise TypeError("No config params given")
        infos: Configuration.Infos = self.__infos
        autocopy: bool = infos.autocopy
        keys: FrozenSet[str] = infos.keys
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
        value_updates: List[Tuple[str, Any, Callable[[Any, str, Any], None]]] = list()

        for name, value in kwargs.items():
            if keys and name not in keys:
                raise KeyError(f"Unknown config key {name!r}")
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
                setattr(obj, attribute, value)
                need_update = True
                value_update: Optional[Callable[[Any, str, Any], None]] = value_update_get(name)
                if callable(value_update):
                    value_updates.append((name, value, value_update))

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

        config.updater("d")(lambda self, name, val: print((self, name, val)))

        @config.validator("a")
        @config.validator("b")
        @config.validator("c")
        @staticmethod
        def __valid_int(val: Any) -> int:
            return max(int(val), 0)

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
        c.config.set("a", 4)
        c.config(a=6, b=5, c=-9)
        print(c.config.known_keys())
        print(c.config.get("a"))
        c.config.set("a", 6)
        c.config(a=6, b=5, c=-12)

        c.a += 2
        print(c.a)

        c.d = d = {"a": 5}
        print(c.d is d)

    main()
