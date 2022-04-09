# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

__all__ = [
    "AbstractAutoLayeredScene",
    "AbstractCursor",
    "AbstractLayeredScene",
    "BoundFocus",
    "BoundFocusProxy",
    "Clickable",
    "Clock",
    "Cursor",
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventTypeNotRegisteredError",
    "FocusableContainer",
    "GUIAutoLayeredMainScene",
    "GUIAutoLayeredScene",
    "GUIMainScene",
    "GUIMainSceneMeta",
    "GUIScene",
    "GUISceneMeta",
    "JoyAxisMotionEvent",
    "JoyBallMotionEvent",
    "JoyButtonDownEvent",
    "JoyButtonEvent",
    "JoyButtonUpEvent",
    "JoyDeviceAddedEvent",
    "JoyDeviceRemovedEvent",
    "JoyHatMotionEvent",
    "KeyDownEvent",
    "KeyEvent",
    "KeyUpEvent",
    "Keyboard",
    "LayeredMainScene",
    "LayeredMainSceneMeta",
    "LayeredScene",
    "LayeredSceneMeta",
    "MainScene",
    "MainSceneMeta",
    "Mouse",
    "MouseButtonDownEvent",
    "MouseButtonEvent",
    "MouseButtonUpEvent",
    "MouseEvent",
    "MouseMotionEvent",
    "MouseWheelEvent",
    "MusicEndEvent",
    "NoFocusSupportError",
    "Pressable",
    "ReturningSceneTransition",
    "Scene",
    "SceneMeta",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneWindow",
    "SupportsFocus",
    "SystemCursor",
    "TextEditingEvent",
    "TextEvent",
    "TextInputEvent",
    "Time",
    "UnknownEventTypeError",
    "UserEvent",
    "Window",
    "WindowCallback",
    "WindowEnterEvent",
    "WindowError",
    "WindowExposedEvent",
    "WindowFocusGainedEvent",
    "WindowFocusLostEvent",
    "WindowHiddenEvent",
    "WindowLeaveEvent",
    "WindowMaximizedEvent",
    "WindowMinimizedEvent",
    "WindowMovedEvent",
    "WindowResizedEvent",
    "WindowRestoredEvent",
    "WindowShownEvent",
    "WindowSizeChangedEvent",
    "WindowTakeFocusEvent",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

import os

import pygame

############ pygame.display initialization ############
if pygame.version.vernum < (2, 1, 2):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.2'")

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'")

os.environ.setdefault("PYGAME_BLEND_ALPHA_SDL2", "1")
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

############ Cleanup ############
del os, pygame

############ Package initialization ############
from .clickable import Clickable
from .clock import Clock
from .cursor import AbstractCursor, Cursor, SystemCursor
from .display import Window, WindowCallback, WindowError
from .event import (
    Event,
    EventFactory,
    EventFactoryError,
    EventManager,
    EventTypeNotRegisteredError,
    JoyAxisMotionEvent,
    JoyBallMotionEvent,
    JoyButtonDownEvent,
    JoyButtonEvent,
    JoyButtonUpEvent,
    JoyDeviceAddedEvent,
    JoyDeviceRemovedEvent,
    JoyHatMotionEvent,
    KeyDownEvent,
    KeyEvent,
    KeyUpEvent,
    MouseButtonDownEvent,
    MouseButtonEvent,
    MouseButtonUpEvent,
    MouseEvent,
    MouseMotionEvent,
    MouseWheelEvent,
    MusicEndEvent,
    TextEditingEvent,
    TextEvent,
    TextInputEvent,
    UnknownEventTypeError,
    UserEvent,
    WindowEnterEvent,
    WindowExposedEvent,
    WindowFocusGainedEvent,
    WindowFocusLostEvent,
    WindowHiddenEvent,
    WindowLeaveEvent,
    WindowMaximizedEvent,
    WindowMinimizedEvent,
    WindowMovedEvent,
    WindowResizedEvent,
    WindowRestoredEvent,
    WindowShownEvent,
    WindowSizeChangedEvent,
    WindowTakeFocusEvent,
)
from .gui import (
    BoundFocus,
    BoundFocusProxy,
    FocusableContainer,
    GUIAutoLayeredMainScene,
    GUIAutoLayeredScene,
    GUIMainScene,
    GUIMainSceneMeta,
    GUIScene,
    GUISceneMeta,
    NoFocusSupportError,
    SupportsFocus,
)
from .keyboard import Keyboard
from .mouse import Mouse
from .pressable import Pressable
from .scene import (
    AbstractAutoLayeredScene,
    AbstractLayeredScene,
    LayeredMainScene,
    LayeredMainSceneMeta,
    LayeredScene,
    LayeredSceneMeta,
    MainScene,
    MainSceneMeta,
    ReturningSceneTransition,
    Scene,
    SceneMeta,
    SceneTransition,
    SceneTransitionCoroutine,
    SceneWindow,
)
from .time import Time
