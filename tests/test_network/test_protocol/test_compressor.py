# -*- coding: Utf-8 -*-

from __future__ import annotations

import json
from typing import Any, Callable

from pydiamond.network.protocol.json import JSONNetworkProtocol
from pydiamond.network.protocol.wrapper.compressor import (
    AbstractCompressorNetworkProtocol,
    BZ2CompressorNetworkProtocol,
    ZlibCompressorNetworkProtocol,
)

import pytest

from .base import BaseTestStreamPacketIncrementalDeserializer, DeserializerConsumer


@pytest.fixture
def json_data() -> Any:
    return {
        "data1": True,
        "data2": [
            {
                "user": "something",
                "password": "other_thing",
            }
        ],
        "data3": {
            "value": [1, 2, 3, 4],
            "salt": "azerty",
        },
        "data4": 3.14,
        "data5": [
            float("+inf"),
            float("-inf"),
            None,
        ],
    }


@pytest.fixture(scope="module")
def json_encoder() -> json.JSONEncoder:
    return json.JSONEncoder(ensure_ascii=False, separators=(",", ":"))


@pytest.fixture(params=[BZ2CompressorNetworkProtocol, ZlibCompressorNetworkProtocol])
def compressor_protocol(request: Any, json_encoder: json.JSONEncoder) -> AbstractCompressorNetworkProtocol[Any, Any]:
    factory: Callable[[Any], AbstractCompressorNetworkProtocol[Any, Any]] = request.param
    return factory(JSONNetworkProtocol(encoder=json_encoder))


@pytest.fixture
def json_data_bytes(json_encoder: json.JSONEncoder, json_data: Any) -> bytes:
    return json_encoder.encode(json_data).encode("utf-8")


@pytest.mark.functional
def test__serialize_deserialize__works(
    compressor_protocol: AbstractCompressorNetworkProtocol[Any, Any],
    json_data: Any,
    json_data_bytes: bytes,
) -> None:
    # Arrange

    # Act
    serialized_data = compressor_protocol.serialize(json_data)
    deserialized_data = compressor_protocol.deserialize(serialized_data)

    # Assert
    assert serialized_data != json_data_bytes
    assert len(serialized_data) < len(json_data_bytes)
    assert deserialized_data == json_data


class TestIncrementalDeserialize(BaseTestStreamPacketIncrementalDeserializer):
    def test__incremental_deserialize__one_shot_chunk(
        self,
        compressor_protocol: AbstractCompressorNetworkProtocol[Any, Any],
        json_data: Any,
    ) -> None:
        # Arrange
        deserializer_consumer: DeserializerConsumer[Any] = compressor_protocol.incremental_deserialize()
        next(deserializer_consumer)

        # Act
        serialized_data = b"".join(compressor_protocol.incremental_serialize(json_data))
        deserialized_data, remaining = self.deserialize_for_test(deserializer_consumer, serialized_data)

        # Assert
        assert serialized_data == compressor_protocol.serialize(json_data)
        assert deserialized_data == json_data
        assert isinstance(remaining, bytes)
        assert not remaining

    def test__incremental_deserialize__handle_partial_document(
        self,
        compressor_protocol: AbstractCompressorNetworkProtocol[Any, Any],
        json_data: Any,
    ) -> None:
        # Arrange
        import struct

        deserializer_consumer: DeserializerConsumer[Any] = compressor_protocol.incremental_deserialize()
        next(deserializer_consumer)

        serialized_data = b"".join(compressor_protocol.incremental_serialize(json_data))
        bytes_sequence: tuple[bytes, ...] = struct.unpack(f"{len(serialized_data)}c", serialized_data)

        # Act
        for chunk in bytes_sequence[:-1]:
            with pytest.raises(EOFError):
                _ = self.deserialize_for_test(deserializer_consumer, chunk)
        output, remainder = self.deserialize_for_test(deserializer_consumer, bytes_sequence[-1])

        # Assert
        assert not remainder
        assert output == json_data
