# -*- coding: Utf-8 -*
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
    "apply_theme_decorator",
    "closed_namespace",
    "no_theme_decorator",
    "set_default_theme_namespace",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from collections import OrderedDict, defaultdict, deque
from contextlib import nullcontext, suppress
from functools import cached_property
from inspect import Parameter, Signature
from itertools import chain, filterfalse
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

from ..system.object import Object, ObjectMeta, mro
from ..system.utils._mangling import PRIVATE_ATTRIBUTE_PATTERN
from ..system.utils.abc import concreteclassmethod, isabstractmethod
from ..system.utils.functools import cache, wraps

_ClassTheme: TypeAlias = MutableMapping[str, MappingProxyType[str, Any]]
_ClassThemeProxy: TypeAlias = MappingProxyType[str, MappingProxyType[str, Any]]
_ClassThemeDict: TypeAlias = MutableMapping[type, _ClassTheme]
_ClassThemeDictProxy: TypeAlias = MappingProxyType[type, _ClassThemeProxy]
_ClassDefaultTheme: TypeAlias = Sequence[str]
_ClassDefaultThemeDict: TypeAlias = MutableMapping[type, _ClassDefaultTheme]
_ClassDefaultThemeDictProxy: TypeAlias = MappingProxyType[type, _ClassDefaultTheme]

_THEMES: _ClassThemeDict = dict()
_DEFAULT_THEME: _ClassDefaultThemeDict = dict()
_CLASSES_NOT_USING_PARENT_THEMES: set[type] = set()
_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES: set[type] = set()


class _ThemeNamespaceBackupItem(NamedTuple):
    name: str | None
    theme_dict: _ClassThemeDict
    default_theme_dict: _ClassDefaultThemeDict


@final
class ThemeNamespace(ContextManager["ThemeNamespace"], Object):

    __THEMES_DEFAULT_DICT: Final[_ClassThemeDict] = _THEMES
    __THEMES_DICT_NAMESPACE: Final[dict[str, _ClassThemeDict]] = {}
    __DEFAULT_THEME_DEFAULT_DICT: Final[_ClassDefaultThemeDict] = _DEFAULT_THEME
    __DEFAULT_THEME_DICT_NAMESPACE: Final[dict[str, _ClassDefaultThemeDict]] = {}
    __actual_namespace: ClassVar[str | None] = None

    def __init__(self, namespace: str, *, extend: bool = False, include_none_namespace: bool = True) -> None:
        self.__namespace: str = str(namespace)
        self.__save_namespaces: deque[_ThemeNamespaceBackupItem] = deque()
        self.__extend: bool = extend
        self.__include_none_namespace: bool = include_none_namespace

    def __enter__(self) -> ThemeNamespace:
        global _THEMES, _DEFAULT_THEME
        THEMES_DICT_NAMESPACE: dict[str, _ClassThemeDict] = ThemeNamespace.__THEMES_DICT_NAMESPACE
        DEFAULT_THEME_DICT_NAMESPACE: dict[str, _ClassDefaultThemeDict] = ThemeNamespace.__DEFAULT_THEME_DICT_NAMESPACE
        with ThemeNamespace.get_lock():
            save_namespace = _ThemeNamespaceBackupItem(
                name=ThemeNamespace.__actual_namespace,
                theme_dict=_THEMES,
                default_theme_dict=_DEFAULT_THEME,
            )
            self.__save_namespaces.append(save_namespace)
            ThemeNamespace.__actual_namespace = namespace = self.__namespace
            try:
                _THEMES = THEMES_DICT_NAMESPACE[namespace]
            except KeyError:
                THEMES_DICT_NAMESPACE[namespace] = _THEMES = dict()
            try:
                _DEFAULT_THEME = DEFAULT_THEME_DICT_NAMESPACE[namespace]
            except KeyError:
                DEFAULT_THEME_DICT_NAMESPACE[namespace] = _DEFAULT_THEME = dict()
            if self.__extend and (self.__include_none_namespace or save_namespace.name is not None):
                _THEMES = self.__ExtendedThemeDict(_THEMES, save_namespace.theme_dict)
                _DEFAULT_THEME = self.__ExtendedDefaultThemeDict(_DEFAULT_THEME, save_namespace.default_theme_dict)
        return self

    def __exit__(self, *args: Any) -> None:
        global _THEMES, _DEFAULT_THEME
        try:
            save_namespace: _ThemeNamespaceBackupItem = self.__save_namespaces.pop()
        except IndexError:
            return
        with ThemeNamespace.get_lock():
            _THEMES = save_namespace.theme_dict
            _DEFAULT_THEME = save_namespace.default_theme_dict
            ThemeNamespace.__actual_namespace = save_namespace.name

    @staticmethod
    def get_actual() -> str | None:
        return ThemeNamespace.__actual_namespace

    @staticmethod
    def get_theme_dict(namespace: str | None) -> _ClassThemeDictProxy:
        theme_dict: _ClassThemeDict
        if namespace is None:
            theme_dict = ThemeNamespace.__THEMES_DEFAULT_DICT
        else:
            theme_dict = ThemeNamespace.__THEMES_DICT_NAMESPACE.get(namespace, {})
        with ThemeNamespace.get_lock():
            return MappingProxyType({cls: MappingProxyType(theme) for cls, theme in theme_dict.items()})

    @staticmethod
    def get_default_theme_dict(namespace: str | None) -> _ClassDefaultThemeDictProxy:
        mapping: MutableMapping[type, Sequence[str]]
        if namespace is None:
            mapping = ThemeNamespace.__DEFAULT_THEME_DEFAULT_DICT
        else:
            mapping = ThemeNamespace.__DEFAULT_THEME_DICT_NAMESPACE.get(namespace, {})
        return MappingProxyType(mapping)

    @property
    def name(self) -> str:
        return self.__namespace

    @staticmethod
    @cache
    def get_lock() -> RLock:
        return RLock()

    class __ExtendedThemeDict(_ClassThemeDict):
        def __init__(self, actual: _ClassThemeDict, extension: _ClassThemeDict) -> None:
            super().__init__()
            self.__actual: _ClassThemeDict = actual
            self.__extension: _ClassThemeDict = extension

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
            NoTheme = super().__new__(_NoThemeType, "NoTheme")
        return NoTheme


NoTheme: _NoThemeType = _NoThemeType()

ThemeType: TypeAlias = str | Iterable[str]


@final
class _ThemedObjectMROResolver(Object):
    __marker: Any = object()

    def __init__(self, max_size: int = 128) -> None:
        self.__lru_cache: defaultdict[ThemedObjectMeta, OrderedDict[tuple[type, ...], tuple[ThemedObjectMeta, ...]]]
        self.__lru_cache = defaultdict(OrderedDict)
        self.__max_size: int = max_size
        self.__lock: defaultdict[ThemedObjectMeta, RLock] = defaultdict(RLock)
        self.__name: str | None = None

    def __set_name__(self, owner: type, name: str, /) -> None:
        self.__name = name

    @overload
    def __get__(self, obj: None, objtype: type, /) -> _ThemedObjectMROResolver:
        ...

    @overload
    def __get__(self, obj: ThemedObjectMeta, objtype: type | None = None, /) -> tuple[ThemedObjectMeta, ...]:
        ...

    def __get__(
        self, obj: ThemedObjectMeta | None, objtype: type | None = None, /
    ) -> _ThemedObjectMROResolver | tuple[ThemedObjectMeta, ...]:
        if obj is None:
            if objtype is None:
                raise TypeError("__get__(None, None) is forbidden")
            return self

        cache_key = tuple(sorted(obj.__virtual_themed_class_bases__, key=lambda cls: cls.__qualname__))
        null = self.__marker

        with self.__lock[obj]:
            lru_cache: OrderedDict[tuple[type, ...], tuple[ThemedObjectMeta, ...]] = self.__lru_cache[obj]
            mro: tuple[ThemedObjectMeta, ...] = lru_cache.get(cache_key, null)
            if mro is not null:
                lru_cache.move_to_end(cache_key)
                return mro
            lru_cache[cache_key] = mro = self.resolve(obj)
            if len(lru_cache) > self.__max_size:
                lru_cache.popitem(last=False)
            return mro

    def resolve(self, cls: ThemedObjectMeta) -> tuple[ThemedObjectMeta, ...]:
        name: str | None = self.__name
        if name is None:
            raise TypeError("__set_name__() was not called")
        cls_mro: Sequence[type]
        try:
            # Will work in most common cases
            cls_mro = (cls,) + mro(*cls.__virtual_themed_class_bases__, *cls.__bases__, attr=name)
        except TypeError:
            # Try in the inverse order ?
            cls_mro = (cls,) + mro(*cls.__bases__, *cls.__virtual_themed_class_bases__, attr=name)

        return tuple(c for c in cls_mro if isinstance(c, ThemedObjectMeta))


class ThemedObjectMeta(ObjectMeta):
    __virtual_themed_class_bases__: tuple[ThemedObjectMeta, ...]
    __theme_ignore__: Sequence[str]
    __theme_associations__: dict[type, dict[str, str]]
    __theme_override__: Sequence[str]

    __themed_class_mro__: Final[_ThemedObjectMROResolver] = _ThemedObjectMROResolver()

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
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            if "theme" not in parameters:
                if not no_theme and not has_kwargs:
                    raise TypeError(f"{func.__qualname__}: Can't support 'theme' parameter")
            else:
                param: Parameter = parameters["theme"]
                if param.kind is not Parameter.KEYWORD_ONLY:
                    raise TypeError(f"{func.__qualname__}: 'theme' is a {param.kind.description} parameter")
                if param.default is not None:
                    raise TypeError(f"{func.__qualname__}: 'theme' parameter must have None as default value")

        if all(not isabstractmethod(attr) for attr in namespace.values()):
            new_method: Callable[..., Any] | None = namespace.get("__new__")
            init_method: Callable[..., None] | None = namespace.get("__init__")
            if new_method is not None:
                check_parameters(new_method)
            if init_method is not None:
                check_parameters(init_method)

        for attr_name in ("__theme_ignore__", "__theme_override__"):
            sequence: str | Sequence[str] = namespace.pop(attr_name, ())
            if isinstance(sequence, str):
                sequence = (sequence,)
            else:
                sequence = tuple(sequence)
            namespace[attr_name] = sequence

        namespace.setdefault("__theme_associations__", {})
        namespace["_no_use_of_themes_"] = bool(no_theme)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if not use_parent_theme:
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            setattr(cls, "_no_parent_theme_", True)
            use_parent_default_theme = False
        if not use_parent_default_theme:
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
            setattr(cls, "_no_parent_default_theme_", True)
        setattr(cls, "_is_abstract_theme_class_", False)
        super().__setattr__(cls, "__virtual_themed_class_bases__", ())
        if all(not isinstance(b, ThemedObjectMeta) or b.is_abstract_theme_class() for b in bases):
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
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
            if not all(isinstance(t, str) for t in theme):
                raise TypeError("Themes must be str objects")
            if any(t is NoTheme for t in theme):
                raise ValueError("The 'NoTheme' special value is in the sequence")

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
    def set_theme(cls, name: str, options: dict[str, Any], update: bool = False, ignore_unusable: bool = True) -> None:
        ...

    @overload
    def set_theme(cls, name: str, options: None) -> None:
        ...

    def set_theme(cls, name: str, options: dict[str, Any] | None, update: bool = False, ignore_unusable: bool = True) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")
        if getattr(cls, "_no_use_of_themes_", False):
            raise TypeError(f"{cls.__qualname__} do not use themes")
        if name is NoTheme:
            raise ValueError("Couldn't set 'NoTheme' as theme")

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

        def check_options(func: Callable[..., Any], options: dict[str, Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            for option in filterfalse(ignored_parameters.__contains__, list(options)):
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

        all_parents_classes = (
            ThemedObjectMeta.__get_all_parent_classes(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_THEMES)
            if parent_themes
            else ()
        )
        theme_key_associations = cls.__theme_associations__
        theme_key_override = cls.__theme_override__
        for t in dict.fromkeys(themes):
            for parent in all_parents_classes:
                parent_theme_kwargs = parent.get_theme_options(
                    t, parent_themes=True, use_default_themes=False, ignore_unusable=False
                )
                for parent_param, cls_param in theme_key_associations.get(parent, {}).items():
                    if parent_param not in parent_theme_kwargs:
                        continue
                    parent_theme_kwargs[cls_param] = parent_theme_kwargs.pop(parent_param)
                for param in theme_key_override:
                    parent_theme_kwargs.pop(param, None)
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

        if parent_default_themes:
            get_all_parents_class = ThemedObjectMeta.__get_all_parent_classes
            for parent in get_all_parents_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
                default_theme |= dict.fromkeys(parent.get_default_themes(parent_default_themes=False))
        with suppress(KeyError):
            default_theme |= dict.fromkeys(_DEFAULT_THEME[cls])

        return tuple(default_theme)

    def is_abstract_theme_class(cls) -> bool:
        return bool(getattr(cls, "_is_abstract_theme_class_", False))

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
        if not getattr(subclass, "_no_parent_theme_", False):
            _CLASSES_NOT_USING_PARENT_THEMES.discard(subclass)
        if not getattr(subclass, "_no_parent_default_theme_", False):
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.discard(subclass)
        return subclass

    @staticmethod
    def __get_all_parent_classes(cls: ThemedObjectMeta, *, do_not_search_for: set[type]) -> Sequence[ThemedObjectMeta]:
        if cls in do_not_search_for:
            return ()

        valid_parent_classes = set(ThemedObjectMeta.__travel_parent_classes(cls, do_not_search_for=do_not_search_for))
        return tuple(filter(valid_parent_classes.__contains__, reversed(cls.__themed_class_mro__)))

    @staticmethod
    def __travel_parent_classes(cls: ThemedObjectMeta, *, do_not_search_for: set[type]) -> Iterator[ThemedObjectMeta]:
        for base in chain(cls.__bases__, cls.__virtual_themed_class_bases__):
            if not isinstance(base, ThemedObjectMeta) or base.is_abstract_theme_class():
                continue
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
    __classes: Final[set[ClassWithThemeNamespaceMeta]] = set()

    __unique_theme_namespace_cache: Final[dict[type, ThemeNamespace]] = dict()
    __extended_unique_theme_namespace_cache: Final[dict[type, ThemeNamespace]] = dict()

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
            apply_theme_decorator: bool = getattr(attr_obj, "__apply_theme_decorator__", False)
            if attr_name == "__theme_init__":
                if not isinstance(attr_obj, classmethod):
                    raise TypeError("'__theme_init__' must be a classmethod")
                if no_theme_decorator in ("once", "permanent") or hasattr(attr_obj, "__apply_theme_decorator__"):
                    raise TypeError("'__theme_init__' must not be decorated")
                namespace[attr_name] = type(attr_obj)(mcs.__theme_initializer_decorator(attr_obj.__func__))
                continue
            if no_theme_decorator in ("once", "permanent"):
                if PRIVATE_ATTRIBUTE_PATTERN.fullmatch(attr_name):
                    no_theme_decorator = "once"
                if no_theme_decorator == "once":
                    if apply_theme_decorator:
                        raise ValueError("Invalid decorator usage")
                    continue
                cls_theme_decorator_exempt.add(attr_name)
            for pattern in theme_decorator_exempt_regex:
                match = pattern.fullmatch(attr_name)
                if match is not None and mcs.validate_theme_decorator_exempt_from_regex(match, attr_obj):
                    cls_theme_decorator_exempt.add(attr_name)
            if not apply_theme_decorator:
                if attr_name in cls_theme_decorator_exempt:
                    continue
                if isinstance(attr_obj, (property, cached_property)):
                    continue
            namespace[attr_name] = mcs.__apply_theme_namespace_decorator(attr_obj)
        namespace["_theme_decorator_exempt_"] = frozenset(cls_theme_decorator_exempt)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)
        if hasattr(cls, "__theme_init__") and not cls.__abstractmethods__:
            mcs.__classes.add(cls)
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
            raise ValueError("Closed namespace setting must not allow extension theme extension")
        ClassWithThemeNamespaceMeta.__namespaces[cls] = ThemeNamespace(
            namespace=str(namespace),
            extend=bool(allow_extension),
            include_none_namespace=bool(include_none_namespace),
        )

    @final
    @concreteclassmethod
    def remove_theme_namespace(cls) -> None:
        ClassWithThemeNamespaceMeta.__namespaces.pop(cls, None)

    @final
    @concreteclassmethod
    def theme_initialize(cls) -> None:
        theme_initialize: Callable[[], None] = getattr(cls, "__theme_init__")
        theme_initialize()

    @final
    @staticmethod
    def theme_initialize_all() -> None:
        for cls in ClassWithThemeNamespaceMeta.__classes:
            cls.theme_initialize()

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
                re_compile(r"__\w+__"),
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
        get_cls: Callable[[Any], type] = (lambda o: o) if use_cls else type  # type: ignore[no-any-return]
        null = nullcontext()

        unique_theme_namespace_cache: dict[type, ThemeNamespace]
        extended_unique_theme_namespace_cache: dict[type, ThemeNamespace]

        unique_theme_namespace_cache = ClassWithThemeNamespaceMeta.__unique_theme_namespace_cache
        extended_unique_theme_namespace_cache = ClassWithThemeNamespaceMeta.__extended_unique_theme_namespace_cache

        def get_unique_theme_namespace(cls: type, *, extend: bool) -> ThemeNamespace:
            cache: dict[type, ThemeNamespace]
            if extend:
                cache = extended_unique_theme_namespace_cache
            else:
                cache = unique_theme_namespace_cache
            try:
                return cache[cls]
            except KeyError:
                namespace = ThemeNamespace(
                    namespace=_mangle_closed_namespace_name(cls),
                    extend=extend,
                    include_none_namespace=extend,
                )
                cache[cls] = namespace
                return namespace

        @wraps(func)
        def wrapper(__cls_or_self: Any, /, *args: Any, **kwargs: Any) -> Any:
            cls: type = get_cls(__cls_or_self)
            theme_namespace: ThemeNamespace | None = ClassWithThemeNamespaceMeta.__namespaces.get(cls)
            unique_theme_namespace_name: str = _mangle_closed_namespace_name(cls)
            extend_unique_theme_namespace: bool = True
            if theme_namespace is not None and theme_namespace.name == unique_theme_namespace_name:
                extend_unique_theme_namespace = False
                theme_namespace = None
            with (
                theme_namespace or null,
                get_unique_theme_namespace(
                    cls,
                    extend=extend_unique_theme_namespace,
                ),
            ):
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
    def __theme_initializer_decorator(func: Callable[[type], None]) -> Callable[[type], None]:
        @wraps(func)
        def wrapper(cls: type, /) -> None:
            theme_namespace: str = _mangle_closed_namespace_name(cls)
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


@overload
def set_default_theme_namespace(
    namespace: str, *, allow_extension: bool = False, include_none_namespace: bool = False
) -> Callable[[_S], _S]:
    ...


@overload
def set_default_theme_namespace(
    namespace: str, cls: _S, *, allow_extension: bool = False, include_none_namespace: bool = False
) -> None:
    ...


def set_default_theme_namespace(
    namespace: str, cls: _S | None = None, *, allow_extension: bool = False, include_none_namespace: bool = False
) -> Callable[[_S], _S] | None:
    def decorator(cls: _S, /) -> _S:
        if namespace == _mangle_closed_namespace_name(cls):
            raise ValueError("use closed_namespace() decorator")
        cls.set_theme_namespace(namespace, allow_extension=allow_extension, include_none_namespace=include_none_namespace)
        return cls

    if cls is not None:
        decorator(cls)
        return None
    return decorator


def closed_namespace(cls: _S) -> _S:
    cls.set_theme_namespace(_mangle_closed_namespace_name(cls), allow_extension=False, include_none_namespace=False)
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
            delattr(func, "__apply_theme_decorator__")
        setattr(func, "__no_theme_decorator__", "once" if not permanent else "permanent")
        return func

    return decorator(func) if func is not None else decorator


def apply_theme_decorator(func: _T) -> _T:
    with suppress(AttributeError):
        delattr(func, "__no_theme_decorator__")
    setattr(func, "__apply_theme_decorator__", True)
    return func
