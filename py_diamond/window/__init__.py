# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond's window module"""

from __future__ import annotations

__all__ = [
    "AbstractAutoLayeredDrawableScene",
    "AbstractCursor",
    "AbstractLayeredScene",
    "AbstractWidget",
    "BoundFocus",
    "BuiltinEvent",
    "BuiltinEventType",
    "Clickable",
    "Clock",
    "Cursor",
    "Dialog",
    "Draggable",
    "DraggingContainer",
    "Event",
    "EventFactory",
    "EventFactoryError",
    "EventManager",
    "EventMeta",
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
    "ScreenshotEvent",
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
    "WindowExit",
    "WindowExposedEvent",
    "WindowFocusGainedEvent",
    "WindowFocusLostEvent",
    "WindowHiddenEvent",
    "WindowLeaveEvent",
    "WindowMaximizedEvent",
    "WindowMinimizedEvent",
    "WindowMovedEvent",
    "WindowRenderer",
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
from .clickable import *
from .clock import *
from .cursor import *
from .dialog import *
from .display import *
from .draggable import *
from .event import *
from .gui import *
from .keyboard import *
from .mouse import *
from .scene import *
from .time import *
from .widget import *
