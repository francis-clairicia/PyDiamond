# -*- coding: Utf-8 -*
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network abstract base socket module"""

from __future__ import annotations

__all__ = [
    "AbstractSocket",
    "AbstractTCPClientSocket",
    "AbstractTCPServerSocket",
    "AbstractTCPSocket",
    "AbstractUDPSocket",
    "IPv4SocketAddress",
    "IPv6SocketAddress",
    "ReceivedDatagram",
    "SocketMeta",
]

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from abc import ABCMeta, abstractmethod
from typing import Any, ClassVar, NamedTuple, TypeAlias, TypeVar, final, overload

from ...system.non_copyable import NonCopyableMeta
from .constants import SOCK_DGRAM, SOCK_STREAM, AddressFamily, ShutdownFlag, SocketKind


class IPv4SocketAddress(NamedTuple):
    host: str
    port: int


class IPv6SocketAddress(NamedTuple):
    host: str
    port: int
    flowinfo: int = 0
    scope_id: int = 0


SocketAddress: TypeAlias = IPv4SocketAddress | IPv6SocketAddress


class SocketMeta(ABCMeta, NonCopyableMeta):
    pass


class AbstractSocket(metaclass=SocketMeta):
    __Self = TypeVar("__Self", bound="AbstractSocket")

    def __repr__(self) -> str:
        sock_family: AddressFamily = self.family
        sock_type: SocketKind = self.type
        if not self.is_open():
            return f"<{type(self).__name__} family={sock_family}, type={sock_type} closed>"
        sock_fd: int = self.fileno()
        laddr: tuple[Any, ...] = tuple(self.getsockname())
        return f"<{type(self).__name__} fd={sock_fd}, family={sock_family}, type={sock_type}, laddr={laddr}>"

    def __str__(self) -> str:
        return self.__repr__()

    def __del__(self) -> None:
        try:
            self.close()
        except:
            pass

    def __enter__(self: __Self) -> __Self:
        if not self.is_open():
            raise RuntimeError("Closed socket")
        return self

    def __exit__(self, *args: Any) -> None:
        if self.is_open():
            try:
                self.close()
            except:

                from sys import stderr
                from traceback import print_exc

                print(f"Exception ignored in {AbstractSocket.__exit__}", file=stderr)
                print_exc()

    @abstractmethod
    def is_open(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def getsockname(self) -> SocketAddress:
        raise NotImplementedError

    @overload
    @abstractmethod
    def getsockopt(self, level: int, optname: int) -> int:
        ...

    @overload
    @abstractmethod
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        ...

    @abstractmethod
    def getsockopt(self, level: int, optname: int, buflen: int = ...) -> int | bytes:
        raise NotImplementedError

    @overload
    @abstractmethod
    def setsockopt(self, level: int, optname: int, value: int | bytes) -> None:
        ...

    @overload
    @abstractmethod
    def setsockopt(self, level: int, optname: int, value: None, optlen: int) -> None:
        ...

    @abstractmethod
    def setsockopt(self, level: int, optname: int, value: int | bytes | None, optlen: int = ...) -> None:
        raise NotImplementedError

    @abstractmethod
    def getblocking(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def setblocking(self, flag: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    def fileno(self) -> int:
        raise NotImplementedError

    @property
    @abstractmethod
    def family(self) -> AddressFamily:
        raise NotImplementedError

    @property
    @abstractmethod
    def type(self) -> SocketKind:
        raise NotImplementedError

    del __Self


class AbstractTCPSocket(AbstractSocket):
    @abstractmethod
    def shutdown(self, how: ShutdownFlag) -> None:
        raise NotImplementedError

    @final
    @property
    def type(self) -> SocketKind:
        return SOCK_STREAM


class AbstractTCPServerSocket(AbstractTCPSocket):
    DEFAULT_BACKLOG: ClassVar[int] = 128

    __Self = TypeVar("__Self", bound="AbstractTCPServerSocket")

    @classmethod
    @abstractmethod
    def bind(
        cls: type[__Self],
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
    ) -> __Self:
        raise NotImplementedError

    @abstractmethod
    def accept(self) -> tuple[AbstractTCPClientSocket, SocketAddress]:
        raise NotImplementedError

    @abstractmethod
    def listening(self) -> int:
        raise NotImplementedError

    @abstractmethod
    def listen(self, backlog: int) -> None:
        raise NotImplementedError

    del __Self


class AbstractTCPClientSocket(AbstractTCPSocket):
    __Self = TypeVar("__Self", bound="AbstractTCPClientSocket")

    @classmethod
    @abstractmethod
    def connect(
        cls: type[__Self],
        address: tuple[str, int],
        *,
        timeout: float | None = ...,
        family: int | None = ...,
    ) -> __Self:
        raise NotImplementedError

    def __repr__(self) -> str:
        sock_family: AddressFamily = self.family
        sock_type: SocketKind = self.type
        if not self.is_open():
            return f"<{type(self).__name__} family={sock_family}, type={sock_type} closed>"
        sock_fd: int = self.fileno()
        laddr: tuple[Any, ...] = tuple(self.getsockname())
        raddr: tuple[Any, ...] | None = self.getpeername()
        if raddr is not None:
            raddr = tuple(raddr)
            return f"<{type(self).__name__} fd={sock_fd}, family={sock_family}, type={sock_type}, laddr={laddr}, raddr={raddr}>"
        return f"<{type(self).__name__} fd={sock_fd}, family={sock_family}, type={sock_type}, laddr={laddr}>"

    @abstractmethod
    def recv(self, bufsize: int, flags: int = ...) -> bytes:
        raise NotImplementedError

    @abstractmethod
    def send(self, data: bytes, flags: int = ...) -> int:
        raise NotImplementedError

    @abstractmethod
    def getpeername(self) -> SocketAddress | None:
        raise NotImplementedError

    def is_connected(self) -> bool:
        return self.is_open() and self.getpeername() is not None

    @abstractmethod
    def reconnect(self, timeout: float | None = ...) -> None:
        raise NotImplementedError

    def try_reconnect(self, timeout: float | None = None) -> bool:
        try:
            self.reconnect(timeout)
        except OSError:
            pass
        return self.is_connected()

    del __Self


class ReceivedDatagram(NamedTuple):
    body: bytes
    sender: SocketAddress


class AbstractUDPSocket(AbstractSocket):
    MAX_PACKET_SIZE: ClassVar[int] = 8192

    @abstractmethod
    def recvfrom(self, bufsize: int = ..., flags: int = ...) -> ReceivedDatagram:
        raise NotImplementedError

    @abstractmethod
    def sendto(self, data: bytes, address: SocketAddress, flags: int = ...) -> int:
        raise NotImplementedError

    @final
    @property
    def type(self) -> SocketKind:
        return SOCK_DGRAM


class AbstractUDPServerSocket(AbstractUDPSocket):
    __Self = TypeVar("__Self", bound="AbstractUDPServerSocket")

    @classmethod
    @abstractmethod
    def bind(
        cls: type[__Self],
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = ...,
    ) -> __Self:
        raise NotImplementedError

    del __Self


class AbstractUDPClientSocket(AbstractUDPSocket):
    __Self = TypeVar("__Self", bound="AbstractUDPClientSocket")

    @classmethod
    @abstractmethod
    def create(cls: type[__Self], family: int = ...) -> __Self:
        raise NotImplementedError

    del __Self
