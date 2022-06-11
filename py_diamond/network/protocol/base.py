# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkProtocol",
    "AutoParsedStreamNetworkProtocol",
    "SecuredNetworkProtocol",
    "SecuredNetworkProtocolMeta",
    "ValidationError",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from functools import cached_property
from io import SEEK_CUR, BufferedReader
from struct import Struct, error as StructError
from threading import RLock
from typing import TYPE_CHECKING, Any, ClassVar, Final, Generator, TypeVar

from cryptography.fernet import Fernet, InvalidToken

from ...system.object import Object, ObjectMeta, final
from ...system.utils.abc import isconcreteclass


class ValidationError(Exception):
    pass


class AbstractNetworkProtocol(Object):
    @abstractmethod
    def serialize(self, packet: Any) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError


class AbstractStreamNetworkProtocol(AbstractNetworkProtocol):
    def parser_add_header_footer(self, data: bytes) -> bytes:
        return data

    @abstractmethod
    def parse_received_data(self, buffer: BufferedReader) -> Generator[bytes, None, None]:
        raise NotImplementedError


class AutoParsedStreamNetworkProtocol(AbstractStreamNetworkProtocol):
    __struct: Final[Struct] = Struct("!I")

    def parser_add_header_footer(self, data: bytes) -> bytes:
        header: bytes = self.__struct.pack(len(data))
        return header + data

    def parse_received_data(self, buffer: BufferedReader) -> Generator[bytes, None, None]:
        struct: Struct = self.__struct
        while len(buffer.peek(struct.size)) >= struct.size:
            # TODO: Check seekable() before doing that
            header: bytes = buffer.read(struct.size)
            try:
                data_length: int = struct.unpack(header)[0]
            except StructError:
                buffer.read()  # Flush all buffer as the data may be corrupted
                return
            # TODO: Test with tiny buffer size
            if len(buffer.peek(data_length)) < data_length:  # Not enough data
                # Reset cursor position for the next call
                buffer.seek(-struct.size, SEEK_CUR)
                return
            yield buffer.read(data_length)


class SecuredNetworkProtocolMeta(ObjectMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="SecuredNetworkProtocolMeta")

    def __new__(mcs: type[__Self], name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> __Self:
        try:
            SecuredNetworkProtocol
        except NameError:
            pass
        else:
            if not any(issubclass(b, SecuredNetworkProtocol) for b in bases):
                raise TypeError(
                    f"{name!r} must inherit from a {SecuredNetworkProtocol.__name__} class in order to use {SecuredNetworkProtocolMeta.__name__} metaclass"
                )
            for attr in ("_cryptography_fernet_",):
                if attr in namespace:
                    raise TypeError(f"Explicit setting of {attr!r} attribute is forbidden")

            if any(len(tuple(filter(lambda t: hasattr(t, attr), bases))) > 1 for attr in ("_cryptography_fernet_", "SECRET_KEY")):
                raise TypeError("Attribute conflict with security attributes")

        _MISSING: Any = object()

        SECRET_KEY: str = namespace.pop("SECRET_KEY", _MISSING)
        secret_key_var: str = kwargs.pop("secret_key_var", _MISSING)

        cls = super().__new__(mcs, name, bases, namespace, **kwargs)

        if SECRET_KEY is not _MISSING and secret_key_var is not _MISSING:
            raise ValueError("secret_key_var and SECRET_KEY was given simultaneously")
        if hasattr(cls, "SECRET_KEY"):
            if SECRET_KEY is not _MISSING or secret_key_var is not _MISSING:
                raise TypeError(f"Attempting to modify the SECRET_KEY variable")
            if not hasattr(cls, "_cryptography_fernet_"):
                SECRET_KEY = getattr(cls, "SECRET_KEY")
        elif isconcreteclass(cls) and not hasattr(cls, "_cryptography_fernet_"):
            if SECRET_KEY is _MISSING and secret_key_var is _MISSING:
                secret_key_var = "SECRET_KEY"

        if SECRET_KEY is _MISSING and secret_key_var is _MISSING:
            return cls

        if SECRET_KEY is _MISSING:
            from os import environ

            try:
                SECRET_KEY = environ[secret_key_var]
            except KeyError:
                raise KeyError(
                    f"Please provide a secret key in your environment using {secret_key_var!r} key set the 'SECRET_KEY' class variable"
                ) from None
            finally:
                del environ
        if not isinstance(SECRET_KEY, str):
            raise TypeError(f"Invalid SECRET_KEY type, expected str but got {type(SECRET_KEY).__qualname__!r}")
        if not SECRET_KEY:
            raise ValueError("Empty secret key")
        Fernet(SECRET_KEY)
        fernet_cached_property = cached_property(lambda self: Fernet(SECRET_KEY))
        super(SecuredNetworkProtocolMeta, cls).__setattr__("_cryptography_fernet_", fernet_cached_property)
        fernet_cached_property.__set_name__(cls, "_cryptography_fernet_")
        super(SecuredNetworkProtocolMeta, cls).__setattr__("SECRET_KEY", SECRET_KEY)

        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if name == "SECRET_KEY":
            raise AttributeError(f"Attempting to modify the secret key")
        if name in ["_cryptography_fernet_"]:
            raise AttributeError(f"{name!r}: Read-only property")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name == "SECRET_KEY":
            raise AttributeError(f"Attempting to delete the secret key")
        if name in ["_cryptography_fernet_"]:
            raise AttributeError(f"{name!r}: Read-only property")
        return super().__delattr__(name)


class SecuredNetworkProtocol(AutoParsedStreamNetworkProtocol, metaclass=SecuredNetworkProtocolMeta):
    SECRET_KEY: ClassVar[str]

    def __init__(self) -> None:
        super().__init__()
        self.__lock = RLock()

    @final
    def serialize(self, packet: Any) -> bytes:
        data: bytes = self.get_unsafe_protocol().serialize(packet)
        with self.__lock:
            return self.fernet.encrypt(data)

    @final
    def deserialize(self, data: bytes) -> Any:
        with self.__lock:
            try:
                data = self.fernet.decrypt(data)
            except InvalidToken as exc:
                raise ValidationError("Invalid token") from exc
        return self.get_unsafe_protocol().deserialize(data)

    @property
    @final
    def fernet(self) -> Fernet:
        cls_fernet: Fernet = getattr(self, "_cryptography_fernet_")
        return cls_fernet

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    @abstractmethod
    def get_unsafe_protocol(self) -> AbstractNetworkProtocol:
        raise NotImplementedError
