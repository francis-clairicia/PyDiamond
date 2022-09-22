# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = ["GenericNetworkProtocolWrapper"]

from typing import Any, Generic, TypeVar

from ..abc import NetworkProtocol

_ST_contra = TypeVar("_ST_contra", contravariant=True)
_DT_co = TypeVar("_DT_co", covariant=True)


class GenericNetworkProtocolWrapper(NetworkProtocol[_ST_contra, _DT_co], Generic[_ST_contra, _DT_co]):
    def __init__(self, protocol: NetworkProtocol[_ST_contra, _DT_co], **kwargs: Any) -> None:
        self.__protocol: NetworkProtocol[_ST_contra, _DT_co] = protocol
        super().__init__(**kwargs)

    @property
    def protocol(self) -> NetworkProtocol[_ST_contra, _DT_co]:
        return self.__protocol
