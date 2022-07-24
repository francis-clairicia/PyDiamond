# -*- coding: Utf-8 -*-

from __future__ import annotations

import math
from io import BytesIO
from typing import Any

from py_diamond.network.protocol.json import JSONPacketDeserializer, JSONPacketSerializer

import pytest

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
    ("non-empty with é", b'"non-empty with \xc3\xa9"'),  # Must handle unicode by default
    ([], b"[]"),
    ([1, 2, 3], b"[1,2,3]"),  # No whitespaces by default
    ({}, b"{}"),
    ({"k": "v", "k2": "v2"}, b'{"k":"v","k2":"v2"}'),  # No whitespaces by default
]

DESERIALIZE_PARAMS: list[tuple[bytes, Any]] = [(output, data) for data, output in SERIALIZE_PARAMS]


@pytest.mark.unit
class TestJSONPacketSerializer:
    @pytest.fixture
    @staticmethod
    def protocol() -> JSONPacketSerializer[Any]:
        return JSONPacketSerializer()

    @pytest.mark.parametrize(["data", "expected_output"], SERIALIZE_PARAMS, ids=repr)
    def test__serialize(self, protocol: JSONPacketSerializer[Any], data: Any, expected_output: bytes) -> None:
        # Arrange

        # Act
        output = protocol.serialize(data)

        # Assert
        assert isinstance(output, bytes)
        assert output == expected_output

    @pytest.mark.parametrize(["data", "expected_output"], SERIALIZE_PARAMS, ids=repr)
    def test__incremental_serialize(self, protocol: JSONPacketSerializer[Any], data: Any, expected_output: bytes) -> None:
        # Arrange

        # Act
        output = b"".join(protocol.incremental_serialize(data))

        # Assert
        assert isinstance(output, bytes)
        assert output == expected_output

    @pytest.mark.parametrize(["data", "expected_output"], SERIALIZE_PARAMS, ids=repr)
    def test__incremental_serialize_to(self, protocol: JSONPacketSerializer[Any], data: Any, expected_output: bytes) -> None:
        # Arrange
        file = BytesIO()

        # Act
        protocol.incremental_serialize_to(file, data)

        # Assert
        assert file.getvalue() == expected_output


@pytest.mark.unit
class TestJSONPacketDeserializer:
    @pytest.fixture
    @staticmethod
    def protocol() -> JSONPacketDeserializer[Any]:
        return JSONPacketDeserializer()

    @pytest.mark.parametrize(["data", "expected_output"], DESERIALIZE_PARAMS, ids=repr)
    def test__deserialize(self, protocol: JSONPacketDeserializer[Any], data: bytes, expected_output: Any) -> None:
        # Arrange

        # Act
        output = protocol.deserialize(data)

        # Assert
        assert type(output) is type(expected_output)
        match data:
            case b"NaN":
                assert math.isnan(output)
            case b"Infinity" | b"-Infinity":
                assert math.isinf(output)
                assert output == expected_output
            case _:
                assert output == expected_output

    @pytest.mark.parametrize(["data", "expected_output"], DESERIALIZE_PARAMS, ids=repr)
    def test__incremental_deserialize(self, protocol: JSONPacketDeserializer[Any], data: bytes, expected_output: Any) -> None:
        # Arrange
        consumer = protocol.incremental_deserialize()
        next(consumer)

        # Act
        with pytest.raises(StopIteration) as exc:
            consumer.send(data)

        output: Any
        remainder: bytes
        output, remainder = exc.value.value

        # Assert
        assert not remainder
        assert type(output) is type(expected_output)
        match data:
            case b"NaN":
                assert math.isnan(output)
            case b"Infinity" | b"-Infinity":
                assert math.isinf(output)
                assert output == expected_output
            case _:
                assert output == expected_output

    @pytest.mark.parametrize(
        ["document", "expected_output"],
        [
            # Test with basic values to avoid regression
            pytest.param("55", (55, 2)),
            pytest.param("55.3", (55.3, 4)),
            pytest.param('""', ("", 2)),
            pytest.param("{}", ({}, 2)),
            pytest.param("[]", ([], 2)),
            pytest.param('"string"', ("string", 8)),
            # Whitespace handling
            pytest.param('    "string"', ("string", 12)),
            pytest.param('"string"    ', ("string", 12)),
            # Ignore successive strings
            pytest.param('"a""b"', ("a", 3)),
            # Ignore successive arrays
            pytest.param("[1,2,3][4,5,6]", ([1, 2, 3], 7)),
            # Ignore successive objects
            pytest.param('{"a":1}{"b":2}', ({"a": 1}, 7)),
        ],
        ids=repr,
    )
    def test__raw_decode__cases_which_must_work(
        self,
        protocol: JSONPacketDeserializer[Any],
        document: str,
        expected_output: tuple[Any, int],
    ) -> None:
        # Arrange

        # Act
        output = protocol.raw_decode(document)

        # Assert
        assert output == expected_output

    @pytest.mark.parametrize(
        "document",
        [
            "{",
            "[",
            '"',
            '"\\"',  # Escaped quote, so this would fail too
            "[{}",
            '"[]',
            '{"a":{"b":[5,3]}',
            '{"a":{"}":[5,3]}',
            '["", ',
            '["", "]"',
        ],
        ids=repr,
    )
    def test__raw_decode__handle_partial_document(self, protocol: JSONPacketDeserializer[Any], document: str) -> None:
        # Arrange

        # Act & Assert
        with pytest.raises(EOFError):
            protocol.raw_decode(document)
