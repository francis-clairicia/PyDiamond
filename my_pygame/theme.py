# -*- coding: Utf-8 -*

from __future__ import annotations
from abc import ABCMeta
from typing import (
    Any,
    Callable,
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
    cast,
    overload,
)
from operator import truth
from inspect import Parameter, Signature

_ClassTheme = Dict[str, Dict[str, Any]]
_ClassThemeDict = Dict[type, _ClassTheme]

_THEMES: _ClassThemeDict = dict()
_HIDDEN_THEMES: _ClassThemeDict = dict()
_DEFAULT_THEME: Dict[type, Set[str]] = dict()
_HIDDEN_DEFAULT_THEME: Dict[type, Set[str]] = dict()
_CLASSES_NOT_USING_PARENT_THEMES: Set[type] = set()
_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES: Set[type] = set()
_HIDDEN_THEME_PREFIX: str = "__"


class ThemeNamespace(ContextManager["ThemeNamespace"]):

    __DEFAULT: _ClassThemeDict = _THEMES
    __NAMESPACE: Dict[str, _ClassThemeDict] = {}
    __actual_namespace: Optional[str] = None

    def __init__(self, namespace: str) -> None:
        self.__namespace: str = str(namespace)
        self.__save_namespace: Optional[str] = None

    def __enter__(self) -> ThemeNamespace:
        global _THEMES
        self.__save_namespace = ThemeNamespace.__actual_namespace
        ThemeNamespace.__actual_namespace = namespace = self.__namespace
        try:
            theme_dict: _ClassThemeDict = ThemeNamespace.__NAMESPACE[namespace]
        except KeyError:
            ThemeNamespace.__NAMESPACE[namespace] = theme_dict = dict()
        _THEMES = theme_dict
        return self

    def __exit__(self, *args: Any) -> None:
        global _THEMES
        namespace, self.__save_namespace = self.__save_namespace, None
        if namespace is None:
            _THEMES = ThemeNamespace.__DEFAULT
        else:
            _THEMES = ThemeNamespace.__NAMESPACE.get(namespace, ThemeNamespace.__DEFAULT)
        ThemeNamespace.__actual_namespace = namespace

    @property
    def namespace(self) -> str:
        return self.__namespace


_T = TypeVar("_T")


class _NoThemeType(str):
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

    def __new__(cls) -> _NoThemeType:
        global NoTheme
        try:
            return NoTheme
        except NameError:
            return super().__new__(_NoThemeType, "NoTheme")


NoTheme: _NoThemeType = _NoThemeType()

ThemeType = Union[str, List[str]]


class MetaThemedObject(ABCMeta):
    def __init__(cls, name: str, bases: Tuple[type, ...], namespace: Dict[str, Any], **kwds: Any) -> None:
        super().__init__(name, bases, namespace, **kwds)
        setattr(cls, "__is_abstract_theme_class__", False)
        cls.__virtual_themed_class_bases__: Tuple[MetaThemedObject, ...] = ()
        if all(not isinstance(b, MetaThemedObject) or b.is_abstract_theme_class() for b in bases):
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        if cls.is_abstract_theme_class():
            return super().__call__(*args, **kwargs)

        theme: Optional[ThemeType] = kwargs.get("theme")
        if theme is NoTheme:
            return super().__call__(*args, **kwargs)

        default_theme: Set[str] = set()

        def add_default_themes(cls: MetaThemedObject) -> None:
            nonlocal default_theme
            try:
                default_theme.update(_HIDDEN_DEFAULT_THEME[cls])
            except KeyError:
                pass
            try:
                default_theme.update(_DEFAULT_THEME[cls])
            except KeyError:
                pass

        for parent in cls.__get_all_parent_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_DEFAULT_THEMES):
            add_default_themes(parent)
        add_default_themes(cls)
        if theme is None:
            theme = list()
        elif isinstance(theme, str):
            theme = [theme]
        theme_kwargs: Dict[str, Any] = cls.get_theme_options(*default_theme, *theme)
        return super().__call__(*args, **(theme_kwargs | kwargs))

    def set_theme(cls, name: str, options: Dict[str, Any], update: bool = False) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")
        if name is NoTheme:
            raise ValueError("Couldn't set 'NoTheme' as theme")
        if "theme" in options:
            raise ValueError("'theme' parameter must not be given in options")

        def check_options(func: Callable[..., Any]) -> None:
            sig: Signature = Signature.from_callable(func)
            parameters: Mapping[str, Parameter] = sig.parameters
            has_kwargs: bool = any(param.kind == Parameter.VAR_KEYWORD for param in parameters.values())

            for option in options:
                if option not in parameters:
                    if not has_kwargs:
                        raise KeyError(f"{func.__qualname__}: Unknown parameter {option!r}")
                    continue
                param: Parameter = parameters[option]
                if param.kind is not Parameter.KEYWORD_ONLY:
                    raise TypeError(f"{func.__qualname__}: {option!r} is a {param.kind.description} parameter")
                if param.default is Parameter.empty:
                    raise TypeError(f"{func.__qualname__}: {option!r} is a required argument")

        default_new_method: Callable[[Type[object]], Any] = object.__new__
        default_init_method: Callable[[object], None] = object.__init__
        new_method: Callable[..., Any] = getattr(cls, "__new__", default_new_method)
        init_method: Callable[..., None] = getattr(cls, "__init__", default_init_method)

        if new_method is default_new_method and init_method is default_init_method:
            raise TypeError(f"{cls.__name__} does not override default object constructors")
        if new_method is not default_new_method:
            check_options(new_method)
        if init_method is not default_init_method:
            check_options(init_method)

        theme_dict: Dict[str, Dict[str, Any]]

        if not name.startswith(_HIDDEN_THEME_PREFIX):
            if cls not in _THEMES:
                _THEMES[cls] = theme_dict = dict()
            else:
                theme_dict = _THEMES[cls]
        else:
            if cls not in _HIDDEN_THEMES:
                _HIDDEN_THEMES[cls] = theme_dict = dict()
            else:
                theme_dict = _HIDDEN_THEMES[cls]
        if name not in theme_dict or not update:
            theme_dict[name] = options
        else:
            theme_dict[name] |= options

    @overload
    def set_default_theme(cls, name: str, /, *names: str) -> None:
        ...

    @overload
    def set_default_theme(cls, name: None, /) -> None:
        ...

    def set_default_theme(cls, name: Union[str, None], /, *names: str) -> None:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes cannot set themes.")

        if name is None:
            if names:
                raise TypeError("Invalid arguments")
            _DEFAULT_THEME.pop(cls, None)
            return
        for theme in [name, *names]:
            if theme is NoTheme:
                raise ValueError("Couldn't set 'NoTheme' as default theme")
            default_theme: Dict[type, Set[str]] = (
                _DEFAULT_THEME if not theme.startswith(_HIDDEN_THEME_PREFIX) else _HIDDEN_DEFAULT_THEME
            )
            if cls not in default_theme:
                default_theme[cls] = set()
            default_theme[cls].add(theme)

    def get_theme_options(cls, *themes: str) -> Dict[str, Any]:
        if cls.is_abstract_theme_class():
            raise TypeError("Abstract theme classes does not have themes.")

        theme_kwargs: Dict[str, Any] = dict()

        def get_theme_options(cls: type, theme: str) -> None:
            nonlocal theme_kwargs
            theme_dict: _ClassThemeDict = _HIDDEN_THEMES if theme.startswith(_HIDDEN_THEME_PREFIX) else _THEMES
            try:
                theme_kwargs |= theme_dict[cls][theme]
            except KeyError:
                pass

        for t in themes:
            for parent in reversed(list(cls.__get_all_parent_class(cls, do_not_search_for=_CLASSES_NOT_USING_PARENT_THEMES))):
                get_theme_options(parent, t)
            get_theme_options(cls, t)
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
    def __get_all_parent_class(cls: MetaThemedObject, do_not_search_for: Set[type]) -> Iterator[MetaThemedObject]:
        if not isinstance(cls, MetaThemedObject) or cls in do_not_search_for or cls.is_abstract_theme_class():
            return
        for base in (*cls.__bases__, *cls.__virtual_themed_class_bases__):
            if not isinstance(base, MetaThemedObject) or base.is_abstract_theme_class():
                continue
            yield base
            yield from MetaThemedObject.__get_all_parent_class(base, do_not_search_for=do_not_search_for)


_ThemedObjectVar = TypeVar("_ThemedObjectVar", bound=MetaThemedObject)


def abstract_theme_class(cls: _ThemedObjectVar) -> _ThemedObjectVar:
    setattr(cls, "__is_abstract_theme_class__", True)
    return cls


@abstract_theme_class
class ThemedObject(metaclass=MetaThemedObject):
    def __init_subclass__(cls, /, *, use_parent_theme: bool = True, use_parent_default_theme: bool = True) -> None:
        super().__init_subclass__()
        if not use_parent_theme:
            _CLASSES_NOT_USING_PARENT_THEMES.add(cls)
            setattr(cls, "__no_parent_theme__", True)
            use_parent_default_theme = False
        if not use_parent_default_theme:
            _CLASSES_NOT_USING_PARENT_DEFAULT_THEMES.add(cls)
            setattr(cls, "__no_parent_default_theme__", True)
