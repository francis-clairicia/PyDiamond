# -*- coding: Utf-8 -*-

from __future__ import annotations

__all__ = ["REQUIREMENTS_FILES", "REQUIREMENTS_FILES_EXTRA_REQUIRES", "REQUIREMENTS_FILES_INPUT"]

from types import MappingProxyType

REQUIREMENTS_FILES_INPUT: MappingProxyType[str, str] = MappingProxyType(  # NOTE: Only use UNIX style paths
    {
        "requirements.txt": "pyproject.toml",
        "requirements-dev.txt": "requirements/requirements-dev.in",
        "requirements-test.txt": "requirements/requirements-test.in",
    }
)

REQUIREMENTS_FILES_EXTRA_REQUIRES: MappingProxyType[str, tuple[str, ...] | None] = MappingProxyType({})

REQUIREMENTS_FILES: tuple[str, ...] = tuple(REQUIREMENTS_FILES_INPUT.keys())
