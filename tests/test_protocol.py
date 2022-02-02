# -*- coding: Utf-8 -*

from typing import ClassVar

from cryptography.fernet import Fernet, InvalidToken

from py_diamond.network.protocol import JSONNetworkProtocol, PicklingNetworkProtocol, SecuredNetworkProtocol


def test_pickling_protocol() -> None:
    d: dict[str, list[tuple[int, float]]] = {"key": [(1, 5.2)]}

    serialized_d: bytes = PicklingNetworkProtocol.serialize(d)
    assert isinstance(serialized_d, bytes)
    assert PicklingNetworkProtocol.deserialize(serialized_d) == d


def test_json_protocol() -> None:
    assert JSONNetworkProtocol.SEPARATOR == b"\0"
    d: bytes = JSONNetworkProtocol.serialize({"key": [1, 2], "value": True})
    assert d == b'{"key": [1, 2], "value": true}'
    assert JSONNetworkProtocol.deserialize(d) == {"key": [1, 2], "value": True}


def test_secured_protocol() -> None:
    class SecuredJSONProtocol(JSONNetworkProtocol, SecuredNetworkProtocol):
        SECRET_KEY: ClassVar[str] = SecuredNetworkProtocol.generate_key()

    assert SecuredJSONProtocol.SEPARATOR == b"\r\n"
    d: bytes = SecuredJSONProtocol.serialize({"key": [1, 2], "value": True})
    assert d != b'{"key": [1, 2], "value": true}'
    assert Fernet(SecuredJSONProtocol.SECRET_KEY).decrypt(d) == b'{"key": [1, 2], "value": true}'

    from pytest import raises

    with raises(InvalidToken):
        Fernet(Fernet.generate_key()).decrypt(d)

    assert SecuredJSONProtocol.deserialize(d) == {"key": [1, 2], "value": True}
