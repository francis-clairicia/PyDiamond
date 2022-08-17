# -*- coding: Utf-8 -*-

from __future__ import annotations

import re
from functools import partial
from importlib import import_module
from typing import TYPE_CHECKING, Literal, NamedTuple

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from pytest import MonkeyPatch
    from pytest_mock import MockerFixture


# A namedtuple with the same attributes as sys.version_info
class MockVersionInfo(NamedTuple):
    major: int
    minor: int
    micro: int
    releaselevel: Literal["alpha", "beta", "candidate", "final"]
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
        for module in filter(partial(re.fullmatch, pattern), tuple(sys.modules)):
            monkeypatch.delitem(sys.modules, module, raising=False)


def mock_module(module_name: str, mocker: MockerFixture) -> MagicMock:
    if module_name == "sys":
        raise ValueError("Do not mock 'sys', man")

    import sys

    pattern = r"{}(?:\.\w+)*".format(module_name)
    new_modules_dict: dict[str, MagicMock] = {
        module: mocker.MagicMock(spec=import_module(module))
        for module in filter(partial(re.fullmatch, pattern), tuple(sys.modules))
    }
    mocker.patch.dict(sys.modules, new_modules_dict)
    return new_modules_dict[module_name]
