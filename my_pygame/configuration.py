# -*- coding: Utf-8 -*

from __future__ import annotations
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
    overload,
)
from copy import deepcopy, Error as CopyError


class _BoundConfiguration:
    def __init__(
        self,
        obj: Any,
        objtype: type,
        keys: Configuration.Keys,
        update: Callable[[Any], None],
        value_update: Dict[str, Callable[[Any, str, Any], None]],
        value_validator: Dict[str, Callable[[Any, Any], Any]],
        autocopy: bool,
    ) -> None:
        self.__obj: Any = obj
        self.__type: type = objtype
        self.__keys: Configuration.Keys = keys
        self.__update: Callable[[Any], None] = update
        self.__value_update: Dict[str, Callable[[Any, str, Any], None]] = value_update
        self.__value_validator: Dict[str, Callable[[Any, Any], Any]] = value_validator
        self.__autocopy: bool = autocopy

    def __iter__(self) -> Iterator[str]:
        return self.__keys.registered.__iter__()

    def registered_keys(self) -> FrozenSet[str]:
        return frozenset(self.__keys.registered)

    def known_keys(self) -> FrozenSet[str]:
        return self.__keys.known

    @overload
    def get(self, name: str) -> Any:
        ...

    @overload
    def get(self, name: str, copy: bool) -> Any:
        ...

    def get(self, name: str, copy: Optional[bool] = None) -> Any:
        if not name:
            raise KeyError("Empty string key")
        if self.__keys.known and name not in self.__keys.known:
            raise KeyError(f"Unknown key {name!r}")
        if name not in self.__keys.registered:
            raise KeyError(f"Unregistered key {name!r}")
        value: Any = getattr(self.__obj, f"_{self.__type.__name__}__{name}")
        if copy is None:
            copy = self.__autocopy
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

        keys: Configuration.Keys = self.__keys
        if keys.known and name not in keys.known:
            raise KeyError(f"Unknown config key {name!r}")

        if copy is None:
            copy = self.__autocopy

        obj: Any = self.__obj
        objtype: type = self.__type
        update: Callable[[Any], None] = self.__update
        value_update: Optional[Callable[[Any, str, Any], None]] = self.__value_update.get(name)
        value_validator: Optional[Callable[[Any, Any], Any]] = self.__value_validator.get(name)
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
            keys.registered.add(name)

        if need_update:
            if callable(value_update):
                value_update(obj, name, value)
            update(obj)

    def remove(self, name: str) -> None:
        if not name:
            raise KeyError("Empty string key")
        if self.__keys.known and name not in self.__keys.known:
            raise KeyError(f"Unknown key {name!r}")
        if name not in self.__keys.registered:
            raise KeyError(f"Unregistered key {name!r}")
        delattr(self.__obj, f"_{self.__type.__name__}__{name}")
        self.__keys.registered.remove(name)

    def __call__(self, *, __copy: Optional[Union[bool, Dict[str, bool]]] = None, **kwargs: Any) -> None:
        if not kwargs:
            raise TypeError("No config params given")
        autocopy: bool = self.__autocopy
        keys: Configuration.Keys = self.__keys
        obj: Any = self.__obj
        objtype: type = self.__type
        update: Callable[[Any], None] = self.__update
        value_update_get: Callable[[str], Optional[Callable[[Any, str, Any], None]]] = self.__value_update.get
        value_validator_get: Callable[[str], Optional[Callable[[Any, Any], Any]]] = self.__value_validator.get

        def copy_value(name: str, value: Any) -> Any:
            copy: bool
            if __copy is None:
                copy = autocopy
            elif isinstance(__copy, bool):
                copy = __copy
            else:
                copy = __copy.get(name, autocopy)
            if not copy:
                return value
            try:
                return deepcopy(value)
            except CopyError:
                return value

        need_update: bool = False
        value_updates: List[Tuple[str, Any, Callable[[Any, str, Any], None]]] = list()

        for name, value in kwargs.items():
            if keys.known and name not in keys.known:
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
            keys.registered.add(name)

        if need_update:
            for name, value, updater in value_updates:
                updater(obj, name, value)
            update(obj)


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
    class Updater:
        def __init__(self) -> None:
            self.__func__: Optional[Callable[[Any], None]] = None

        def __call__(self, obj: Any) -> None:
            func: Optional[Callable[[Any], None]] = self.__func__
            if callable(func):
                func(obj)

    class Keys:
        def __init__(self, known_keys: Sequence[str]) -> None:
            if any(not key for key in known_keys):
                raise ValueError("Configuration key must not be empty")
            self.known: FrozenSet[str] = frozenset(known_keys)
            self.registered: Set[str] = set()

    @overload
    def __init__(self, *, autocopy: bool = False) -> None:
        ...

    @overload
    def __init__(self, *known_keys: str, autocopy: bool = False) -> None:
        ...

    def __init__(self, *known_keys: str, autocopy: bool = False) -> None:
        self.__keys: Configuration.Keys = Configuration.Keys(known_keys)
        self.__update: Configuration.Updater = Configuration.Updater()
        self.__value_update: Dict[str, Callable[[Any, str, Any], None]] = dict()
        self.__value_validator: Dict[str, Callable[[Any, Any], Any]] = dict()
        self.__autocopy: bool = autocopy

    def __iter__(self) -> Iterator[str]:
        return self.__keys.registered.__iter__()

    def registered_keys(self) -> FrozenSet[str]:
        return frozenset(self.__keys.registered)

    def known_keys(self) -> FrozenSet[str]:
        return self.__keys.known

    @overload
    def __get__(self, obj: None, objtype: Optional[type] = None) -> Configuration:
        ...

    @overload
    def __get__(self, obj: Any, objtype: Optional[type] = None) -> _BoundConfiguration:
        ...

    def __get__(self, obj: Any, objtype: Optional[type] = None) -> Union[Configuration, _BoundConfiguration]:
        if obj is None:
            return self
        if objtype is None:
            objtype = type(obj)
        return _BoundConfiguration(
            obj, objtype, self.__keys, self.__update, self.__value_update, self.__value_validator, self.__autocopy
        )

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
                self.__value_update[config_name] = _make_function_wrapper(func)
                return func

            return decorator

        self.__update.__func__ = _make_function_wrapper(arg)
        return arg

    def validator(self, config_name: str) -> Callable[[_ValueValidator], _ValueValidator]:
        def decorator(func: _ValueValidator) -> _ValueValidator:
            self.__value_validator[config_name] = _make_function_wrapper(func)
            return func

        return decorator


class ConfigAttribute(Generic[_T]):
    def __init__(self, config: Configuration, *, copy_on_get: Optional[bool] = None, copy_on_set: Optional[bool] = None) -> None:
        self.__name: str = str()
        self.__config = config.__get__
        self.__known_keys: FrozenSet[str] = config.known_keys()
        self.__copy_get: Optional[bool] = copy_on_get
        self.__copy_set: Optional[bool] = copy_on_set
        self.__updater: Any = None
        self.__validator: Any = None

    def __set_name__(self, owner: type, name: str) -> None:
        if len(name) == 0:
            raise ValueError(f"Attribute name must not be empty")
        known_keys: FrozenSet[str] = self.__known_keys
        if known_keys and name not in known_keys:
            raise ValueError(f"Invalid attribute name {name!r}: Not known by configuration object")
        self.__name = name
        config: Configuration = self.__config(None)
        if self.__updater is not None:
            config.updater(name)(self.__updater)
        if self.__validator is not None:
            config.validator(name)(self.__validator)

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
            value: _T = config.get(name, copy=self.__copy_get)  # type: ignore[arg-type]
        except KeyError as e:
            raise AttributeError(str(e)) from None
        return value

    def __set__(self, obj: Any, value: _T) -> None:
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = self.__config(obj)
        config.set(name, value, copy=self.__copy_set)  # type: ignore[arg-type]

    def __delete__(self, obj: Any) -> None:
        name: str = self.__name
        if not name:
            raise ValueError("No name was given. Use __set_name__ method.")
        config: _BoundConfiguration = self.__config(obj)
        config.remove(name)

    def updater(self, func: _ValueUpdater) -> _ValueUpdater:
        self.__updater = func
        if self.__name:
            self.__config(None).updater(self.__name)(func)
        return func

    def validator(self, func: _ValueValidator) -> _ValueValidator:
        self.__validator = func
        if self.__name:
            self.__config(None).validator(self.__name)(func)
        return func


if __name__ == "__main__":

    class Configurable:
        config = Configuration("a", "b", "c", "d", autocopy=True)

        a: ConfigAttribute[int] = ConfigAttribute(config)
        b: ConfigAttribute[int] = ConfigAttribute(config)
        c: ConfigAttribute[int] = ConfigAttribute(config)
        d: ConfigAttribute[Dict[str, int]] = ConfigAttribute(config, copy_on_get=False, copy_on_set=False)

        @a.updater
        @config.updater("b")
        @config.updater("c")
        def __on_update_field(self, name: str, val: int) -> None:
            print(f"{self}: {name} set to {val}")

        d.updater(lambda self, name, val: print((self, name, val)))

        @config.validator("a")
        @config.validator("b")
        @c.validator
        @staticmethod
        def __valid_int(val: Any) -> int:
            return max(int(val), 0)

        @config.updater
        def _update(self) -> None:
            print("Update object")

    class SubConfigurable(Configurable):
        def _update(self) -> None:
            super()._update()
            print("Subfunction update")

    def main() -> None:
        c = SubConfigurable()
        c.config.set("a", 4)
        c.config(a=6, b=5, c=-9)
        print(c.config.registered_keys())
        print(c.config.get("a"))
        c.config.set("a", 6)
        c.config(a=6, b=5, c=-12)

        c.a += 2
        print(c.a)

        c.d = d = {"a": 5}
        print(c.d is d)

    main()
