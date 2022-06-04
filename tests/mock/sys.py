# -*- coding: Utf-8 -*-

from __future__ import annotations

import re
from functools import partial
from typing import TYPE_CHECKING, Literal as L, NamedTuple

if TYPE_CHECKING:
    from pytest import MonkeyPatch


# A namedtuple with the same attributes as sys.version_info
class MockVersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: L["alpha", "beta", "candidate", "final"]
    serial: int

    def __repr__(self) -> str:
        return f"sys.version_info({', '.join(f'{k}={v!r}' for k, v in self._asdict().items())})"

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.micro}{'.' + self.releaselevel[0] + str(self.serial) if self.releaselevel != 'final' else ''}"


def unload_module(module_name: str, include_submodules: bool, monkeypatch: MonkeyPatch) -> None:
    import sys

    monkeypatch.delitem(sys.modules, module_name, raising=False)
    if include_submodules:
        pattern = r"{}(?:\.\w+)+".format(module_name)
        for module in filter(partial(re.match, pattern), tuple(sys.modules)):
            monkeypatch.delitem(sys.modules, module, raising=False)
