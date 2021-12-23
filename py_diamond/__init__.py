# -*- coding: Utf-8 -*

import os
import sys

############ Environment initialization ############
if sys.version_info[0:2] < (3, 9):
    raise ImportError("This framework must be ran with python >= 3.9 (actual={}.{}.{})".format(*sys.version_info[0:3]))

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")  # Must be set before importing pygame

############ Cleanup ############
del os, sys
