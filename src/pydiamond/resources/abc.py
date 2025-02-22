# Copyright (c) 2021-2025, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Resource abstract base classes module"""

from __future__ import annotations

__all__ = [
    "Resource",
    "ResourcesLocation",
]

from abc import ABCMeta, abstractmethod
from pathlib import Path
from typing import BinaryIO, ContextManager, Protocol, runtime_checkable


@runtime_checkable
class Resource(Protocol, metaclass=ABCMeta):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def as_file(self) -> ContextManager[Path]:
        raise NotImplementedError

    @abstractmethod
    def open(self) -> BinaryIO:
        raise NotImplementedError


@runtime_checkable
class ResourcesLocation(Protocol, metaclass=ABCMeta):
    @abstractmethod
    def get_resource(self, resource: str) -> Resource:
        raise NotImplementedError
