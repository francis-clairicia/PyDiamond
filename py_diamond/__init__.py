# -*- coding: Utf-8 -*

import os
import sys

############ Environment initialization ############
if sys.version_info[0:2] < (3, 9):
    raise ImportError("This framework must be ran with python >= 3.9 (actual={}.{}.{})".format(*sys.version_info[0:3]))

PYGAME_HIDE_SUPPORT_PROMPT: str = os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # Must be set before importing pygame
if PYGAME_HIDE_SUPPORT_PROMPT not in ("0", "1"):
    raise ValueError("Invalid value for 'PYGAME_HIDE_SUPPORT_PROMPT' environment variable")
if PYGAME_HIDE_SUPPORT_PROMPT == "0":
    os.environ.pop("PYGAME_HIDE_SUPPORT_PROMPT")

############ Cleanup ############
del os, sys
