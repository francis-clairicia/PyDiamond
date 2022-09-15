# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import Any

from pydiamond.version import VersionInfo

import pytest


class TestVersionInfo:
    @pytest.mark.parametrize(
        ["version_tuple", "expected_version"],
        [
            pytest.param((1, 0, 0), "1.0.0"),
            pytest.param((1, 0, 0, "final"), "1.0.0"),
            pytest.param((1, 0, 0, "final", 0), "1.0.0"),
            pytest.param((1, 0, 0, "final", 100), "1.0.0"),
            pytest.param((1, 0, 0, "alpha"), "1.0.0a0"),
            pytest.param((1, 0, 0, "alpha", 5), "1.0.0a5"),
            pytest.param((1, 0, 0, "beta"), "1.0.0b0"),
            pytest.param((1, 0, 0, "beta", 5), "1.0.0b5"),
            pytest.param((1, 0, 0, "candidate"), "1.0.0rc0"),
            pytest.param((1, 0, 0, "candidate", 5), "1.0.0rc5"),
            pytest.param((1, 0, 0, ""), "1.0.0.dev0"),
            pytest.param((1, 0, 0, "", 5), "1.0.0.dev5"),
        ],
        ids=str,
    )
    def test__str__returns_the_right_version_identifier(self, version_tuple: tuple[Any, ...], expected_version: str) -> None:
        # Arrange
        version_info = VersionInfo(*version_tuple)

        # Act
        version_str = str(version_info)

        # Assert
        assert version_str == expected_version

    @pytest.mark.parametrize(
        ["version", "expected_version_tuple"],
        [
            pytest.param("1.0.0", (1, 0, 0, "final", 0)),
            pytest.param("1.0.0a0", (1, 0, 0, "alpha", 0)),
            pytest.param("1.0.0a5", (1, 0, 0, "alpha", 5)),
            pytest.param("1.0.0b0", (1, 0, 0, "beta", 0)),
            pytest.param("1.0.0b5", (1, 0, 0, "beta", 5)),
            pytest.param("1.0.0rc0", (1, 0, 0, "candidate", 0)),
            pytest.param("1.0.0rc5", (1, 0, 0, "candidate", 5)),
            pytest.param("1.0.0.dev0", (1, 0, 0, "", 0)),
            pytest.param("1.0.0.dev5", (1, 0, 0, "", 5)),
        ],
        ids=str,
    )
    def test__from_string__returns_the_right_version_info(self, version: str, expected_version_tuple: tuple[Any, ...]) -> None:
        # Arrange

        # Act
        version_info = VersionInfo.from_string(version)

        # Assert
        assert version_info == expected_version_tuple

    @pytest.mark.parametrize(
        "version",
        [
            "1.0",
            "1.0.",
            "a.b.c",
            "1.0.0.a0",
            "1.0.0.b0",
            "1.0.0.rc0",
            "1.0.0-a0",
            "1.0.0-b0",
            "1.0.0-rc0",
            "1.0.0.a",
            "1.0.0.b",
            "1.0.0.rc",
            "1.0.0.dev",
            "1.0.0-dev1",
        ],
        ids=str,
    )
    def test__from_string__invalid(self, version: str) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(ValueError, match=r"Invalid version"):
            _ = VersionInfo.from_string(version)

    def test__version_info__rich_comparison(self) -> None:
        # Arrange
        from random import Random

        random = Random(42)

        expected_release_order = [
            "1.0.0.dev0",
            "1.0.0.dev1",
            "1.0.0.dev2",
            "1.0.0.dev10",
            "1.0.0.dev100",
            "1.0.0a0",
            "1.0.0a1",
            "1.0.0a2",
            "1.0.0a10",
            "1.0.0a100",
            "1.0.0b0",
            "1.0.0b1",
            "1.0.0b2",
            "1.0.0b10",
            "1.0.0b100",
            "1.0.0rc0",
            "1.0.0rc1",
            "1.0.0rc2",
            "1.0.0rc10",
            "1.0.0rc100",
            "1.0.0",  # Final release
            "1.0.1.dev0",
            "1.0.1",
            "1.0.2",
            "1.0.10",
            "1.1.0.dev0",
            "1.1.0",
            "1.2.0",
            "1.10.0",
            "2.0.0a2",
            "2.0.0rc5",
            "2.0.0",
            "10.0.0",
        ]
        release_order = list(expected_release_order)
        random.shuffle(release_order)
        assert release_order != expected_release_order

        # Act
        release_order.sort(key=VersionInfo.from_string)

        # Assert
        assert release_order == expected_release_order
