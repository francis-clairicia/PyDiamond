# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Themed objects module"""

from __future__ import annotations

__all__ = ["MetaThemedObject", "NoTheme", "ThemeNamespace", "ThemeType", "ThemedObject", "abstract_theme_class"]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta
from contextlib import suppress
from inspect import Parameter, Signature
from operator import truth
from typing import (
    Any,
    Callable,
    ClassVar,
    ContextManager,
    Dict,
    Iterator,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    overload,
)

_ClassTheme = Dict[str, Dict[str, Any]]
_ClassThemeDict = Dict[type, _ClassTheme]

_THEMES: _ClassThemeDict = dict()
_DEFAULT_THEME: Dict[type, List[str]] = dict()
_CLASSES_NOT_USING_PARENT_THEMES: Set[type] = set()
_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES: Set[type] = set()


class ThemeNamespace(ContextManager["ThemeNamespace"]):

    __DEFAULT: ClassVar[_ClassThemeDict] = _THEMES
    __NAMESPACE: ClassVar[Dict[str, _ClassThemeDict]] = {}
    __actual_namespace: ClassVar[Optional[str]] = None

    def __init__(self, /, namespace: str) -> None:
        self.__namespace: str = str(namespace)
        self.__save_namespace: Optional[str] = None
        self.__entered: int = 0

    def __enter__(self, /) -> ThemeNamespace:
        global _THEMES
        if self.__entered == 0:
            self.__save_namespace = ThemeNamespace.__actual_namespace
            ThemeNamespace.__actual_namespace = namespace = self.__namespace
            NAMESPACE: Dict[str, _ClassThemeDict] = ThemeNamespace.__NAMESPACE
            try:
                _THEMES = NAMESPACE[namespace]
            except KeyError:
                NAMESPACE[namespace] = _THEMES = dict()
        self.__entered += 1
        return self

    def __exit__(self, /, *args: Any) -> None:
        global _THEMES
        if self.__entered == 0:
            return
        self.__entered -= 1
        if self.__entered > 0:
            return
        namespace: Optional[str] = self.__save_namespace
        self.__save_namespace = None
        NAMESPACE: Dict[str, _ClassThemeDict] = ThemeNamespace.__NAMESPACE
        DEFAULT: _ClassThemeDict = ThemeNamespace.__DEFAULT
        if namespace is None:
            _THEMES = DEFAULT
        else:
            _THEMES = NAMESPACE[namespace]
        ThemeNamespace.__actual_namespace = namespace

    @property
    def namespace(self, /) -> str:
        return self.__namespace


_T = TypeVar("_T")


class _NoThemeType(str):
    def __init_subclass__(cls, /) -> None:
        raise TypeError("No subclass are allowed")

    def __new__(cls, /) -> _NoThemeType:
        global NoTheme
        try:
            return NoTheme
        except NameError:
            NoTheme = super().__new__(_NoThemeType, "NoTheme")
        return NoTheme


NoTheme: _NoThemeType = _NoThemeType()

ThemeType = Union[str, List[str]]


class MetaThemedObject(ABCMeta):
    __virtual_themed_class_bases__: Tuple[MetaThemedObject, ...]

    def __new__(
        metacls,
        /,
        name: str,
        bases: Tuple[type, ...],
        namespace: Dict[str, Any],
        *,
        use_parent_theme: bool = True,
        use_parent_default_theme: bool = True,
        **kwargs: Any,
    ) -> MetaThemedObject:
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
            new_method: Optional[Callable[..., Any]] = namespace.get("__new__")
            init_method: Optional[Callable[..., None]] = namespace.get("__init__")
            if new_method is not None:
                check_parameters(new_method)
            if init_method is not None:
                check_parameters(init_method)

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)
        if not use_parent_theme:
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            setattr(cls, "__no_parent_theme__", True)
            use_parent_default_theme = False
        if not use_parent_default_theme:
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
            setattr(cls, "__no_parent_default_theme__", True)
        setattr(cls, "__is_abstract_theme_class__", False)
        cls.__virtual_themed_class_bases__ = ()
        if all(not isinstance(b, MetaThemedObject) or b.is_abstract_theme_class() for b in bases):
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
        return cls

    def __call__(cls, /, *args: Any, **kwargs: Any) -> Any:
        create_object: Callable[..., Any] = super().__call__
        if cls.is_abstract_theme_class():
            return create_object(*args, **kwargs)

        theme: Optional[ThemeType] = kwargs.get("theme")
        if theme is NoTheme:
            return create_object(*args, **kwargs)
        if theme is None:
            theme = []
        elif isinstance(theme, str):
            theme = [theme]
        else:
            theme = list(theme)
            if not all(isinstance(t, str) for t in theme):
                raise TypeError("Themes must be str objects")

        default_theme: Tuple[str, ...] = cls.get_default_themes()
        theme_kwargs: Dict[str, Any] = cls.get_theme_options(*default_theme, *theme, ignore_unusable=True)
        if theme_kwargs:
            kwargs = theme_kwargs | kwargs
        return create_object(*args, **kwargs)

    def __setattr__(cls, /, name: str, value: Any) -> None:
        if name in ("__new__", "__init__"):
            raise AttributeError("can't set attribute")
        return super().__setattr__(name, value)

    @overload
    def set_theme(cls, /, name: str, options: Dict[str, Any], update: bool = False, ignore_unusable: bool = False) -> None:
        ...

    @overload
    def set_theme(cls, /, name: str, options: None) -> None:
        ...

    def set_theme(
        cls, /, name: str, options: Optional[Dict[str, Any]], update: bool = False, ignore_unusable: bool = False
    ) -> None:
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

        def check_options(func: Callable[..., Any], options: Dict[str, Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            for option in list(options):
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

        default_new_method: Callable[[Type[object]], Any] = object.__new__
        default_init_method: Callable[[object], None] = object.__init__
        new_method: Callable[..., Any] = getattr(cls, "__new__", default_new_method)
        init_method: Callable[..., None] = getattr(cls, "__init__", default_init_method)

        if new_method is default_new_method and init_method is default_init_method:
            raise TypeError(f"{cls.__name__} does not override default object constructors")
        if new_method is not default_new_method:
            check_options(new_method, options)
        if init_method is not default_init_method:
            check_options(init_method, options)

        theme_dict: Dict[str, Dict[str, Any]]

        if cls not in _THEMES:
            _THEMES[cls] = theme_dict = dict()
        else:
            theme_dict = _THEMES[cls]
        if name not in theme_dict or not update:
            theme_dict[name] = options.copy()
        else:
            theme_dict[name] |= options

    @overload
    def set_default_theme(cls, name: str, /, *names: str, update: bool = False) -> None:
        ...

    @overload
    def set_default_theme(cls, name: None, /) -> None:
        ...

    def set_default_theme(cls, name: Union[str, None], /, *names: str, update: bool = False) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")

        if name is None:
            if names:
                raise TypeError("Invalid arguments")
            _DEFAULT_THEME.pop(cls, None)
            return
        default_themes: Dict[str, None] = dict.fromkeys([name, *names])
        if any(theme is NoTheme for theme in default_themes):
            raise ValueError("Couldn't set 'NoTheme' as default theme")
        if cls not in _DEFAULT_THEME or not update:
            _DEFAULT_THEME[cls] = list(default_themes)
        else:
            _DEFAULT_THEME[cls] = list(dict.fromkeys((*_DEFAULT_THEME[cls], *default_themes)))

    def get_theme_options(cls, /, *themes: str, parent_themes: bool = True, ignore_unusable: bool = False) -> Dict[str, Any]:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes does not have themes.")

        theme_kwargs: Dict[str, Any] = dict()

        def get_theme_options(cls: type, theme: str) -> None:
            nonlocal theme_kwargs
            with suppress(KeyError):
                theme_kwargs |= _THEMES[cls][theme]

        get_all_parents_class = MetaThemedObject.__get_all_parent_class
        for t in dict.fromkeys(themes):
            if parent_themes:
                for parent in get_all_parents_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_THEMES):
                    get_theme_options(parent, t)
            get_theme_options(cls, t)

        if not ignore_unusable or not theme_kwargs:
            return theme_kwargs

        def check_options(func: Callable[..., Any]) -> None:
            sig: Signature = Signature.from_callable(func, follow_wrapped=True)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            for option in list(theme_kwargs):
                if option not in parameters:
                    if not has_kwargs:
                        theme_kwargs.pop(option)
                    continue
                param: Parameter = parameters[option]
                if param.kind is not Parameter.KEYWORD_ONLY or param.default is Parameter.empty:
                    theme_kwargs.pop(option)

        default_new_method: Callable[[Type[object]], Any] = object.__new__
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

    def get_default_themes(cls, /, *, parent_default_themes: bool = True) -> Tuple[str, ...]:
        default_theme: Dict[str, None] = dict()

        def add_default_themes(cls: MetaThemedObject) -> None:
            nonlocal default_theme
            with suppress(KeyError):
                default_theme |= dict.fromkeys(_DEFAULT_THEME[cls])

        if parent_default_themes:
            get_all_parents_class = MetaThemedObject.__get_all_parent_class
            for parent in get_all_parents_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
                add_default_themes(parent)
        add_default_themes(cls)

        return tuple(default_theme)

    def is_abstract_theme_class(cls, /) -> bool:
        return truth(getattr(cls, "__is_abstract_theme_class__", False))

    def register(cls, /, subclass: Type[_T]) -> Type[_T]:
        def register_themed_subclass(subclass: MetaThemedObject) -> None:
            subclass.__virtual_themed_class_bases__ = (*subclass.__virtual_themed_class_bases__, cls)
            if not getattr(subclass, "__no_parent_theme__", False):
                try:
                    _CLASSES_NOT_USING_PARENT_THEMES.remove(subclass)
                except (ValueError, KeyError):
                    pass
            if not getattr(subclass, "__no_parent_default_theme__", False):
                try:
                    _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.remove(subclass)
                except (ValueError, KeyError):
                    pass

        super().register(subclass)
        if isinstance(subclass, MetaThemedObject):
            register_themed_subclass(subclass)  # type: ignore
        return subclass

    @staticmethod
    def __get_all_parent_class(cls: MetaThemedObject, do_not_search_for: Set[type]) -> List[MetaThemedObject]:
        def get_all_parent_class(cls: MetaThemedObject) -> Iterator[MetaThemedObject]:
            if not isinstance(cls, MetaThemedObject) or cls in do_not_search_for or cls.is_abstract_theme_class():
                return
            mro: List[type]
            try:
                mro = list(getattr(cls, "__mro__"))[1:]
            except AttributeError:
                mro = list(cls.__bases__)

            for base in (*mro, *cls.__virtual_themed_class_bases__):
                if not isinstance(base, MetaThemedObject) or base.is_abstract_theme_class():
                    continue
                yield base
                yield from get_all_parent_class(base)

        return list(reversed(dict.fromkeys(get_all_parent_class(cls))))


_ThemedObjectClass = TypeVar("_ThemedObjectClass")


def abstract_theme_class(cls: _ThemedObjectClass) -> _ThemedObjectClass:
    setattr(cls, "__is_abstract_theme_class__", True)
    return cls


@abstract_theme_class
class ThemedObject(metaclass=MetaThemedObject):
    pass
