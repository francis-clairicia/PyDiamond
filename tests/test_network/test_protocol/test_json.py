# -*- coding: Utf-8 -*-

from __future__ import annotations

from io import BytesIO
from typing import Any

from pydiamond.network.protocol.json import JSONPacketDeserializer, JSONPacketSerializer

import pytest

from .base import BaseTestStreamPacketIncrementalDeserializer, DeserializerConsumer

SERIALIZE_PARAMS: list[tuple[Any, bytes]] = [
    (5, b"5"),
    (-123, b"-123"),
    (1.3, b"1.3"),
    (1e5, b"100000.0"),
    (float("nan"), b"NaN"),
    (float("-inf"), b"-Infinity"),
    (float("+inf"), b"Infinity"),
    (True, b"true"),
    (False, b"false"),
    (None, b"null"),
    ("", b'""'),
    ("non-empty", b'"non-empty"'),
    ('non-empty with "', b'"non-empty with \\""'),
    ("non-empty with é", b'"non-empty with \xc3\xa9"'),  # Must handle unicode by default
    ([], b"[]"),
    ([1, 2, 3], b"[1,2,3]"),  # No whitespaces by default
    ({}, b"{}"),
    ({"k": "v", "k2": "v2"}, b'{"k":"v","k2":"v2"}'),  # No whitespaces by default
]

DESERIALIZE_PARAMS: list[tuple[bytes, Any]] = [
    (output, data) for data, output in SERIALIZE_PARAMS if isinstance(data, (str, list, dict))
] + [
    (
        b'[{"value": "a"}, {"value": 3.14}, {"value": true}, {"value": {"other": [Infinity]}}]',
        [{"value": "a"}, {"value": 3.14}, {"value": True}, {"value": {"other": [float("+inf")]}}],
    ),
    (
        b'"[{\\"value\\": \\"a\\"}, {\\"value\\": 3.14}, {\\"value\\": True}, {\\"value\\": {\\"other\\": [float(\\"nan\\")]}}]"',
        '[{"value": "a"}, {"value": 3.14}, {"value": True}, {"value": {"other": [float("nan")]}}]',
    ),
    (
        b'{"key": [{"key": "value", "key2": [4, 5, -Infinity]}], "other": null}',
        {"key": [{"key": "value", "key2": [4, 5, float("-inf")]}], "other": None},
    ),
    (
        b'{"{\\"key\\": [{\\"key\\": \\"value\\", \\"key2\\": [4, 5, -Infinity]}], \\"other\\": null}": 42}',
        {'{"key": [{"key": "value", "key2": [4, 5, -Infinity]}], "other": null}': 42},
    ),
]


class TestJSONPacketSerializer:
    @pytest.fixture
    @staticmethod
    def protocol() -> JSONPacketSerializer[Any]:
        return JSONPacketSerializer()

    @pytest.mark.parametrize(["data", "expected_output"], SERIALIZE_PARAMS)
    def test__serialize(self, protocol: JSONPacketSerializer[Any], data: Any, expected_output: bytes) -> None:
        # Arrange

        # Act
        output = protocol.serialize(data)

        # Assert
        assert isinstance(output, bytes)
        assert output == expected_output

    @pytest.mark.parametrize(["data", "expected_output"], SERIALIZE_PARAMS)
    def test__incremental_serialize(self, protocol: JSONPacketSerializer[Any], data: Any, expected_output: bytes) -> None:
        # Arrange

        # Act
        output = b"".join(protocol.incremental_serialize(data))

        # Assert
        assert isinstance(output, bytes)
        assert output == expected_output

    @pytest.mark.parametrize(["data", "expected_output"], SERIALIZE_PARAMS)
    def test__incremental_serialize_to(self, protocol: JSONPacketSerializer[Any], data: Any, expected_output: bytes) -> None:
        # Arrange
        file = BytesIO()

        # Act
        protocol.incremental_serialize_to(file, data)

        # Assert
        assert file.getvalue() == expected_output


class TestJSONPacketDeserializer(BaseTestStreamPacketIncrementalDeserializer):
    @pytest.fixture
    @staticmethod
    def protocol() -> JSONPacketDeserializer[Any]:
        return JSONPacketDeserializer()

    @pytest.fixture
    @staticmethod
    def consumer(protocol: JSONPacketDeserializer[Any]) -> DeserializerConsumer[Any]:
        consumer = protocol.incremental_deserialize()
        next(consumer)
        return consumer

    @pytest.mark.parametrize(["data", "expected_output"], DESERIALIZE_PARAMS)
    def test__deserialize(self, protocol: JSONPacketDeserializer[Any], data: bytes, expected_output: Any) -> None:
        # Arrange

        # Act
        output = protocol.deserialize(data)

        # Assert
        assert type(output) is type(expected_output)
        assert output == expected_output

    @pytest.mark.parametrize(["data", "expected_output"], DESERIALIZE_PARAMS)
    def test__incremental_deserialize__oneshot_valid_packet(
        self,
        consumer: DeserializerConsumer[Any],
        data: bytes,
        expected_output: Any,
    ) -> None:
        # Arrange

        # Act
        output, remainder = self.deserialize(consumer, data)

        # Assert
        assert not remainder
        assert type(output) is type(expected_output)
        assert output == expected_output

    @pytest.mark.parametrize(
        ["data", "expected_output", "expected_remainder"],
        [
            pytest.param(b'    "leading-whitespaces"', "leading-whitespaces", b""),
            pytest.param(b'"trailing-whitespaces"    ', "trailing-whitespaces", b"    "),  # Trailing whitespace will be ignored
        ],
        ids=repr,
    )
    def test__incremental_deserialize__whitespace_handling(
        self,
        consumer: DeserializerConsumer[Any],
        data: bytes,
        expected_output: Any,
        expected_remainder: bytes,
    ) -> None:
        # Arrange

        # Act
        output, remainder = self.deserialize(consumer, data)

        # Assert
        assert output == expected_output
        assert remainder == expected_remainder

    @pytest.mark.parametrize(["data", "expected_output"], DESERIALIZE_PARAMS)
    @pytest.mark.parametrize("expected_remainder", list(map(lambda v: v[0], DESERIALIZE_PARAMS)))
    def test__incremental_deserialize__chunk_with_remainder(
        self,
        consumer: DeserializerConsumer[Any],
        data: bytes,
        expected_output: Any,
        expected_remainder: bytes,
    ) -> None:
        # Arrange
        data += expected_remainder

        # Act
        output, remainder = self.deserialize(consumer, data)

        # Assert
        assert output == expected_output
        assert remainder == expected_remainder

    @pytest.mark.parametrize(["data", "expected_output"], DESERIALIZE_PARAMS)
    def test__incremental_deserialize__handle_partial_document(
        self,
        consumer: DeserializerConsumer[Any],
        data: bytes,
        expected_output: Any,
    ) -> None:
        # Arrange
        import struct

        bytes_sequence: tuple[bytes, ...] = struct.unpack(f"{len(data)}c", data)

        # Act
        for chunk in bytes_sequence[:-1]:
            with pytest.raises(EOFError):
                _ = self.deserialize(consumer, chunk)
        output, remainder = self.deserialize(consumer, bytes_sequence[-1])

        # Assert
        assert not remainder
        assert type(output) is type(expected_output)
        assert output == expected_output
