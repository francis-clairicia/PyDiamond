# -*- coding: Utf-8 -*

from typing import ClassVar

import pytest
from cryptography.fernet import Fernet, InvalidToken

from py_diamond.network.protocol import JSONNetworkProtocol, PicklingNetworkProtocol, SecuredNetworkProtocol


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
    class SecuredJSONProtocol(JSONNetworkProtocol, SecuredNetworkProtocol):
        SECRET_KEY: ClassVar[str] = SecuredNetworkProtocol.generate_key()

    protocol = SecuredJSONProtocol()
    d: bytes = protocol.serialize({"key": [1, 2], "value": True})
    assert d != b'{"key":[1,2],"value":true}'
    assert protocol.fernet.decrypt(d) == b'{"key":[1,2],"value":true}'
    assert Fernet(SecuredJSONProtocol.SECRET_KEY).decrypt(d) == b'{"key":[1,2],"value":true}'

    with pytest.raises(InvalidToken):
        Fernet(Fernet.generate_key()).decrypt(d)

    assert protocol.deserialize(d) == {"key": [1, 2], "value": True}
