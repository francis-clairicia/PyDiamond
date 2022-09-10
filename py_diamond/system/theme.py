# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Themed objects module"""

from __future__ import annotations

__all__ = [
    "ClassWithThemeNamespace",
    "ClassWithThemeNamespaceMeta",
    "NoTheme",
    "ThemeNamespace",
    "ThemeType",
    "ThemedObject",
    "ThemedObjectMeta",
    "abstract_theme_class",
    "closed_namespace",
    "force_apply_theme_decorator",
    "no_theme_decorator",
    "set_default_theme_namespace",
]

from abc import abstractmethod
from collections import OrderedDict, defaultdict, deque
from contextlib import suppress
from functools import cached_property
from inspect import Parameter, Signature
from itertools import chain
from re import compile as re_compile
from threading import RLock
from types import FunctionType, LambdaType, MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Final,
    Iterable,
    Iterator,
    Mapping,
    Match,
    MutableMapping,
    NamedTuple,
    Pattern,
    Sequence,
    TypeAlias,
    TypeVar,
    final,
    overload,
)

from .object import Object, ObjectMeta, mro
from .utils._mangling import getattr_pv
from .utils.abc import concreteclassmethod, isabstractclass, isabstractmethod
from .utils.functools import cache, wraps

_ClassTheme: TypeAlias = MutableMapping[str, MappingProxyType[str, Any]]
_ClassThemeProxy: TypeAlias = MappingProxyType[str, MappingProxyType[str, Any]]
_ClassThemeDict: TypeAlias = MutableMapping[type, _ClassTheme]
_ClassThemeDictProxy: TypeAlias = MappingProxyType[type, _ClassThemeProxy]
_ClassDefaultTheme: TypeAlias = Sequence[str]
_ClassDefaultThemeDict: TypeAlias = MutableMapping[type, _ClassDefaultTheme]
_ClassDefaultThemeDictProxy: TypeAlias = MappingProxyType[type, _ClassDefaultTheme]


class _ThemeNamespaceBackupItem(NamedTuple):
    name: str | None
    theme_dict: _ClassThemeDict
    default_theme_dict: _ClassDefaultThemeDict


@final
class ThemeNamespace(ContextManager["ThemeNamespace"], Object):

    __THEMES: _ClassThemeDict = dict()
    __DEFAULT_THEME: _ClassDefaultThemeDict = dict()
    __THEMES_DEFAULT_DICT: Final[_ClassThemeDict] = __THEMES
    __THEMES_DICT_NAMESPACE: Final[defaultdict[str, _ClassThemeDict]] = defaultdict(dict)
    __DEFAULT_THEME_DEFAULT_DICT: Final[_ClassDefaultThemeDict] = __DEFAULT_THEME
    __DEFAULT_THEME_DICT_NAMESPACE: Final[defaultdict[str, _ClassDefaultThemeDict]] = defaultdict(dict)
    __actual_namespace: ClassVar[str | None] = None

    def __init__(self, namespace: str, *, extend: bool = False, include_none_namespace: bool = True) -> None:
        if not namespace:
            raise ValueError("Empty namespace name")
        self.__namespace: str = str(namespace)
        self.__save_namespaces: deque[_ThemeNamespaceBackupItem] = deque()
        self.__extend: bool = bool(extend)
        self.__include_none_namespace: bool = bool(include_none_namespace)

    def __enter__(self) -> ThemeNamespace:
        with ThemeNamespace.get_lock():
            save_namespace = _ThemeNamespaceBackupItem(
                name=ThemeNamespace.__actual_namespace,
                theme_dict=ThemeNamespace.__THEMES,
                default_theme_dict=ThemeNamespace.__DEFAULT_THEME,
            )
            self.__save_namespaces.append(save_namespace)
            ThemeNamespace.__actual_namespace = namespace = self.__namespace
            ThemeNamespace.__THEMES = ThemeNamespace.__THEMES_DICT_NAMESPACE[namespace]
            ThemeNamespace.__DEFAULT_THEME = ThemeNamespace.__DEFAULT_THEME_DICT_NAMESPACE[namespace]
            if self.__extend and (self.__include_none_namespace or save_namespace.name is not None):
                ThemeNamespace.__THEMES = self.__extend_theme_dict(
                    ThemeNamespace.__THEMES,
                    save_namespace.theme_dict,
                )
                ThemeNamespace.__DEFAULT_THEME = self.__extend_default_theme_dict(
                    ThemeNamespace.__DEFAULT_THEME,
                    save_namespace.default_theme_dict,
                )
        return self

    def __exit__(self, *args: Any) -> None:
        with ThemeNamespace.get_lock():
            try:
                save_namespace: _ThemeNamespaceBackupItem = self.__save_namespaces.pop()
            except IndexError:
                return
            ThemeNamespace.__THEMES = save_namespace.theme_dict
            ThemeNamespace.__DEFAULT_THEME = save_namespace.default_theme_dict
            ThemeNamespace.__actual_namespace = save_namespace.name

    @staticmethod
    def get_actual_namespace_name() -> str | None:
        return ThemeNamespace.__actual_namespace

    @staticmethod
    def get_theme_dict(namespace: str | None) -> _ClassThemeDictProxy:
        theme_dict: _ClassThemeDict
        if namespace is None:
            theme_dict = ThemeNamespace.__THEMES_DEFAULT_DICT
        else:
            theme_dict = ThemeNamespace.__THEMES_DICT_NAMESPACE[namespace]
        with ThemeNamespace.get_lock():
            return MappingProxyType({cls: MappingProxyType(theme) for cls, theme in theme_dict.items()})

    @staticmethod
    def get_default_theme_dict(namespace: str | None) -> _ClassDefaultThemeDictProxy:
        mapping: _ClassDefaultThemeDict
        if namespace is None:
            mapping = ThemeNamespace.__DEFAULT_THEME_DEFAULT_DICT
        else:
            mapping = ThemeNamespace.__DEFAULT_THEME_DICT_NAMESPACE[namespace]
        return MappingProxyType(mapping)

    @property
    def name(self) -> str:
        return self.__namespace

    @staticmethod
    @cache
    def get_lock() -> RLock:
        return RLock()

    @staticmethod
    def __extend_theme_dict(
        actual: _ClassThemeDict,
        extension: _ClassThemeDict,
    ) -> __ExtendedThemeDict:
        return ThemeNamespace.__ExtendedThemeDict(actual, extension)

    @staticmethod
    def __extend_default_theme_dict(
        actual: _ClassDefaultThemeDict,
        extension: _ClassDefaultThemeDict,
    ) -> __ExtendedDefaultThemeDict:
        return ThemeNamespace.__ExtendedDefaultThemeDict(actual, extension)

    class __ExtendedThemeDict(_ClassThemeDict):
        def __init__(self, actual: _ClassThemeDict, extension: _ClassThemeDict) -> None:
            super().__init__()
            self.__actual: _ClassThemeDict = actual
            self.__extension: _ClassThemeDict = extension

        def __repr__(self) -> str:
            return f"{self.__class__.__name__.strip('_')}(actual={self.__actual!r}, extension={self.__extension!r})"

        def __key_list(self) -> frozenset[type]:
            return frozenset(chain(self.__actual, self.__extension))

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

            def __repr__(self) -> str:
                return f"{self.__class__.__name__.strip('_')}(actual={self.__actual!r}, extension={self.__extension!r})"

            def __key_list(self) -> frozenset[str]:
                return frozenset(chain(self.__actual or {}, self.__extension or {}))

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

        def __repr__(self) -> str:
            return f"{self.__class__.__name__.strip('_')}(actual={self.__actual!r}, extension={self.__extension!r})"

        def __key_list(self) -> frozenset[type]:
            return frozenset(chain(self.__actual, self.__extension))

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
_ThemedObjectClass = TypeVar("_ThemedObjectClass", bound="ThemedObjectMeta")


class _NoThemeType(str):
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

    def __new__(cls) -> _NoThemeType:
        global NoTheme
        try:
            return NoTheme
        except NameError:
            NoTheme = super().__new__(_NoThemeType, "NoTheme")  # type: ignore[misc]
        return NoTheme


NoTheme: Final[_NoThemeType] = _NoThemeType()

ThemeType: TypeAlias = str | Iterable[str] | _NoThemeType


class _AbstractThemedObjectResolver(Object):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="_AbstractThemedObjectResolver")

    def __init__(self, max_size: int = 128) -> None:
        self.__lru_cache: defaultdict[ThemedObjectMeta, OrderedDict[tuple[type, ...], tuple[ThemedObjectMeta, ...]]]
        self.__lru_cache = defaultdict(OrderedDict)
        self.__max_size: int = max_size
        self.__lock: defaultdict[ThemedObjectMeta, RLock] = defaultdict(RLock)

    @overload
    def __get__(self: __Self, obj: None, objtype: type, /) -> __Self:
        ...

    @overload
    def __get__(self, obj: ThemedObjectMeta, objtype: type | None = None, /) -> tuple[ThemedObjectMeta, ...]:
        ...

    def __get__(self: __Self, obj: ThemedObjectMeta | None, objtype: type | None = None) -> __Self | tuple[ThemedObjectMeta, ...]:
        if obj is None:
            if objtype is None:
                raise TypeError("__get__(None, None) is forbidden")
            return self

        cache_key = tuple(sorted(obj.__virtual_themed_class_bases__, key=lambda cls: cls.__qualname__))

        with self.__lock[obj]:
            lru_cache: OrderedDict[tuple[type, ...], tuple[ThemedObjectMeta, ...]] = self.__lru_cache[obj]
            mro: tuple[ThemedObjectMeta, ...] | None = lru_cache.get(cache_key, None)
            if mro is not None:
                lru_cache.move_to_end(cache_key)
            else:
                lru_cache[cache_key] = mro = self.resolve(obj)
                if len(lru_cache) > self.__max_size:
                    lru_cache.popitem(last=False)
            return mro

    @abstractmethod
    def resolve(self, cls: ThemedObjectMeta) -> tuple[ThemedObjectMeta, ...]:
        raise NotImplementedError


@final
class _ThemedObjectMROResolver(_AbstractThemedObjectResolver):
    __name: str | None = None

    def __set_name__(self, owner: type, name: str, /) -> None:
        self.__name = name

    def resolve(self, cls: ThemedObjectMeta) -> tuple[ThemedObjectMeta, ...]:
        name: str | None = self.__name
        if name is None:
            raise TypeError("__set_name__() was not called")
        return (cls,) + mro(*cls.__themed_class_bases__, attr=name)


@final
class _ThemedObjectBasesResolver(_AbstractThemedObjectResolver):
    def resolve(self, cls: ThemedObjectMeta) -> tuple[ThemedObjectMeta, ...]:
        return tuple(c for c in cls.__bases__ if isinstance(c, ThemedObjectMeta)) + cls.__virtual_themed_class_bases__


class ThemedObjectMeta(ObjectMeta):
    __virtual_themed_class_bases__: tuple[ThemedObjectMeta, ...]
    __theme_ignore__: Sequence[str]
    __theme_associations__: Mapping[ThemedObjectMeta, dict[str, str]]
    __theme_override__: Sequence[str]

    __themed_class_bases__: Final[_ThemedObjectBasesResolver] = _ThemedObjectBasesResolver()
    __themed_class_mro__: Final[_ThemedObjectMROResolver] = _ThemedObjectMROResolver()

    __CLASSES_NOT_USING_PARENT_THEMES: Final[set[type]] = set()
    __CLASSES_NOT_USING_PARENT_DEFAULT_THEMES: Final[set[type]] = set()

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        *,
        no_theme: bool = False,
        use_parent_theme: bool = True,
        use_parent_default_theme: bool = True,
        **kwargs: Any,
    ) -> ThemedObjectMeta:
        if any(isinstance(cls, ThemedObjectMeta) and getattr(cls, "_no_use_of_themes_", False) for cls in bases):
            no_theme = True

        if no_theme:
            use_parent_theme = use_parent_default_theme = False

        def check_parameters(func: Callable[..., Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters

            if "theme" not in parameters:
                if not no_theme:
                    raise TypeError(f"{func.__qualname__}: Can't support 'theme' parameter")
            else:
                param: Parameter = parameters["theme"]
                if param.kind is not Parameter.KEYWORD_ONLY:
                    raise TypeError(f"{func.__qualname__}: 'theme' is a {param.kind.description} parameter")
                if param.default is not None:
                    raise TypeError(f"{func.__qualname__}: 'theme' parameter must have None as default value")

        if all(not isabstractmethod(attr) for attr in namespace.values()):
            init_method: Callable[..., None] | None = namespace.get("__init__")
            if init_method is not None:
                check_parameters(init_method)

        for attr_name in ("__theme_ignore__", "__theme_override__"):
            sequence: str | Sequence[str] = namespace.pop(attr_name, ())
            if isinstance(sequence, str):
                sequence = (sequence,)
            else:
                sequence = tuple(set(sequence))
            namespace[attr_name] = sequence

        namespace["__theme_associations__"] = MappingProxyType(dict(namespace.get("__theme_associations__", {})))
        namespace["_no_use_of_themes_"] = bool(no_theme)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        setattr(cls, "_is_abstract_theme_class_", isabstractclass(cls))
        if not use_parent_theme:
            mcs.__CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            use_parent_default_theme = False
        setattr(cls, "_no_parent_theme_", bool(use_parent_theme))
        if not use_parent_default_theme:
            mcs.__CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
        setattr(cls, "_no_parent_default_theme_", bool(use_parent_default_theme))
        super().__setattr__(cls, "__virtual_themed_class_bases__", ())
        return cls

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        create_object: Callable[..., Any] = super().__call__
        if cls.is_abstract_theme_class() or getattr(cls, "_no_use_of_themes_", False):
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
            assert all(isinstance(t, str) for t in theme), "Themes must be str objects"
            assert not any(t is NoTheme for t in theme), "The 'NoTheme' special value is in the sequence"

        theme_kwargs: dict[str, Any] = cls.get_theme_options(
            *theme, parent_themes=True, use_default_themes=True, use_parent_default_themes=True, ignore_unusable=True
        )
        if theme_kwargs:
            kwargs = theme_kwargs | kwargs
        return create_object(*args, **kwargs)

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError("can't set attribute")
        if name in (
            "__virtual_themed_class_bases__",
            "__theme_ignore__",
            "__theme_associations__",
            "__theme_override__",
        ):
            raise AttributeError("Read-only attribute")
        return super().__setattr__(name, value)

    def __delattr__(self, name: str, /) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError("can't delete attribute")
        if name in (
            "__virtual_themed_class_bases__",
            "__theme_ignore__",
            "__theme_associations__",
            "__theme_override__",
        ):
            raise AttributeError("Read-only attribute")
        return super().__delattr__(name)

    @overload
    def set_theme(cls, name: str, options: dict[str, Any], *, update: bool = False, ignore_unusable: bool = False) -> None:
        ...

    @overload
    def set_theme(cls, name: str, options: None) -> None:
        ...

    def set_theme(cls, name: str, options: dict[str, Any] | None, *, update: bool = False, ignore_unusable: bool = False) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")
        if getattr(cls, "_no_use_of_themes_", False):
            raise TypeError(f"{cls.__qualname__} do not use themes")
        if name is NoTheme:
            raise ValueError("Couldn't set 'NoTheme' as theme")

        _THEMES: _ClassThemeDict = getattr_pv(ThemeNamespace, "THEMES")
        if not options:
            if options is None or not update:
                with ThemeNamespace.get_lock():
                    _THEMES.pop(cls, None)
            return

        if "theme" in options:
            raise ValueError("'theme' parameter must not be given in options")

        ignored_parameters: Sequence[str] = cls.__theme_ignore__
        for opt in options:
            if opt in ignored_parameters:
                raise ValueError(f"{opt!r} is an ignored theme parameter")

        default_init_method: Callable[[object], None] = object.__init__
        init_method: Callable[..., None] = getattr(cls, "__init__", default_init_method)

        if init_method is default_init_method:
            raise TypeError(f"{cls.__name__} does not override default object constructors")
        sig: Signature = Signature.from_callable(init_method, follow_wrapped=True)
        parameters: Mapping[str, Parameter] = sig.parameters

        for option in list(options):
            if option not in parameters:
                if not ignore_unusable:
                    raise TypeError(f"{init_method.__qualname__}: Unknown parameter {option!r}")
                options.pop(option)
                continue
            param: Parameter = parameters[option]
            if param.kind is not Parameter.KEYWORD_ONLY:
                if not ignore_unusable:
                    raise TypeError(f"{init_method.__qualname__}: {option!r} is a {param.kind.description} parameter")
                options.pop(option)
            elif param.default is Parameter.empty:
                if not ignore_unusable:
                    raise TypeError(f"{init_method.__qualname__}: {option!r} is a required parameter")
                options.pop(option)

        theme_dict: _ClassTheme

        with ThemeNamespace.get_lock():
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
        if getattr(cls, "_no_use_of_themes_", False):
            raise TypeError(f"{cls.__qualname__} do not use themes")

        _DEFAULT_THEME: _ClassDefaultThemeDict = getattr_pv(ThemeNamespace, "DEFAULT_THEME")
        if name is None:
            if names:
                raise TypeError("Invalid arguments")
            with ThemeNamespace.get_lock():
                _DEFAULT_THEME.pop(cls, None)
            return
        default_themes: dict[str, None] = dict.fromkeys([name, *names])
        if any(theme is NoTheme for theme in default_themes):
            raise ValueError("Couldn't set 'NoTheme' as default theme")
        with ThemeNamespace.get_lock():
            if cls not in _DEFAULT_THEME or not update:
                _DEFAULT_THEME[cls] = tuple(default_themes)
            else:
                _DEFAULT_THEME[cls] = tuple(dict.fromkeys((*_DEFAULT_THEME[cls], *default_themes)))

    def get_theme_options(
        cls,
        *themes: str,
        parent_themes: bool = True,
        use_default_themes: bool = True,
        use_parent_default_themes: bool = True,
        ignore_unusable: bool = False,
    ) -> dict[str, Any]:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes does not have themes.")
        if getattr(cls, "_no_use_of_themes_", False):
            raise TypeError(f"{cls.__qualname__} do not use themes")

        if use_default_themes:
            themes = cls.get_default_themes(parent_default_themes=use_parent_default_themes) + themes

        theme_kwargs: dict[str, Any] = dict()
        if not themes:
            return theme_kwargs

        _THEMES: _ClassThemeDict = getattr_pv(ThemeNamespace, "THEMES")
        all_parents_classes = (
            ThemedObjectMeta.__get_all_parent_classes(cls, do_not_search_for=cls.__CLASSES_NOT_USING_PARENT_THEMES)
            if parent_themes
            else ()
        )
        theme_key_associations = cls.__theme_associations__
        theme_key_override = cls.__theme_override__
        for t in dict.fromkeys(themes):
            for parent in all_parents_classes:
                parent_theme_kwargs = parent.get_theme_options(
                    t, parent_themes=False, use_default_themes=False, ignore_unusable=False
                )
                for parent_param, cls_param in theme_key_associations.get(parent, {}).items():
                    if parent_param in theme_kwargs:
                        theme_kwargs[cls_param] = theme_kwargs.pop(parent_param)
                    if parent_param in parent_theme_kwargs:
                        parent_theme_kwargs[cls_param] = parent_theme_kwargs.pop(parent_param)
                for opt in theme_key_override:
                    parent_theme_kwargs.pop(opt, None)
                theme_kwargs |= parent_theme_kwargs
            with suppress(KeyError):
                theme_kwargs |= _THEMES[cls][t]

        if not theme_kwargs or not ignore_unusable:
            return theme_kwargs

        default_init_method: Callable[[object], None] = object.__init__
        init_method: Callable[..., None] = getattr(cls, "__init__", default_init_method)

        if init_method is default_init_method:
            theme_kwargs.clear()
        else:
            sig: Signature = Signature.from_callable(init_method, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters

            for option in tuple(theme_kwargs):
                if option not in parameters:
                    theme_kwargs.pop(option)
                    continue
                param: Parameter = parameters[option]
                if param.kind is not Parameter.KEYWORD_ONLY or param.default is Parameter.empty:
                    theme_kwargs.pop(option)

        return theme_kwargs

    def get_default_themes(cls, *, parent_default_themes: bool = True) -> tuple[str, ...]:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes does not have themes.")
        if getattr(cls, "_no_use_of_themes_", False):
            raise TypeError(f"{cls.__qualname__} do not use themes")

        default_theme: dict[str, None] = dict()

        _DEFAULT_THEME: _ClassDefaultThemeDict = getattr_pv(ThemeNamespace, "DEFAULT_THEME")
        if parent_default_themes:
            get_all_parents_class = ThemedObjectMeta.__get_all_parent_classes
            for parent in get_all_parents_class(cls, do_not_search_for=cls.__CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
                default_theme |= dict.fromkeys(parent.get_default_themes(parent_default_themes=False))
        with suppress(KeyError):
            default_theme |= dict.fromkeys(_DEFAULT_THEME[cls])

        return tuple(default_theme)

    def is_abstract_theme_class(cls) -> bool:
        return bool(vars(cls).get("_is_abstract_theme_class_", False) or isabstractclass(cls))

    def register(cls, subclass: type[_T]) -> type[_T]:
        def register_themed_subclass(subclass: ThemedObjectMeta) -> None:
            if not subclass.is_abstract_theme_class():
                cls.register_themed_subclass(subclass)

        super().register(subclass)
        if isinstance(subclass, ThemedObjectMeta):
            register_themed_subclass(subclass)  # type: ignore[unreachable]
        return subclass

    def register_themed_subclass(cls, subclass: _ThemedObjectClass) -> _ThemedObjectClass:
        if not isinstance(subclass, ThemedObjectMeta):
            raise TypeError("Not a themed object")
        if subclass.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot have themes.")
        if cls in subclass.__themed_class_mro__:
            raise TypeError("Already a themed subclass")
        virtual_themed_class_bases = (*subclass.__virtual_themed_class_bases__, cls)
        super(ThemedObjectMeta, subclass).__setattr__("__virtual_themed_class_bases__", virtual_themed_class_bases)
        subclass.__class__.__themed_class_mro__.__get__(subclass)  # Compute it now to check if add it will work
        if not getattr(subclass, "_no_parent_theme_", False):
            cls.__CLASSES_NOT_USING_PARENT_THEMES.discard(subclass)
        if not getattr(subclass, "_no_parent_default_theme_", False):
            cls.__CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.discard(subclass)
        return subclass

    @staticmethod
    def __get_all_parent_classes(cls: ThemedObjectMeta, *, do_not_search_for: set[type]) -> Sequence[ThemedObjectMeta]:
        if cls in do_not_search_for:
            return ()

        valid_parent_classes = set(ThemedObjectMeta.__travel_parent_classes(cls, do_not_search_for=do_not_search_for))
        return tuple(filter(valid_parent_classes.__contains__, reversed(cls.__themed_class_mro__)))

    @staticmethod
    def __travel_parent_classes(cls: ThemedObjectMeta, *, do_not_search_for: set[type]) -> Iterator[ThemedObjectMeta]:
        for base in filter(lambda b: not b.is_abstract_theme_class(), cls.__themed_class_bases__):
            yield base
            if base not in do_not_search_for:
                yield from ThemedObjectMeta.__travel_parent_classes(base, do_not_search_for=do_not_search_for)


def abstract_theme_class(cls: _ThemedObjectClass) -> _ThemedObjectClass:
    setattr(cls, "_is_abstract_theme_class_", True)
    return cls


@abstract_theme_class
class ThemedObject(Object, metaclass=ThemedObjectMeta):
    pass


class ClassWithThemeNamespaceMeta(ObjectMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="ClassWithThemeNamespaceMeta")

    __namespaces: Final[dict[type, ThemeNamespace]] = dict()

    __unique_theme_namespace_cache: Final[dict[str, ThemeNamespace]] = dict()

    _theme_decorator_exempt_: frozenset[str]

    def __new__(
        mcs: type[__Self],
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> __Self:
        theme_decorator_exempt_regex: frozenset[Pattern[str]] = mcs.get_default_theme_decorator_exempt_regex()

        if "_theme_decorator_exempt_" in namespace:
            raise TypeError("_theme_decorator_exempt_ must not be set")

        cls_theme_decorator_exempt: set[str] = set(mcs.get_default_theme_decorator_exempt())
        if "__theme_init__" in cls_theme_decorator_exempt:
            raise TypeError("'__theme_init__' must not be in decorator exempt")
        for base in filter(lambda base: isinstance(base, ClassWithThemeNamespaceMeta), bases):
            cls_theme_decorator_exempt.update(getattr(base, "_theme_decorator_exempt_", ()))

        for attr_name, attr_obj in namespace.items():
            no_theme_decorator: str | None = getattr(attr_obj, "__no_theme_decorator__", None)
            force_apply_theme_decorator: bool = getattr(attr_obj, "__force_apply_theme_decorator__", False)
            if attr_name == "__theme_init__":
                if not isinstance(attr_obj, classmethod):
                    raise TypeError("'__theme_init__' must be a classmethod")
                if no_theme_decorator in ("once", "permanent") or hasattr(attr_obj, "__force_apply_theme_decorator__"):
                    raise TypeError("'__theme_init__' must not be decorated")
                namespace[attr_name] = type(attr_obj)(mcs.__theme_initializer_decorator(attr_obj.__func__))
                continue
            if no_theme_decorator in ("once", "permanent"):
                if no_theme_decorator == "once":
                    if force_apply_theme_decorator:
                        raise ValueError("Invalid decorator usage")
                    continue
                cls_theme_decorator_exempt.add(attr_name)
            for pattern in theme_decorator_exempt_regex:
                match = pattern.match(attr_name)
                if match is not None and mcs.validate_theme_decorator_exempt_from_regex(match, attr_obj):
                    cls_theme_decorator_exempt.add(attr_name)
            if not force_apply_theme_decorator:
                if attr_name in cls_theme_decorator_exempt:
                    continue
                if isinstance(attr_obj, (property, cached_property)):
                    continue
            namespace[attr_name] = mcs.__apply_theme_namespace_decorator(attr_obj)
        namespace["_theme_decorator_exempt_"] = frozenset(cls_theme_decorator_exempt)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name == "_theme_decorator_exempt_":
            raise AttributeError(f"{name} cannot be overriden")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name == "_theme_decorator_exempt_":
            raise AttributeError(f"{name} cannot be deleted")
        return super().__delattr__(name)

    @final
    @concreteclassmethod
    def get_theme_namespace(cls) -> str | None:
        namespace = ClassWithThemeNamespaceMeta.__namespaces.get(cls)
        return namespace.name if namespace else None

    @final
    @concreteclassmethod
    def set_theme_namespace(cls, namespace: str, *, allow_extension: bool = False, include_none_namespace: bool = False) -> None:
        if namespace == _mangle_closed_namespace_name(cls) and allow_extension:
            raise ValueError("Closed namespace setting must not allow theme extension")
        ClassWithThemeNamespaceMeta.__namespaces[cls] = ThemeNamespace(
            namespace=str(namespace),
            extend=bool(allow_extension),
            include_none_namespace=bool(include_none_namespace),
        )

    @final
    @concreteclassmethod
    def set_closed_theme_namespace(cls) -> None:
        return cls.set_theme_namespace(_mangle_closed_namespace_name(cls), allow_extension=False, include_none_namespace=False)

    @final
    @concreteclassmethod
    def remove_theme_namespace(cls) -> None:
        ClassWithThemeNamespaceMeta.__namespaces.pop(cls, None)

    @final
    @concreteclassmethod
    def theme_initialize(cls) -> None:
        theme_initialize: Callable[[], None] = getattr(cls, "__theme_init__")
        theme_initialize()

    @classmethod
    @cache
    def get_default_theme_decorator_exempt(mcs) -> frozenset[str]:
        return frozenset(
            {
                *(name for name, obj in vars(object).items() if callable(obj) or isinstance(obj, classmethod)),
                "__del__",
                "__getattr__",
            }
        )

    @classmethod
    @cache
    def get_default_theme_decorator_exempt_regex(mcs) -> frozenset[Pattern[str]]:
        return frozenset(
            {
                re_compile(r"^__\w+__$"),
            }
        )

    @classmethod
    def validate_theme_decorator_exempt_from_regex(mcs, match: Match[str], attr_obj: Any) -> bool:
        return callable(attr_obj) or isinstance(
            attr_obj,
            (
                property,
                cached_property,
                classmethod,
            ),
        )

    @staticmethod
    def __theme_namespace_decorator(func: Callable[..., Any], /, use_cls: bool = False) -> Callable[..., Any]:
        get_cls: Callable[[Any], type] = (lambda o: o) if use_cls else type

        all_theme_namespaces: dict[type, ThemeNamespace] = ClassWithThemeNamespaceMeta.__namespaces
        unique_theme_namespace_cache: dict[str, ThemeNamespace]

        unique_theme_namespace_cache = ClassWithThemeNamespaceMeta.__unique_theme_namespace_cache

        def get_unique_theme_namespace(cls: type) -> ThemeNamespace:
            namespace = _mangle_closed_namespace_name(cls)
            try:
                return unique_theme_namespace_cache[namespace]
            except KeyError:
                theme_namespace = ThemeNamespace(
                    namespace=namespace,
                    extend=True,
                    include_none_namespace=True,
                )
                unique_theme_namespace_cache[namespace] = theme_namespace
                return theme_namespace

        @wraps(func)
        def wrapper(__cls_or_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            cls: type = get_cls(__cls_or_self)
            with all_theme_namespaces.get(cls) or get_unique_theme_namespace(cls):
                return func(__cls_or_self, *args, **kwargs)

        return wrapper

    @staticmethod
    def __apply_theme_namespace_decorator(obj: Any) -> Any:
        if isabstractmethod(obj):
            return obj

        theme_namespace_decorator = ClassWithThemeNamespaceMeta.__theme_namespace_decorator
        match obj:
            case property(fget=fget, fset=fset, fdel=fdel):
                if callable(fget):
                    obj = obj.getter(theme_namespace_decorator(fget))
                if callable(fset):
                    obj = obj.setter(theme_namespace_decorator(fset))
                if callable(fdel):
                    obj = obj.deleter(theme_namespace_decorator(fdel))
            case cached_property(func=func):
                setattr(obj, "func", theme_namespace_decorator(func))
            case classmethod(__func__=func):
                obj = type(obj)(theme_namespace_decorator(func, use_cls=True))
            case FunctionType() | LambdaType():
                obj = theme_namespace_decorator(obj)
        return obj

    @staticmethod
    def __theme_initializer_decorator(
        func: Callable[[ClassWithThemeNamespaceMeta], None]
    ) -> Callable[[ClassWithThemeNamespaceMeta], None]:
        @wraps(func)
        def wrapper(cls: ClassWithThemeNamespaceMeta, /) -> None:
            theme_namespace: str = cls.get_theme_namespace() or _mangle_closed_namespace_name(cls)
            with ThemeNamespace(theme_namespace):
                return func(cls)

        return wrapper


def _mangle_closed_namespace_name(cls: type) -> str:
    return f"_{cls.__name__.strip('_')}__{id(cls):#x}"


class ClassWithThemeNamespace(Object, metaclass=ClassWithThemeNamespaceMeta):
    @classmethod
    def __theme_init__(cls) -> None:
        pass


_S = TypeVar("_S", bound=ClassWithThemeNamespaceMeta)


def set_default_theme_namespace(
    namespace: str, *, allow_extension: bool = False, include_none_namespace: bool = False
) -> Callable[[_S], _S]:
    def decorator(cls: _S, /) -> _S:
        cls.set_theme_namespace(namespace, allow_extension=allow_extension, include_none_namespace=include_none_namespace)
        return cls

    return decorator


def closed_namespace(cls: _S) -> _S:
    cls.set_closed_theme_namespace()
    return cls


@overload
def no_theme_decorator(func: _T) -> _T:
    ...


@overload
def no_theme_decorator(*, permanent: bool = True) -> Callable[[_T], _T]:
    ...


def no_theme_decorator(func: Any = None, *, permanent: bool = True) -> Any:
    permanent = bool(permanent)

    def decorator(func: Any) -> Any:
        with suppress(AttributeError):
            delattr(func, "__force_apply_theme_decorator__")
        setattr(func, "__no_theme_decorator__", "once" if not permanent else "permanent")
        return func

    return decorator(func) if func is not None else decorator


def force_apply_theme_decorator(func: _T) -> _T:
    with suppress(AttributeError):
        delattr(func, "__no_theme_decorator__")
    setattr(func, "__force_apply_theme_decorator__", True)
    return func
