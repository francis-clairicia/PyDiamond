# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Themed objects module"""

from __future__ import annotations

__all__ = ["NoTheme", "ThemeNamespace", "ThemeType", "ThemedObject", "ThemedObjectMeta", "abstract_theme_class"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta
from contextlib import suppress
from inspect import Parameter, Signature
from operator import truth
from types import MappingProxyType
from typing import (
    Any,
    Callable,
    ClassVar,
    ContextManager,
    FrozenSet,
    Iterable,
    Iterator,
    Mapping,
    MutableMapping,
    Sequence,
    TypeAlias,
    TypeVar,
    overload,
)

_ClassTheme: TypeAlias = MutableMapping[str, MappingProxyType[str, Any]]
_ClassThemeDict: TypeAlias = MutableMapping[type, _ClassTheme]
_ClassDefaultTheme: TypeAlias = Sequence[str]
_ClassDefaultThemeDict: TypeAlias = MutableMapping[type, _ClassDefaultTheme]

_THEMES: _ClassThemeDict = dict()
_DEFAULT_THEME: _ClassDefaultThemeDict = dict()
_CLASSES_NOT_USING_PARENT_THEMES: set[type] = set()
_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES: set[type] = set()


class ThemeNamespace(ContextManager["ThemeNamespace"]):

    __THEMES_DEFAULT_DICT: ClassVar[_ClassThemeDict] = _THEMES
    __THEMES_DICT_NAMESPACE: ClassVar[dict[str, _ClassThemeDict]] = {}
    __DEFAULT_THEME_DEFAULT_DICT: ClassVar[_ClassDefaultThemeDict] = _DEFAULT_THEME
    __DEFAULT_THEME_DICT_NAMESPACE: ClassVar[dict[str, _ClassDefaultThemeDict]] = {}
    __actual_namespace: ClassVar[str | None] = None

    def __init__(self, namespace: str, *, extend: bool = False, include_none_namespace: bool = True) -> None:
        self.__namespace: str = str(namespace)
        self.__save_namespace: str | None = None
        self.__save_theme_dict: _ClassThemeDict
        self.__save_default_theme_dict: _ClassDefaultThemeDict
        self.__entered: int = 0
        self.__extend: bool = extend
        self.__include_none_namespace: bool = include_none_namespace

    def __enter__(self) -> ThemeNamespace:
        global _THEMES, _DEFAULT_THEME
        if self.__entered == 0:
            self.__save_namespace = ThemeNamespace.__actual_namespace
            self.__save_theme_dict = _THEMES
            self.__save_default_theme_dict = _DEFAULT_THEME
            ThemeNamespace.__actual_namespace = namespace = self.__namespace
            THEMES_DICT_NAMESPACE: dict[str, _ClassThemeDict] = ThemeNamespace.__THEMES_DICT_NAMESPACE
            DEFAULT_THEME_DICT_NAMESPACE: dict[str, _ClassDefaultThemeDict] = ThemeNamespace.__DEFAULT_THEME_DICT_NAMESPACE
            try:
                _THEMES = THEMES_DICT_NAMESPACE[namespace]
            except KeyError:
                THEMES_DICT_NAMESPACE[namespace] = _THEMES = dict()
            try:
                _DEFAULT_THEME = DEFAULT_THEME_DICT_NAMESPACE[namespace]
            except KeyError:
                DEFAULT_THEME_DICT_NAMESPACE[namespace] = _DEFAULT_THEME = dict()
            if self.__extend and (self.__include_none_namespace or self.__save_namespace is not None):
                _THEMES = self.__ExtendedThemeDict(_THEMES, self.__save_theme_dict)
                _DEFAULT_THEME = self.__ExtendedDefaultThemeDict(_DEFAULT_THEME, self.__save_default_theme_dict)
        self.__entered += 1
        return self

    def __exit__(self, *args: Any) -> None:
        global _THEMES, _DEFAULT_THEME
        if self.__entered <= 0:
            return
        self.__entered -= 1
        if self.__entered > 0:
            return
        namespace: str | None = self.__save_namespace
        self.__save_namespace = None
        _THEMES = self.__save_theme_dict
        _DEFAULT_THEME = self.__save_default_theme_dict
        del self.__save_theme_dict, self.__save_default_theme_dict
        ThemeNamespace.__actual_namespace = namespace

    @staticmethod
    def get_actual() -> str | None:
        return ThemeNamespace.__actual_namespace

    @staticmethod
    def get_theme_dict(namespace: str | None) -> MappingProxyType[type, _ClassTheme]:  # TODO: MappingProxyType on _ClassTheme
        if namespace is None:
            return MappingProxyType(ThemeNamespace.__THEMES_DEFAULT_DICT)
        return MappingProxyType(ThemeNamespace.__THEMES_DICT_NAMESPACE.get(namespace, {}))

    @staticmethod
    def get_default_theme_dict(namespace: str | None) -> MappingProxyType[type, Sequence[str]]:
        mapping: MutableMapping[type, Sequence[str]]
        if namespace is None:
            mapping = ThemeNamespace.__DEFAULT_THEME_DEFAULT_DICT
        else:
            mapping = ThemeNamespace.__DEFAULT_THEME_DICT_NAMESPACE.get(namespace, {})
        return MappingProxyType(mapping)

    @property
    def namespace(self) -> str:
        return self.__namespace

    class __ExtendedThemeDict(_ClassThemeDict):
        def __init__(self, actual: _ClassThemeDict, extension: _ClassThemeDict) -> None:
            super().__init__()
            self.__actual: _ClassThemeDict = actual
            self.__extension: _ClassThemeDict = extension

        def __key_list(self) -> FrozenSet[type]:
            return frozenset((*self.__actual, *self.__extension))

        def __contains__(self, __o: object) -> bool:
            return __o in self.__actual

        def __iter__(self) -> Iterator[type]:
            return iter(self.__key_list())

        def __len__(self) -> int:
            return len(self.__key_list())

        def __getitem__(self, __k: type) -> _ClassTheme:
            theme: _ClassTheme | None = self.__actual.get(__k)
            extension: _ClassTheme | None = self.__extension.get(__k)
            if theme is None and extension is None:
                raise KeyError(__k)
            return self.__ExtendedTheme(__k, self.__actual, theme, extension)

        def __setitem__(self, __k: type, __v: _ClassTheme) -> None:
            self.__actual[__k] = __v

        def __delitem__(self, __k: type) -> None:
            del self.__actual[__k]

        def popitem(self) -> tuple[type, _ClassTheme]:
            return self.__actual.popitem()

        __marker: Any = object()

        def pop(self, __key: type, __default: Any = __marker) -> Any:
            if __default is self.__marker:
                return self.__actual.pop(__key)
            return self.__actual.pop(__key, __default)

        class __ExtendedTheme(_ClassTheme):
            def __init__(
                self,
                cls: type,
                theme_dict: _ClassThemeDict,
                theme: _ClassTheme | None,
                extension: _ClassTheme | None,
            ) -> None:
                super().__init__()
                self.__cls: type = cls
                self.__theme_dict: _ClassThemeDict = theme_dict
                self.__actual: _ClassTheme | None = theme
                self.__extension: _ClassTheme | None = extension

            def __key_list(self) -> FrozenSet[str]:
                return frozenset((*(self.__actual or {}), *(self.__extension or {})))

            def __iter__(self) -> Iterator[str]:
                return iter(self.__key_list())

            def __len__(self) -> int:
                return len(self.__key_list())

            def __contains__(self, __o: object) -> bool:
                return __o in (self.__actual or {})

            def __getitem__(self, __k: str) -> MappingProxyType[str, Any]:
                theme: _ClassTheme | None = self.__actual
                extension: _ClassTheme | None = self.__extension
                if theme is None:
                    if extension is None:
                        raise KeyError(__k)
                    return extension[__k]
                elif extension is None:
                    return theme[__k]
                theme_options: MappingProxyType[str, Any] | None = theme.get(__k)
                extension_options: MappingProxyType[str, Any] | None = extension.get(__k)
                if theme_options is None:
                    if extension_options is None:
                        raise KeyError(__k)
                    return extension_options
                elif extension_options is None:
                    return theme_options
                return MappingProxyType(extension_options | theme_options)

            def __setitem__(self, __k: str, __v: MappingProxyType[str, Any]) -> None:
                theme: _ClassTheme | None = self.__actual
                if theme is None:
                    self.__theme_dict[self.__cls] = self.__actual = theme = {}
                theme[__k] = __v

            def __delitem__(self, __k: str) -> None:
                theme: _ClassTheme | None = self.__actual
                if theme is None:
                    raise KeyError(__k)
                del theme[__k]

            def popitem(self) -> tuple[str, MappingProxyType[str, Any]]:
                return (self.__actual or {}).popitem()

            __marker: Any = object()

            def pop(self, __key: str, __default: Any = __marker) -> Any:
                if __default is self.__marker:
                    return (self.__actual or {}).pop(__key)
                return (self.__actual or {}).pop(__key, __default)

    class __ExtendedDefaultThemeDict(_ClassDefaultThemeDict):
        def __init__(self, actual: _ClassDefaultThemeDict, extension: _ClassDefaultThemeDict) -> None:
            super().__init__()
            self.__actual: _ClassDefaultThemeDict = actual
            self.__extension: _ClassDefaultThemeDict = extension

        def __key_list(self) -> FrozenSet[type]:
            return frozenset((*self.__actual, *self.__extension))

        def __contains__(self, __o: object) -> bool:
            return __o in self.__actual

        def __iter__(self) -> Iterator[type]:
            return iter(self.__key_list())

        def __len__(self) -> int:
            return len(self.__key_list())

        def __getitem__(self, __k: type) -> _ClassDefaultTheme:
            default_themes: _ClassDefaultTheme | None = self.__actual.get(__k)
            extension: _ClassDefaultTheme | None = self.__extension.get(__k)
            if default_themes is None and extension is None:
                raise KeyError(__k)
            return (*(extension or ()), *(default_themes or ()))

        def __setitem__(self, __k: type, __v: _ClassDefaultTheme) -> None:
            self.__actual[__k] = __v

        def __delitem__(self, __k: type) -> None:
            del self.__actual[__k]

        def popitem(self) -> tuple[type, _ClassDefaultTheme]:
            return self.__actual.popitem()

        __marker: Any = object()

        def pop(self, __key: type, __default: Any = __marker) -> Any:
            if __default is self.__marker:
                return self.__actual.pop(__key)
            return self.__actual.pop(__key, __default)


_T = TypeVar("_T")


class _NoThemeType(str):
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

    def __new__(cls) -> _NoThemeType:
        global NoTheme
        try:
            return NoTheme
        except NameError:
            NoTheme = super().__new__(_NoThemeType, "NoTheme")
        return NoTheme


NoTheme: _NoThemeType = _NoThemeType()

ThemeType: TypeAlias = str | Iterable[str]


class ThemedObjectMeta(ABCMeta):
    __virtual_themed_class_bases__: tuple[ThemedObjectMeta, ...]
    __theme_ignore__: Sequence[str]
    __theme_associations__: dict[type, dict[str, str]]

    def __new__(
        metacls,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        use_parent_theme: bool = True,
        use_parent_default_theme: bool = True,
        **kwargs: Any,
    ) -> ThemedObjectMeta:
        def check_parameters(func: Callable[..., Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            if "theme" not in parameters:
                if not has_kwargs:
                    raise TypeError(f"{func.__qualname__}: Can't support 'theme' parameter")
            else:
                param: Parameter = parameters["theme"]
                if param.kind is not Parameter.KEYWORD_ONLY:
                    raise TypeError(f"{func.__qualname__}: 'theme' is a {param.kind.description} parameter")
                if param.default is not None:
                    raise TypeError(f"{func.__qualname__}: 'theme' parameter must have None as default value")

        if all(not getattr(attr, "__isabstractmethod__", False) for attr in namespace.values()):
            new_method: Callable[..., Any] | None = namespace.get("__new__")
            init_method: Callable[..., None] | None = namespace.get("__init__")
            if new_method is not None:
                check_parameters(new_method)
            if init_method is not None:
                check_parameters(init_method)

        ignored_parameters: str | Sequence[str] = namespace.pop("__theme_ignore__", ())
        if isinstance(ignored_parameters, str):
            ignored_parameters = (ignored_parameters,)
        namespace["__theme_ignore__"] = tuple(ignored_parameters)

        namespace.setdefault("__theme_associations__", {})

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if not use_parent_theme:
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            setattr(cls, "_no_parent_theme_", True)
            use_parent_default_theme = False
        if not use_parent_default_theme:
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
            setattr(cls, "_no_parent_default_theme_", True)
        setattr(cls, "_is_abstract_theme_class_", False)
        cls.__virtual_themed_class_bases__ = ()
        if all(not isinstance(b, ThemedObjectMeta) or b.is_abstract_theme_class() for b in bases):
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
        return cls

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        create_object: Callable[..., Any] = super().__call__
        if cls.is_abstract_theme_class():
            return create_object(*args, **kwargs)

        theme: ThemeType | None = kwargs.get("theme")
        if theme is NoTheme:
            return create_object(*args, **kwargs)
        if theme is None:
            theme = ()
        elif isinstance(theme, str):
            theme = (theme,)
        else:
            theme = tuple(theme)
            if not all(isinstance(t, str) for t in theme):
                raise TypeError("Themes must be str objects")
            if any(t is NoTheme for t in theme):
                raise ValueError("The 'NoTheme' special value is in the sequence")

        default_theme: tuple[str, ...] = cls.get_default_themes()
        theme_kwargs: dict[str, Any] = cls.get_theme_options(*default_theme, *theme, ignore_unusable=True)
        if theme_kwargs:
            kwargs = theme_kwargs | kwargs
        return create_object(*args, **kwargs)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError("can't set attribute")
        if name in ("__theme_ignore__", "__theme_associations__"):
            raise AttributeError("Read-only attribute")
        return super().__setattr__(name, value)

    @overload
    def set_theme(cls, name: str, options: dict[str, Any], update: bool = False, ignore_unusable: bool = False) -> None:
        ...

    @overload
    def set_theme(cls, name: str, options: None) -> None:
        ...

    def set_theme(cls, name: str, options: dict[str, Any] | None, update: bool = False, ignore_unusable: bool = False) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")
        if name is NoTheme:
            raise ValueError("Couldn't set 'NoTheme' as theme")

        if not options:
            if options is None or not update:
                _THEMES.pop(cls, None)
            return

        if "theme" in options:
            raise ValueError("'theme' parameter must not be given in options")

        ignored_parameters: Sequence[str] = cls.__theme_ignore__
        for opt in options:
            if opt in ignored_parameters:
                raise ValueError(f"{opt!r} is an ignored theme parameter")

        def check_options(func: Callable[..., Any], options: dict[str, Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            for option in filter(lambda option: option not in ignored_parameters, list(options)):
                if option not in parameters:
                    if not has_kwargs:
                        if not ignore_unusable:
                            raise TypeError(f"{func.__qualname__}: Unknown parameter {option!r}")
                        options.pop(option)
                    continue
                param: Parameter = parameters[option]
                if param.kind is not Parameter.KEYWORD_ONLY:
                    if not ignore_unusable:
                        raise TypeError(f"{func.__qualname__}: {option!r} is a {param.kind.description} parameter")
                    options.pop(option)
                elif param.default is Parameter.empty:
                    if not ignore_unusable:
                        raise TypeError(f"{func.__qualname__}: {option!r} is a required parameter")
                    options.pop(option)

        default_new_method: Callable[[type[object]], Any] = object.__new__
        default_init_method: Callable[[object], None] = object.__init__
        new_method: Callable[..., Any] = getattr(cls, "__new__", default_new_method)
        init_method: Callable[..., None] = getattr(cls, "__init__", default_init_method)

        if new_method is default_new_method and init_method is default_init_method:
            raise TypeError(f"{cls.__name__} does not override default object constructors")
        if new_method is not default_new_method:
            check_options(new_method, options)
        if init_method is not default_init_method:
            check_options(init_method, options)

        theme_dict: MutableMapping[str, MappingProxyType[str, Any]]

        if cls not in _THEMES:
            _THEMES[cls] = theme_dict = dict()
        else:
            theme_dict = _THEMES[cls]
        if name not in theme_dict or not update:
            theme_dict[name] = MappingProxyType(options.copy())
        else:
            theme_dict[name] = MappingProxyType(theme_dict[name] | options)

    @overload
    def set_default_theme(cls, name: str, /, *names: str, update: bool = False) -> None:
        ...

    @overload
    def set_default_theme(cls, name: None, /) -> None:
        ...

    def set_default_theme(cls, name: str | None, /, *names: str, update: bool = False) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")

        if name is None:
            if names:
                raise TypeError("Invalid arguments")
            _DEFAULT_THEME.pop(cls, None)
            return
        default_themes: dict[str, None] = dict.fromkeys([name, *names])
        if any(theme is NoTheme for theme in default_themes):
            raise ValueError("Couldn't set 'NoTheme' as default theme")
        if cls not in _DEFAULT_THEME or not update:
            _DEFAULT_THEME[cls] = tuple(default_themes)
        else:
            _DEFAULT_THEME[cls] = tuple(dict.fromkeys((*_DEFAULT_THEME[cls], *default_themes)))

    def get_theme_options(cls, *themes: str, parent_themes: bool = True, ignore_unusable: bool = False) -> dict[str, Any]:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes does not have themes.")

        theme_kwargs: dict[str, Any] = dict()
        if not themes:
            return theme_kwargs

        all_parents_classes = (
            tuple(ThemedObjectMeta.__get_all_parent_classes(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_THEMES))
            if parent_themes
            else ()
        )
        theme_key_associations = cls.__theme_associations__
        for t in dict.fromkeys(themes):
            for parent in all_parents_classes:
                parent_theme_kwargs = parent.get_theme_options(t)
                for parent_param, cls_param in theme_key_associations.get(parent, {}).items():
                    if parent_param not in parent_theme_kwargs:
                        continue
                    parent_theme_kwargs[cls_param] = parent_theme_kwargs.pop(parent_param)
                theme_kwargs |= parent_theme_kwargs
            with suppress(KeyError):
                theme_kwargs |= _THEMES[cls][t]

        if not all_parents_classes or not theme_kwargs or not ignore_unusable:
            return theme_kwargs

        def check_options(func: Callable[..., Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            for option in tuple(theme_kwargs):
                if option not in parameters:
                    if not has_kwargs:
                        theme_kwargs.pop(option)
                    continue
                param: Parameter = parameters[option]
                if param.kind is not Parameter.KEYWORD_ONLY or param.default is Parameter.empty:
                    theme_kwargs.pop(option)

        default_new_method: Callable[[type[object]], Any] = object.__new__
        default_init_method: Callable[[object], None] = object.__init__
        new_method: Callable[..., Any] = getattr(cls, "__new__", default_new_method)
        init_method: Callable[..., None] = getattr(cls, "__init__", default_init_method)

        if new_method is default_new_method and init_method is default_init_method:
            theme_kwargs.clear()
        else:
            if new_method is not default_new_method:
                check_options(new_method)
            if init_method is not default_init_method:
                check_options(init_method)

        return theme_kwargs

    def get_default_themes(cls, *, parent_default_themes: bool = True) -> tuple[str, ...]:
        default_theme: dict[str, None] = dict()

        def add_default_themes(cls: ThemedObjectMeta) -> None:
            nonlocal default_theme
            with suppress(KeyError):
                default_theme |= dict.fromkeys(_DEFAULT_THEME[cls])

        if parent_default_themes:
            get_all_parents_class = ThemedObjectMeta.__get_all_parent_classes
            for parent in get_all_parents_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
                add_default_themes(parent)
        add_default_themes(cls)

        return tuple(default_theme)

    def is_abstract_theme_class(cls) -> bool:
        return truth(getattr(cls, "_is_abstract_theme_class_", False))

    def register(cls, subclass: type[_T]) -> type[_T]:
        def register_themed_subclass(subclass: ThemedObjectMeta) -> None:
            if not subclass.is_abstract_theme_class():
                cls.register_themed_subclass(subclass)

        super().register(subclass)
        if isinstance(subclass, ThemedObjectMeta):
            register_themed_subclass(subclass)  # type: ignore[unreachable]
        return subclass

    def register_themed_subclass(cls, subclass: _T) -> _T:
        themed_subclass: Any = subclass
        if not isinstance(themed_subclass, ThemedObjectMeta):
            raise TypeError("Not a themed object")
        if themed_subclass.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot have themes.")
        themed_subclass.__virtual_themed_class_bases__ = (*themed_subclass.__virtual_themed_class_bases__, cls)
        if not getattr(themed_subclass, "_no_parent_theme_", False):
            try:
                _CLASSES_NOT_USING_PARENT_THEMES.remove(themed_subclass)
            except (ValueError, KeyError):
                pass
        if not getattr(themed_subclass, "_no_parent_default_theme_", False):
            try:
                _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.remove(themed_subclass)
            except (ValueError, KeyError):
                pass
        return subclass

    @staticmethod
    def __get_all_parent_classes(cls: ThemedObjectMeta, *, do_not_search_for: set[type]) -> Sequence[ThemedObjectMeta]:
        def get_all_parent_classes(cls: ThemedObjectMeta) -> Iterator[ThemedObjectMeta]:
            if not isinstance(cls, ThemedObjectMeta) or cls in do_not_search_for or cls.is_abstract_theme_class():
                return
            mro: list[type]
            try:
                mro = list(getattr(cls, "__mro__"))[1:]
            except AttributeError:
                mro = list(cls.__bases__)
            mro.extend(cls.__virtual_themed_class_bases__)

            for base in mro:
                if not isinstance(base, ThemedObjectMeta) or base.is_abstract_theme_class():
                    continue
                yield base
                yield from get_all_parent_classes(base)

        return tuple(reversed(dict.fromkeys(get_all_parent_classes(cls))))


_ThemedObjectClass = TypeVar("_ThemedObjectClass")


def abstract_theme_class(cls: _ThemedObjectClass) -> _ThemedObjectClass:
    setattr(cls, "_is_abstract_theme_class_", True)
    return cls


@abstract_theme_class
class ThemedObject(metaclass=ThemedObjectMeta):
    pass


del _T, _ThemedObjectClass
