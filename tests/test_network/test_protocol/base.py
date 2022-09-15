# -*- coding: Utf-8 -*


from __future__ import annotations

from typing import Generator, TypeAlias, TypeVar

from pydiamond.system.utils.itertools import send_return

_T_co = TypeVar("_T_co", covariant=True)


DeserializerConsumer: TypeAlias = Generator[None, bytes, tuple[_T_co, bytes]]


class BaseTestStreamPacketIncrementalDeserializer:
    @staticmethod
    def deserialize(gen: Generator[None, bytes, tuple[_T_co, bytes]], chunk: bytes, /) -> tuple[_T_co, bytes]:
        try:
            return send_return(gen, chunk)
        except StopIteration:
            raise EOFError from None
