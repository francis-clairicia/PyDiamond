# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, TypeVar, Union, cast
from operator import truth


class ThemeNamespace:

    __NAMESPACE: Any = None

    def __init__(self, namespace: Any) -> None:
        self.__namespace: Any = namespace
        self.__save_namespace: Any = None

    def __enter__(self) -> ThemeNamespace:
        self.__save_namespace = ThemeNamespace.__NAMESPACE
        ThemeNamespace.__NAMESPACE = self.__namespace
        if ThemeNamespace.__NAMESPACE not in _THEMES:
            _THEMES[ThemeNamespace.__NAMESPACE] = dict()
        return self

    def __exit__(self, *args: Any) -> None:
        ThemeNamespace.__NAMESPACE = self.__save_namespace

    @staticmethod
    def get() -> Any:
        return ThemeNamespace.__NAMESPACE

    @property
    def namespace(self) -> Any:
        return self.__namespace


_ClassTheme = Dict[str, Dict[str, Any]]
_ClassThemeDict = Dict[type, _ClassTheme]

_THEMES: Dict[Any, _ClassThemeDict] = {ThemeNamespace.get(): dict()}
_HIDDEN_THEMES: _ClassThemeDict = dict()
_DEFAULT_THEME: Dict[type, List[str]] = dict()
_HIDDEN_DEFAULT_THEME: Dict[type, List[str]] = dict()
_CLASSES_NOT_USING_PARENT_THEMES: List[type] = list()
_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES: List[type] = list()
_HIDDEN_THEME_PREFIX: str = "__"

_T = TypeVar("_T")


class _NoThemeType(str):
    pass


NoTheme: _NoThemeType = _NoThemeType()

Theme = Union[str, List[str]]


class MetaThemedObject(ABCMeta):
    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwds: Any) -> None:
        super().__init__(name, bases, namespace, **kwds)
        setattr(cls, "__is_abstract_theme_class__", False)
        cls.__virtual_themed_class_bases__: Tuple[MetaThemedObject, ...] = ()
        if all(not isinstance(b, MetaThemedObject) or b.is_abstract_theme_class() for b in bases):
            if cls not in _CLASSES_NOT_USING_PARENT_THEMES:
                _CLASSES_NOT_USING_PARENT_THEMES.append(cls)
            if cls not in _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES:
                _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.append(cls)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls.is_abstract_theme_class():
            return super().__call__(*args, **kwargs)

        theme: Optional[Theme] = kwargs.pop("theme", None)
        if isinstance(theme, _NoThemeType):
            return super().__call__(*args, **kwargs)

        default_theme: List[str] = list()
        for parent in cls.__get_all_parent_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
            default_theme += _HIDDEN_DEFAULT_THEME.get(parent, list()) + _DEFAULT_THEME.get(parent, list())
        default_theme += _HIDDEN_DEFAULT_THEME.get(cls, list()) + _DEFAULT_THEME.get(cls, list())
        if theme is None:
            theme = list()
        elif isinstance(theme, str):
            theme = [theme]
        theme_kwargs: Dict[str, Any] = cls.get_theme_options(*default_theme, *theme)
        return super().__call__(*args, **(theme_kwargs | kwargs))

    def set_theme(cls, name: str, options: Dict[str, Any]) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")
        if name is NoTheme:
            raise ValueError("Couldn't set 'NoTheme' as theme")

        theme_dict: Dict[str, Dict[str, Any]]

        if not name.startswith(_HIDDEN_THEME_PREFIX):
            if cls not in _THEMES[ThemeNamespace.get()]:
                _THEMES[ThemeNamespace.get()][cls] = dict()
            theme_dict = _THEMES[ThemeNamespace.get()][cls]
        else:
            if cls not in _HIDDEN_THEMES:
                _HIDDEN_THEMES[cls] = dict()
            theme_dict = _HIDDEN_THEMES[cls]
        if name not in theme_dict:
            theme_dict[name] = options
        else:
            theme_dict[name] |= options

    def set_default_theme(cls, name: Union[Theme, None]) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")
        if name is NoTheme:
            raise ValueError("Couldn't set 'NoTheme' as default theme")

        if name is None:
            _DEFAULT_THEME.pop(cls, None)
            return
        if isinstance(name, str):
            name = [name]
        for theme in name:
            default_theme: Dict[type, List[str]] = (
                _DEFAULT_THEME if not theme.startswith(_HIDDEN_THEME_PREFIX) else _HIDDEN_DEFAULT_THEME
            )
            if cls not in default_theme:
                default_theme[cls] = list()
            default_theme[cls].append(theme)

    def get_theme_options(cls, *themes: str) -> Dict[str, Any]:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes does not have themes.")

        theme_kwargs: Dict[str, Any] = dict()
        for t in themes:
            for parent in reversed(list(cls.__get_all_parent_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_THEMES))):
                theme_kwargs |= cls.__get_theme_options(parent, t)
            theme_kwargs |= cls.__get_theme_options(cls, t)
        return theme_kwargs

    def is_abstract_theme_class(cls) -> bool:
        return truth(getattr(cls, "__is_abstract_theme_class__", False))

    def register(cls, subclass: Type[_T]) -> Type[_T]:
        super().register(subclass)
        if isinstance(subclass, MetaThemedObject):
            cls.__register_themed_subclass(cast(MetaThemedObject, subclass))
        return subclass

    def __register_themed_subclass(cls, subclass: MetaThemedObject) -> None:
        subclass.__virtual_themed_class_bases__ = (*subclass.__virtual_themed_class_bases__, cls)
        if not getattr(subclass, "__no_parent_theme__", False):
            try:
                _CLASSES_NOT_USING_PARENT_THEMES.remove(subclass)
            except ValueError:
                pass
        if not getattr(subclass, "__no_parent_default_theme__", False):
            try:
                _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.remove(subclass)
            except ValueError:
                pass

    @staticmethod
    def __get_theme_options(cls: type, theme: str) -> Dict[str, Any]:
        if theme.startswith(_HIDDEN_THEME_PREFIX):
            return _HIDDEN_THEMES.get(cls, dict()).get(theme, dict())
        return _THEMES[ThemeNamespace.get()].get(cls, dict()).get(theme, dict())

    @staticmethod
    def __get_all_parent_class(cls: MetaThemedObject, do_not_search_for: List[type] = []) -> Iterator[MetaThemedObject]:
        if not isinstance(cls, MetaThemedObject) or cls in do_not_search_for or cls.is_abstract_theme_class():
            return
        for base in (*cls.__bases__, *cls.__virtual_themed_class_bases__):
            if not isinstance(base, MetaThemedObject) or base.is_abstract_theme_class():
                continue
            yield base
            yield from MetaThemedObject.__get_all_parent_class(base)


_ThemedObjectVar = TypeVar("_ThemedObjectVar", bound=MetaThemedObject)


def abstract_theme_class(cls: _ThemedObjectVar) -> _ThemedObjectVar:
    setattr(cls, "__is_abstract_theme_class__", True)
    return cls


@abstract_theme_class
class ThemedObject(metaclass=MetaThemedObject):
    def __init_subclass__(cls, /, *, use_parent_theme: bool = True, use_parent_default_theme: bool = True) -> None:
        super().__init_subclass__()
        if not use_parent_theme:
            _CLASSES_NOT_USING_PARENT_THEMES.append(cls)
            setattr(cls, "__no_parent_theme__", True)
            use_parent_default_theme = False
        if not use_parent_default_theme:
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.append(cls)
            setattr(cls, "__no_parent_default_theme__", True)
