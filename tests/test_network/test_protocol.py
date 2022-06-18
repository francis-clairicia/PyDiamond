# -*- coding: Utf-8 -*-

from __future__ import annotations

from py_diamond.network.protocol import EncryptorProtocol, JSONNetworkProtocol, PicklingNetworkProtocol

import pytest
from cryptography.fernet import Fernet, InvalidToken


def test_pickling_protocol() -> None:
    d: dict[str, list[tuple[int, float]]] = {"key": [(1, 5.2)]}
    protocol = PicklingNetworkProtocol()

    serialized_d: bytes = protocol.serialize(d)
    assert isinstance(serialized_d, bytes)
    assert protocol.deserialize(serialized_d) == d


def test_json_protocol() -> None:
    protocol = JSONNetworkProtocol()
    d: bytes = protocol.serialize({"key": [1, 2], "value": True})
    assert d == b'{"key":[1,2],"value":true}'
    assert protocol.deserialize(d) == {"key": [1, 2], "value": True}


def test_secured_protocol() -> None:
    key: str = EncryptorProtocol.generate_key()
    protocol = EncryptorProtocol(JSONNetworkProtocol(), key)
    d: bytes = protocol.serialize({"key": [1, 2], "value": True})
    assert d != b'{"key":[1,2],"value":true}'
    assert protocol.key.decrypt(d) == b'{"key":[1,2],"value":true}'
    assert Fernet(key).decrypt(d) == b'{"key":[1,2],"value":true}'

    with pytest.raises(InvalidToken):
        Fernet(Fernet.generate_key()).decrypt(d)

    assert protocol.deserialize(d) == {"key": [1, 2], "value": True}
