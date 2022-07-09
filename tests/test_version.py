# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import Any

from py_diamond.version import VersionInfo

import pytest


@pytest.mark.unit
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
            pytest.param((1, 0, 0, "final", 0, ".dev1"), "1.0.0.dev1"),
            pytest.param((1, 0, 0, "final", 0, "+abcdef"), "1.0.0+abcdef"),
            pytest.param((1, 0, 0, "alpha", 5, ".dev1"), "1.0.0a5.dev1"),
            pytest.param((1, 0, 0, "alpha", 5, "+abcdef"), "1.0.0a5+abcdef"),
            pytest.param((1, 0, 0, "beta", 5, ".dev1"), "1.0.0b5.dev1"),
            pytest.param((1, 0, 0, "beta", 5, "+abcdef"), "1.0.0b5+abcdef"),
            pytest.param((1, 0, 0, "candidate", 5, ".dev1"), "1.0.0rc5.dev1"),
            pytest.param((1, 0, 0, "candidate", 5, "+abcdef"), "1.0.0rc5+abcdef"),
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
