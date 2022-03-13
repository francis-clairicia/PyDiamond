# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkProtocol",
    "AutoParsedNetworkProtocol",
    "NetworkProtocolMeta",
    "SecuredNetworkProtocol",
    "SecuredNetworkProtocolMeta",
    "ValidationError",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import ABCMeta, abstractmethod
from contextlib import contextmanager
from struct import Struct, error as StructError
from threading import RLock
from types import TracebackType
from typing import Any, Callable, ClassVar, Final, Generator, Iterator, ParamSpec, TypeVar

from cryptography.fernet import Fernet, InvalidToken

from ...system.namespace import ClassNamespaceMeta
from ...system.utils import isconcreteclass, wraps


class ValidationError(Exception):
    pass


class NetworkProtocolMeta(ABCMeta, ClassNamespaceMeta):
    __Self = TypeVar("__Self", bound="NetworkProtocolMeta")

    def __new__(metacls: type[__Self], name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> __Self:
        try:
            AbstractNetworkProtocol
        except NameError:
            pass
        else:
            if not any(issubclass(b, AbstractNetworkProtocol) for b in bases):
                raise TypeError(
                    f"{name!r} must be inherits from a {AbstractNetworkProtocol.__name__} class in order to use {NetworkProtocolMeta.__name__} metaclass"
                )
        return super().__new__(metacls, name, bases, namespace)

    del __Self


class AbstractNetworkProtocol(metaclass=NetworkProtocolMeta, frozen=True):
    @classmethod
    @abstractmethod
    def serialize(cls, packet: Any) -> bytes:
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def deserialize(cls, data: bytes) -> Any:
        raise NotImplementedError

    @classmethod
    def add_header_footer(cls, data: bytes) -> bytes:
        return data

    @classmethod
    @abstractmethod
    def parse_received_data(cls, buffer: bytes) -> Generator[bytes, None, bytes]:
        raise NotImplementedError

    @classmethod
    def verify_packet_to_send(cls, packet: Any) -> None:
        pass

    @classmethod
    def verify_received_data(cls, data: bytes) -> None:
        pass

    @classmethod
    def verify_received_packet(cls, packet: Any) -> None:
        pass

    @classmethod
    def handle_deserialize_error(
        cls, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        return False


class AutoParsedNetworkProtocol(AbstractNetworkProtocol):
    struct: Final[Struct] = Struct("!I")

    @classmethod
    def add_header_footer(cls, data: bytes) -> bytes:
        header: bytes = cls.struct.pack(len(data))
        return header + data

    @classmethod
    def parse_received_data(cls, buffer: bytes) -> Generator[bytes, None, bytes]:
        struct: Struct = cls.struct
        while True:
            if len(buffer) < struct.size:
                break
            header: bytes = buffer[: struct.size]
            body: bytes = buffer[struct.size :]
            try:
                data_length: int = struct.unpack(header)[0]
            except StructError:
                return bytes()
            if len(body) < data_length:
                break
            yield body[:data_length]
            buffer = body[data_length:]
        return buffer


class SecuredNetworkProtocolMeta(NetworkProtocolMeta):
    __Self = TypeVar("__Self", bound="SecuredNetworkProtocolMeta")

    def __new__(metacls: type[__Self], name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> __Self:
        try:
            SecuredNetworkProtocol
        except NameError:
            namespace["_lock_"] = RLock()
        else:
            if not any(issubclass(b, SecuredNetworkProtocol) for b in bases):
                raise TypeError(
                    f"{name!r} must be inherits from a {SecuredNetworkProtocol.__name__} class in order to use {SecuredNetworkProtocolMeta.__name__} metaclass"
                )
            for attr in ("_cryptography_fernet_", "_lock_"):
                if attr in namespace:
                    raise TypeError(f"Explicit setting of {attr!r} attribute is forbidden")

            if any(
                len(tuple(filter(lambda t: hasattr(t, attr), bases))) > 1
                for attr in ("_cryptography_fernet_", "_lock_", "SECRET_KEY")
            ):
                raise TypeError("Attribute conflict with security attributes")

            for attr in ("add_header_footer", "parse_received_data", "verify_received_data"):
                if attr in namespace:
                    raise TypeError(f"{attr!r} must not be overriden")
                namespace[attr] = vars(SecuredNetworkProtocol)[attr]

        _MISSING: Any = object()

        SECRET_KEY: str = namespace.pop("SECRET_KEY", _MISSING)
        secret_key_var: str = kwargs.pop("secret_key_var", _MISSING)

        cls = super().__new__(metacls, name, bases, namespace, **kwargs)

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
        if SECRET_KEY is not _MISSING or secret_key_var is not _MISSING:
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
            setattr(cls, "SECRET_KEY", SECRET_KEY)
            if not isinstance(SECRET_KEY, str):
                raise TypeError(f"Invalid SECRET_KEY type, expected str but got {type(SECRET_KEY).__qualname__!r}")
            if not SECRET_KEY:
                raise ValueError("Empty secret key")
            RFernet = metacls.__RFernet
            fernet: Fernet = RFernet(SECRET_KEY)
            setattr(cls, "_cryptography_fernet_", fernet)

        serialize: Callable[[type[SecuredNetworkProtocol], Any], bytes]
        try:
            serialize = getattr(getattr(cls, "serialize"), "__func__")
        except AttributeError:
            serialize = _MISSING
        deserialize: Callable[[type[SecuredNetworkProtocol], bytes], Any]
        try:
            deserialize = getattr(getattr(cls, "deserialize"), "__func__")
        except (AttributeError, KeyError):
            deserialize = _MISSING

        _P = ParamSpec("_P")
        _T = TypeVar("_T")

        def fernet_wrapper(func: Callable[_P, _T]) -> Callable[_P, _T]:
            setattr(func, "_fernet_wrapper_", True)
            return func

        def is_fernet_wrapper(func: Callable[..., Any]) -> bool:
            return getattr(func, "_fernet_wrapper_", False)

        if serialize is not _MISSING and not is_fernet_wrapper(serialize):

            @wraps(serialize)
            @fernet_wrapper
            def serialize_wrapper(cls: type[SecuredNetworkProtocol], /, packet: Any) -> bytes:
                lock: RLock = getattr(cls, "_lock_")
                with lock:
                    fernet: SecuredNetworkProtocolMeta.__RFernet
                    fernet = getattr(cls, "_cryptography_fernet_", _MISSING)
                    if fernet is _MISSING:
                        raise AttributeError("No SECRET_KEY given")
                    data: bytes
                    with fernet.increase_depth("encryption"):
                        data = serialize(cls, packet)
                    if fernet.get_depth("encryption") == 0:
                        return fernet.encrypt(data)
                return data

            setattr(cls, "serialize", classmethod(serialize_wrapper))

        if deserialize is not _MISSING and not is_fernet_wrapper(deserialize):

            @wraps(deserialize)
            @fernet_wrapper
            def deserialize_wrapper(cls: type[SecuredNetworkProtocol], /, data: bytes) -> Any:
                lock: RLock = getattr(cls, "_lock_")
                with lock:
                    fernet: SecuredNetworkProtocolMeta.__RFernet
                    fernet = getattr(cls, "_cryptography_fernet_", _MISSING)
                    if fernet is _MISSING:
                        raise AttributeError("No SECRET_KEY given")
                    packet: Any
                    if fernet.get_depth("decryption") == 0:
                        data = fernet.decrypt(data)
                    with fernet.increase_depth("decryption"):
                        packet = deserialize(cls, data)
                    return packet

            setattr(cls, "deserialize", classmethod(deserialize_wrapper))

        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if getattr(cls, "_class_namespace_was_init_") and name == "SECRET_KEY":
            raise AttributeError(f"Attempting to modify the secret key")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if getattr(cls, "_class_namespace_was_init_") and name == "SECRET_KEY":
            raise AttributeError(f"Attempting to delete the secret key")
        return super().__delattr__(name)

    class __RFernet(Fernet):
        def __init__(self, key: bytes | str, backend: Any = None):
            super().__init__(key, backend)
            self.__lock: RLock = RLock()
            self.__depth: dict[str, int] = {}

        @contextmanager
        def increase_depth(self, context: str) -> Iterator[None]:
            with self.__lock:
                depth: dict[str, int] = self.__depth
                depth[context] = depth.get(context, 0) + 1
                try:
                    yield
                finally:
                    depth[context] -= 1
                    if depth[context] <= 0:
                        depth.pop(context)

        def get_depth(self, context: str) -> int:
            depth: dict[str, int] = self.__depth
            return depth.get(context, 0)

    del __Self


class SecuredNetworkProtocol(AutoParsedNetworkProtocol, metaclass=SecuredNetworkProtocolMeta):
    SECRET_KEY: ClassVar[str]

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    @classmethod
    def add_header_footer(cls, data: bytes) -> bytes:
        return AutoParsedNetworkProtocol.add_header_footer(data)

    @classmethod
    def parse_received_data(cls, buffer: bytes) -> Generator[bytes, None, bytes]:
        return AutoParsedNetworkProtocol.parse_received_data(buffer)

    @classmethod
    def verify_received_data(cls, data: bytes) -> None:
        return AutoParsedNetworkProtocol.verify_received_data(data)

    @classmethod
    def handle_deserialize_error(
        cls, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        if issubclass(exc_type, InvalidToken):
            return True
        return super().handle_deserialize_error(data, exc_type, exc_value, tb)