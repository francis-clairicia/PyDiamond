# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

from __future__ import annotations

__all__ = [
    "AbstractAutoLayeredDrawableScene",
    "AbstractCursor",
    "AbstractLayeredMainScene",
    "AbstractLayeredScene",
    "AbstractWidget",
    "BoundFocus",
    "BoundFocusProxy",
    "BuiltinEvent",
    "Clickable",
    "Clock",
    "Cursor",
    "Dialog",
    "DialogMeta",
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventType",
    "FocusableContainer",
    "GUIScene",
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
    "LayeredMainSceneMeta",
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
    "PopupDialog",
    "RenderedLayeredScene",
    "ReturningSceneTransition",
    "ReturningSceneTransitionProtocol",
    "Scene",
    "SceneMeta",
    "SceneTransition",
    "SceneTransitionCoroutine",
    "SceneTransitionProtocol",
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

import os

import pygame

############ pygame.display initialization ############
if pygame.version.vernum < (2, 1, 2):
    raise ImportError(f"Your pygame version is too old: {pygame.version.ver!r} < '2.1.2'", name=__name__, path=__file__)

if pygame.version.SDL < (2, 0, 16):
    raise ImportError(f"Your SDL version is too old: {str(pygame.version.SDL)!r} < '2.0.16'", name=__name__, path=__file__)

os.environ.setdefault("PYGAME_BLEND_ALPHA_SDL2", "1")
os.environ.setdefault("SDL_VIDEO_CENTERED", "1")

############ Cleanup ############
del os, pygame

############ Package initialization ############
from .clickable import Clickable
from .clock import Clock
from .cursor import AbstractCursor, Cursor, SystemCursor
from .dialog import Dialog, DialogMeta, PopupDialog
from .display import Window, WindowCallback, WindowError
from .event import (
    BuiltinEvent,
    Event,
    EventFactory,
    EventFactoryError,
    EventManager,
    EventType,
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
from .gui import BoundFocus, BoundFocusProxy, FocusableContainer, GUIScene, NoFocusSupportError, SupportsFocus
from .keyboard import Keyboard
from .mouse import Mouse
from .scene import (
    AbstractAutoLayeredDrawableScene,
    AbstractLayeredMainScene,
    AbstractLayeredScene,
    LayeredMainSceneMeta,
    LayeredSceneMeta,
    MainScene,
    MainSceneMeta,
    RenderedLayeredScene,
    ReturningSceneTransition,
    ReturningSceneTransitionProtocol,
    Scene,
    SceneMeta,
    SceneTransition,
    SceneTransitionCoroutine,
    SceneTransitionProtocol,
    SceneWindow,
)
from .time import Time
from .widget import AbstractWidget
