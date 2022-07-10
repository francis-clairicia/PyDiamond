# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond version declaration module"""

from __future__ import annotations

__all__ = ["VersionInfo", "version_info"]

import typing

from typing_extensions import assert_never


class VersionInfo(typing.NamedTuple):
    major: int
    minor: int
    patch: int
    releaselevel: typing.Literal["alpha", "beta", "candidate", "final"] = "final"
    serial: int = 0
    suffix: str = ""

    def __str__(self) -> str:
        releaselevel: str
        match self.releaselevel:
            case "alpha" | "beta":
                releaselevel = self.releaselevel[0]
            case "candidate":
                releaselevel = "rc"
            case "final":
                releaselevel = ""
            case _:
                assert_never(self.releaselevel)
        if releaselevel:
            releaselevel = f"{releaselevel}{self.serial}"
        return f"{self.major}.{self.minor}.{self.patch}{releaselevel}{self.suffix}"


version_info: typing.Final[VersionInfo] = VersionInfo(1, 0, 0, "alpha", 0, ".dev2")
