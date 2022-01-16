# -*- coding: Utf-8 -*
# Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

__all__ = [
    "AbstractAutoLayeredScene",
    "AbstractLayeredScene",
    "BoundFocus",
    "BoundFocusProxy",
    "Clickable",
    "Clock",
    "Cursor",
    "CustomCursor",
    "Event",
    "EventFactory",
    "EventManager",
    "FocusableContainer",
    "GUIMainScene",
    "GUIScene",
    "HasFocusUpdate",
    "JoyAxisMotionEvent",
    "JoyBallMotionEvent",
    "JoyButtonDownEvent",
    "JoyButtonEventType",
    "JoyButtonUpEvent",
    "JoyDeviceAddedEvent",
    "JoyDeviceRemovedEvent",
    "JoyHatMotionEvent",
    "KeyDownEvent",
    "KeyEventType",
    "KeyUpEvent",
    "Keyboard",
    "LayeredMainScene",
    "LayeredScene",
    "MainScene",
    "MetaGUIMainScene",
    "MetaGUIScene",
    "MetaLayeredMainScene",
    "MetaLayeredScene",
    "MetaMainScene",
    "MetaScene",
    "Mouse",
    "MouseButtonDownEvent",
    "MouseButtonEventType",
    "MouseButtonUpEvent",
    "MouseEventType",
    "MouseMotionEvent",
    "MouseWheelEvent",
    "MusicEndEvent",
    "NoFocusSupportError",
    "Pressable",
    "ReturningSceneTransition",
    "Scene",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneWindow",
    "ScheduledFunction",
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
    "closed_namespace",
    "scheduled",
    "set_default_theme_namespace",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021, Francis Clairicia-Rose-Claire-Josephine"
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
from .cursor import Cursor, CustomCursor, SystemCursor
from .display import ScheduledFunction, Window, WindowCallback, WindowError, scheduled
from .event import (
    Event,
    EventFactory,
    EventManager,
    JoyAxisMotionEvent,
    JoyBallMotionEvent,
    JoyButtonDownEvent,
    JoyButtonEventType,
    JoyButtonUpEvent,
    JoyDeviceAddedEvent,
    JoyDeviceRemovedEvent,
    JoyHatMotionEvent,
    KeyDownEvent,
    KeyEventType,
    KeyUpEvent,
    MouseButtonDownEvent,
    MouseButtonEventType,
    MouseButtonUpEvent,
    MouseEventType,
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
    GUIMainScene,
    GUIScene,
    HasFocusUpdate,
    MetaGUIMainScene,
    MetaGUIScene,
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
    LayeredScene,
    MainScene,
    MetaLayeredMainScene,
    MetaLayeredScene,
    MetaMainScene,
    MetaScene,
    ReturningSceneTransition,
    Scene,
    SceneTransition,
    SceneTransitionCoroutine,
    SceneWindow,
    closed_namespace,
    set_default_theme_namespace,
)
from .time import Time
