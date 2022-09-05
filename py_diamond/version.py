# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""PyDiamond version declaration module"""

from __future__ import annotations

__all__ = ["VersionInfo", "version_info"]

import typing

from typing_extensions import assert_never

from . import __version__


class VersionInfo(typing.NamedTuple):
    major: int
    minor: int
    patch: int
    releaselevel: typing.Literal["", "alpha", "beta", "candidate", "final"] = "final"  # Empty string means 'in development'
    serial: int = 0

    def __str__(self) -> str:
        releaselevel: str
        match self.releaselevel:
            case "":
                releaselevel = ".dev"
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
        return f"{self.major}.{self.minor}.{self.patch}{releaselevel}"

    @staticmethod
    def from_string(version: str) -> VersionInfo:
        import re

        pattern = r"^(?P<major>\d+)\.(?P<minor>\d+)\.(?P<patch>\d+)(?:(?P<releaselevel>a|b|rc|\.dev)(?P<serial>\d+))?$"

        match = re.match(pattern, version)
        if match is None:
            raise ValueError("Invalid version")

        major, minor, patch = map(int, match.group("major", "minor", "patch"))

        releaselevel: typing.Literal["", "alpha", "beta", "candidate", "final"]
        match match["releaselevel"]:
            case ".dev":
                releaselevel = ""
            case "a":
                releaselevel = "alpha"
            case "b":
                releaselevel = "beta"
            case "rc":
                releaselevel = "candidate"
            case None:
                releaselevel = "final"
            case _:  # Should not happen
                raise AssertionError("Invalid regex pattern")

        serial: int = int(match["serial"]) if match["serial"] else 0

        return VersionInfo(major, minor, patch, releaselevel, serial)


version_info: typing.Final[VersionInfo] = VersionInfo.from_string(__version__)
