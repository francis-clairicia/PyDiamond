# -*- coding: Utf-8 -*


from __future__ import annotations

from typing import Generator, TypeAlias, TypeVar

from pydiamond.system.utils.itertools import NoStopIteration, send_return

_T_co = TypeVar("_T_co", covariant=True)


DeserializerConsumer: TypeAlias = Generator[None, bytes, tuple[_T_co, bytes]]


class BaseTestStreamPacketIncrementalDeserializer:
    @staticmethod
    def deserialize_for_test(gen: Generator[None, bytes, tuple[_T_co, bytes]], chunk: bytes, /) -> tuple[_T_co, bytes]:
        try:
            return send_return(gen, chunk)
        except NoStopIteration:
            raise EOFError from None
