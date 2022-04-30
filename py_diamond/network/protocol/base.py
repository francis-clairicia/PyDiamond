# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Abstract base network packet protocol module"""

from __future__ import annotations

__all__ = [
    "AbstractNetworkProtocol",
    "AutoParsedNetworkProtocol",
    "SecuredNetworkProtocol",
    "SecuredNetworkProtocolMeta",
    "ValidationError",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"

from abc import abstractmethod
from contextlib import contextmanager
from functools import cached_property
from struct import Struct, error as StructError
from threading import RLock
from types import MethodType, TracebackType
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Final, Generator, Iterator, TypeVar

from cryptography.fernet import Fernet, InvalidToken

from ...system.object import Object, ObjectMeta
from ...system.utils import isabstractmethod, isconcreteclass


class ValidationError(Exception):
    pass


class AbstractNetworkProtocol(Object):
    @abstractmethod
    def serialize(self, packet: Any) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def deserialize(self, data: bytes) -> Any:
        raise NotImplementedError

    def parser_add_header_footer(self, data: bytes) -> bytes:
        return data

    @abstractmethod
    def parse_received_data(self, buffer: bytes) -> Generator[bytes, None, bytes]:
        raise NotImplementedError

    def verify_packet_to_send(self, packet: Any) -> None:
        pass

    def verify_received_data(self, data: bytes) -> None:
        pass

    def verify_received_packet(self, packet: Any) -> None:
        pass

    def handle_deserialize_error(
        self, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        return False


class AutoParsedNetworkProtocol(AbstractNetworkProtocol):
    __struct: Final[Struct] = Struct("!I")

    def parser_add_header_footer(self, data: bytes) -> bytes:
        header: bytes = self.__struct.pack(len(data))
        return header + data

    def parse_received_data(self, buffer: bytes) -> Generator[bytes, None, bytes]:
        struct: Struct = self.__struct
        while len(buffer) >= struct.size:
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


class SecuredNetworkProtocolMeta(ObjectMeta):
    if TYPE_CHECKING:
        __Self = TypeVar("__Self", bound="SecuredNetworkProtocolMeta")

    __initializing: set[SecuredNetworkProtocolMeta] = set()

    def __new__(metacls: type[__Self], name: str, bases: tuple[type, ...], namespace: dict[str, Any], **kwargs: Any) -> __Self:
        try:
            SecuredNetworkProtocol
        except NameError:
            pass
        else:
            if not any(issubclass(b, SecuredNetworkProtocol) for b in bases):
                raise TypeError(
                    f"{name!r} must be inherits from a {SecuredNetworkProtocol.__name__} class in order to use {SecuredNetworkProtocolMeta.__name__} metaclass"
                )
            for attr in ("_cryptography_fernet_",):
                if attr in namespace:
                    raise TypeError(f"Explicit setting of {attr!r} attribute is forbidden")

            if any(len(tuple(filter(lambda t: hasattr(t, attr), bases))) > 1 for attr in ("_cryptography_fernet_", "SECRET_KEY")):
                raise TypeError("Attribute conflict with security attributes")

            for attr in ("parser_add_header_footer", "parse_received_data", "verify_received_data"):
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
        RFernet = metacls.__RFernet
        RFernet(SECRET_KEY)
        fernet_cached_property = cached_property(lambda self: RFernet(getattr(self, "SECRET_KEY")))
        setattr(cls, "_cryptography_fernet_", fernet_cached_property)
        fernet_cached_property.__set_name__(cls, "_cryptography_fernet_")
        cls.__initializing.add(cls)
        try:
            setattr(cls, "SECRET_KEY", SECRET_KEY)
        finally:
            cls.__initializing.remove(cls)

        serialize: Callable[[SecuredNetworkProtocol, Any], bytes]
        try:
            serialize = getattr(cls, "serialize")
            if isabstractmethod(serialize):
                raise AttributeError
        except AttributeError:
            serialize = _MISSING
        deserialize: Callable[[SecuredNetworkProtocol, bytes], Any]
        try:
            deserialize = getattr(cls, "deserialize")
            if isabstractmethod(deserialize):
                raise AttributeError
        except AttributeError:
            deserialize = _MISSING

        if serialize is not _MISSING and not isinstance(serialize, cls.__FernetWrapper):

            def serialize_wrapper(self: SecuredNetworkProtocol, /, packet: Any) -> bytes:
                with self.lock:
                    fernet: SecuredNetworkProtocolMeta.__RFernet = getattr(self, "_cryptography_fernet_")
                    data: bytes
                    with fernet.increase_depth("encryption"):
                        data = serialize(self, packet)
                    if fernet.get_depth("encryption") == 0:
                        return fernet.encrypt(data)
                return data

            setattr(cls, "serialize", cls.__FernetWrapper(serialize, serialize_wrapper, "encryption"))

        if deserialize is not _MISSING and not isinstance(deserialize, cls.__FernetWrapper):

            def deserialize_wrapper(self: SecuredNetworkProtocol, /, data: bytes) -> Any:
                with self.lock:
                    fernet: SecuredNetworkProtocolMeta.__RFernet
                    fernet = getattr(self, "_cryptography_fernet_")
                    packet: Any
                    if fernet.get_depth("decryption") == 0:
                        data = fernet.decrypt(data)
                    with fernet.increase_depth("decryption"):
                        packet = deserialize(self, data)
                    return packet

            setattr(cls, "deserialize", cls.__FernetWrapper(deserialize, deserialize_wrapper, "decryption"))

        return cls

    def __setattr__(cls, name: str, value: Any, /) -> None:
        if cls not in cls.__initializing and name == "SECRET_KEY":
            raise AttributeError(f"Attempting to modify the secret key")
        return super().__setattr__(name, value)

    def __delattr__(cls, name: str, /) -> None:
        if name == "SECRET_KEY":
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
            with self.__lock:
                depth: dict[str, int] = self.__depth
                return depth.get(context, 0)

    class __FernetWrapper(Object):
        def __init__(self, func: Callable[..., Any], wrapper: Callable[..., Any], context: str) -> None:
            self.func = func
            self.wrapper = wrapper
            self.context = context

        @cached_property
        def __call__(self) -> Callable[..., Any]:
            return self.wrapper

        def __get__(self, obj: object, objtype: type | None = None, /) -> Callable[..., Any]:
            if obj is None:
                return self
            return MethodType(self, obj)

        @property
        def __wrapped__(self) -> Callable[..., Any]:
            return self.func


class SecuredNetworkProtocol(AutoParsedNetworkProtocol, metaclass=SecuredNetworkProtocolMeta):
    SECRET_KEY: ClassVar[str]

    def __init__(self) -> None:
        super().__init__()
        self.__lock = RLock()

    @property
    def lock(self) -> RLock:
        return self.__lock

    @property
    def fernet(self) -> Fernet:
        cls_fernet: Fernet = getattr(self, "_cryptography_fernet_")
        return cls_fernet

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("utf-8")

    def parser_add_header_footer(self, data: bytes) -> bytes:
        return AutoParsedNetworkProtocol.parser_add_header_footer(self, data)

    def parse_received_data(self, buffer: bytes) -> Generator[bytes, None, bytes]:
        return AutoParsedNetworkProtocol.parse_received_data(self, buffer)

    def verify_received_data(self, data: bytes) -> None:
        return AutoParsedNetworkProtocol.verify_received_data(self, data)

    def handle_deserialize_error(
        self, data: bytes, exc_type: type[BaseException], exc_value: BaseException, tb: TracebackType
    ) -> bool:
        if issubclass(exc_type, InvalidToken):
            return True
        return super().handle_deserialize_error(data, exc_type, exc_value, tb)
