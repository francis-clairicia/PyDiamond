# -*- coding: Utf-8 -*

from __future__ import annotations
from typing import Any, Dict, Iterator, List, Tuple, Union


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

Theme = Union[str, List[str], None]


class MetaThemedObject(type):
    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwds: Any) -> None:
        super().__init__(name, bases, namespace, **kwds)
        if all(not isinstance(b, MetaThemedObject) for b in bases):
            if cls not in _CLASSES_NOT_USING_PARENT_THEMES:
                _CLASSES_NOT_USING_PARENT_THEMES.append(cls)
            if cls not in _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES:
                _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.append(cls)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        default_theme: List[str] = list()
        for parent in cls.__get_all_parent_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
            default_theme += _HIDDEN_DEFAULT_THEME.get(parent, list()) + _DEFAULT_THEME.get(parent, list())
        default_theme += _HIDDEN_DEFAULT_THEME.get(cls, list()) + _DEFAULT_THEME.get(cls, list())
        theme: Theme = kwargs.pop("theme", None)
        if theme is None:
            theme = list()
        elif isinstance(theme, str):
            theme = [theme]
        theme_kwargs: Dict[str, Any] = cls.get_theme_options(*default_theme, *theme)
        return super().__call__(*args, **(theme_kwargs | kwargs))

    def set_theme(cls, name: str, options: Dict[str, Any]) -> None:
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

    def set_default_theme(cls, name: Theme) -> None:
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
        theme_kwargs: Dict[str, Any] = dict()
        for t in themes:
            for parent in reversed(list(cls.__get_all_parent_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_THEMES))):
                theme_kwargs |= cls.__get_theme_options(parent, t)
            theme_kwargs |= cls.__get_theme_options(cls, t)
        return theme_kwargs

    @staticmethod
    def __get_theme_options(cls: type, theme: str) -> Dict[str, Any]:
        if theme.startswith(_HIDDEN_THEME_PREFIX):
            return _HIDDEN_THEMES.get(cls, dict()).get(theme, dict())
        return _THEMES[ThemeNamespace.get()].get(cls, dict()).get(theme, dict())

    @staticmethod
    def __get_all_parent_class(cls: type, do_not_search_for: List[type] = []) -> Iterator[type]:
        if not isinstance(cls, MetaThemedObject) or cls in do_not_search_for:
            return
        for base in cls.__bases__:
            if not isinstance(base, MetaThemedObject):
                continue
            yield base
            yield from MetaThemedObject.__get_all_parent_class(base)


class ThemedObject(metaclass=MetaThemedObject):
    def __init_subclass__(cls, use_parent_theme: bool = True, use_parent_default_theme: bool = True) -> None:
        super().__init_subclass__()
        if not use_parent_theme:
            _CLASSES_NOT_USING_PARENT_THEMES.append(cls)
            use_parent_default_theme = False
        if not use_parent_default_theme:
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.append(cls)
