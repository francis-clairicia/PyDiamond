# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import Any

from pydiamond.network.protocol import EncryptorNetworkProtocol, JSONNetworkProtocol, PickleNetworkProtocol

import pytest
from cryptography.fernet import Fernet, InvalidToken


def test_pickling_protocol() -> None:
    d: dict[str, list[tuple[int, float]]] = {"key": [(1, 5.2)]}
    protocol: PickleNetworkProtocol[Any, Any] = PickleNetworkProtocol()

    serialized_d: bytes = protocol.serialize(d)
    assert isinstance(serialized_d, bytes)
    assert protocol.deserialize(serialized_d) == d


def test_json_protocol() -> None:
    protocol: JSONNetworkProtocol[Any, Any] = JSONNetworkProtocol()
    d: bytes = protocol.serialize({"key": [1, 2], "value": True})
    assert d == b'{"key":[1,2],"value":true}'
    assert protocol.deserialize(d) == {"key": [1, 2], "value": True}


def test_secured_protocol() -> None:
    key: bytes = Fernet.generate_key()
    protocol: EncryptorNetworkProtocol[Any, Any, JSONNetworkProtocol[Any, Any]] = EncryptorNetworkProtocol(
        JSONNetworkProtocol(), key
    )
    d: bytes = protocol.serialize({"key": [1, 2], "value": True})
    assert d != b'{"key":[1,2],"value":true}'
    assert protocol.key.decrypt(d) == b'{"key":[1,2],"value":true}'
    assert Fernet(key).decrypt(d) == b'{"key":[1,2],"value":true}'

    with pytest.raises(InvalidToken):
        Fernet(Fernet.generate_key()).decrypt(d)

    assert protocol.deserialize(d) == {"key": [1, 2], "value": True}
