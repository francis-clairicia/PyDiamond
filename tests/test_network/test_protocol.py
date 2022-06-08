# -*- coding: Utf-8 -*-

from __future__ import annotations

from typing import ClassVar

from py_diamond.network.protocol import JSONNetworkProtocol, PicklingNetworkProtocol, SecuredNetworkProtocol

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
    class SecuredJSONProtocol(SecuredNetworkProtocol):
        SECRET_KEY: ClassVar[str] = SecuredNetworkProtocol.generate_key()

        def get_unsafe_protocol(self) -> JSONNetworkProtocol:
            return JSONNetworkProtocol()

    protocol = SecuredJSONProtocol()
    d: bytes = protocol.serialize({"key": [1, 2], "value": True})
    assert d != b'{"key":[1,2],"value":true}'
    assert protocol.fernet.decrypt(d) == b'{"key":[1,2],"value":true}'
    assert Fernet(SecuredJSONProtocol.SECRET_KEY).decrypt(d) == b'{"key":[1,2],"value":true}'

    with pytest.raises(InvalidToken):
        Fernet(Fernet.generate_key()).decrypt(d)

    assert protocol.deserialize(d) == {"key": [1, 2], "value": True}


def test_secured_protocol_secret_key_from_env() -> None:
    random_key: str = SecuredNetworkProtocol.generate_key()

    from os import environ

    environ["SECRET_KEY"] = random_key

    try:

        class SecuredJSONProtocol(SecuredNetworkProtocol):
            def get_unsafe_protocol(self) -> JSONNetworkProtocol:
                return JSONNetworkProtocol()

    finally:
        del environ["SECRET_KEY"]

    assert SecuredJSONProtocol.SECRET_KEY == random_key


def test_secured_protocol_secret_key_from_env_custom_var() -> None:
    random_key: str = SecuredNetworkProtocol.generate_key()

    from os import environ

    environ["MY_SUPER_SECRET_KEY"] = random_key

    try:

        class SecuredJSONProtocol(SecuredNetworkProtocol, secret_key_var="MY_SUPER_SECRET_KEY"):
            def get_unsafe_protocol(self) -> JSONNetworkProtocol:
                return JSONNetworkProtocol()

    finally:
        del environ["MY_SUPER_SECRET_KEY"]

    assert SecuredJSONProtocol.SECRET_KEY == random_key
