# -*- coding: Utf-8 -*-

from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, NamedTuple

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# A namedtuple with the same attributes as sys.version_info
class MockVersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: str
    serial: int


def unload_module(module_name: str, include_submodules: bool, monkeypatch: MonkeyPatch) -> None:
    import sys

    monkeypatch.delitem(sys.modules, module_name)
    if include_submodules:
        pattern = r"{}(?:\.\w+)+".format(module_name)
        for module in filter(partial(re.match, pattern), tuple(sys.modules)):
            monkeypatch.delitem(sys.modules, module, raising=False)
