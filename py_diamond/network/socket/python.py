# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network python socket module"""

from __future__ import annotations

__all__ = [
    "PythonTCPClientSocket",
    "PythonTCPServerSocket",
    "PythonUDPClientSocket",
    "PythonUDPServerSocket",
]

import os
from socket import (
    SO_REUSEADDR,
    SOCK_DGRAM,
    SOCK_STREAM,
    SOL_SOCKET,
    SOMAXCONN,
    create_connection as _create_connection,
    create_server as _create_server,
    has_ipv6 as HAS_IPV6,
    socket,
)
from threading import RLock
from typing import TYPE_CHECKING, Any, Callable, Concatenate, Final, ParamSpec, TypeVar

from ...system.object import final
from ...system.utils._mangling import delattr_pv, getattr_pv, hasattr_pv, setattr_pv
from ...system.utils.abc import concreteclass
from ...system.utils.functools import wraps
from .base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractTCPServerSocket,
    AbstractTCPSocket,
    AbstractUDPClientSocket,
    AbstractUDPServerSocket,
    AbstractUDPSocket,
    ReceivedDatagram,
    SocketAddress,
    new_socket_address,
)
from .constants import AF_INET, AF_INET6, AddressFamily, ShutdownFlag

if TYPE_CHECKING:
    from _typeshed import WriteableBuffer


_P = ParamSpec("_P")
_R = TypeVar("_R")
_SocketVar = TypeVar("_SocketVar", bound="_AbstractPythonSocket")


def _thread_safe_python_socket_method(
    func: Callable[Concatenate[_SocketVar, _P], _R]
) -> Callable[Concatenate[_SocketVar, _P], _R]:
    @wraps(func)
    def wrapper(self: _SocketVar, /, *args: _P.args, **kwargs: _P.kwargs) -> Any:
        with getattr_pv(self, "lock", owner=_AbstractPythonSocket):
            return func(self, *args, **kwargs)

    return wrapper


class _AbstractPythonSocket(AbstractSocket):
    __slots__ = ("__lock", "__socket", "__family")

    def __init__(self, family: int) -> None:
        family = AddressFamily(family)
        setattr_pv(self, "lock", RLock(), owner=_AbstractPythonSocket)
        setattr_pv(self, "family", family, owner=_AbstractPythonSocket)
        super().__init__()

    @_thread_safe_python_socket_method
    def __repr__(self) -> str:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        sock_family = self.family
        if sock is None:
            return f"<{type(self).__name__} family={sock_family} closed>"
        laddr: tuple[Any, ...] = sock.getsockname()
        fd: int = sock.fileno()
        return f"<{type(self).__name__} fd={fd}, family={sock_family}, type={sock.type}, laddr={laddr}>"

    @final
    @_thread_safe_python_socket_method
    def is_open(self) -> bool:
        return hasattr_pv(self, "socket", owner=_AbstractPythonSocket)

    @final
    @_thread_safe_python_socket_method
    def close(self) -> None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        try:
            sock.close()
        except OSError:
            pass
        finally:
            delattr_pv(self, "socket", owner=_AbstractPythonSocket)

    @final
    @_thread_safe_python_socket_method
    def getsockname(self) -> SocketAddress:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return new_socket_address(sock.getsockname(), sock.family)

    @final
    @_thread_safe_python_socket_method
    def getblocking(self) -> bool:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.getblocking()

    @final
    @_thread_safe_python_socket_method
    def setblocking(self, flag: bool) -> None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.setblocking(flag)

    @final
    @_thread_safe_python_socket_method
    def gettimeout(self) -> float | None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.gettimeout()

    @final
    @_thread_safe_python_socket_method
    def settimeout(self, value: float | None) -> None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.settimeout(value)

    @final
    @_thread_safe_python_socket_method
    def fileno(self) -> int:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.fileno()

    @property  # type: ignore[misc]
    @final
    @_thread_safe_python_socket_method
    def family(self) -> AddressFamily:
        family: AddressFamily = getattr_pv(self, "family", owner=_AbstractPythonSocket)
        return family


class _AbstractPythonTCPSocket(_AbstractPythonSocket, AbstractTCPSocket):
    __slots__ = ()

    @final
    @_thread_safe_python_socket_method
    def shutdown(self, how: ShutdownFlag) -> None:
        how = ShutdownFlag(how)
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.shutdown(how)


@final
@concreteclass
class PythonTCPServerSocket(_AbstractPythonTCPSocket, AbstractTCPServerSocket):
    __slots__ = ()

    DEFAULT_BACKLOG: Final[int] = max(SOMAXCONN, 128)

    @classmethod
    @final
    def bind(
        cls,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
        backlog: int | None = None,
        dualstack_ipv6: bool = False,
    ) -> PythonTCPServerSocket:
        if backlog is None:
            backlog = cls.DEFAULT_BACKLOG

        self: PythonTCPServerSocket = cls(family)
        sock: socket = _create_server(address, family=family, backlog=backlog, reuse_port=False, dualstack_ipv6=dualstack_ipv6)
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        return self

    @final
    @_thread_safe_python_socket_method
    def accept(self) -> tuple[PythonTCPClientSocket, SocketAddress]:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        client: socket
        addr: tuple[Any, ...]
        client, addr = sock.accept()
        try:
            return (
                PythonTCPClientSocket.from_builtin_socket(client, register_peername=False),
                new_socket_address(addr, client.family),
            )
        except BaseException:
            client.close()
            raise

    @final
    @_thread_safe_python_socket_method
    def listen(self, backlog: int) -> None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        sock.listen(backlog)
        setattr_pv(self, "backlog", backlog)


@final
@concreteclass
class PythonTCPClientSocket(_AbstractPythonTCPSocket, AbstractTCPClientSocket):
    __slots__ = ("__peer",)

    @classmethod
    @final
    def connect(
        cls, address: tuple[str, int], *, timeout: float | None = None, family: int | None = None
    ) -> PythonTCPClientSocket:
        if family is not None:
            family = AddressFamily(family)
        sock: socket
        if family is None:
            sock = _create_connection(address, timeout=timeout)
            family = AddressFamily(sock.family)
        else:
            sock = socket(family, SOCK_STREAM)
            try:
                sock.settimeout(timeout)
                sock.connect(address)
            except BaseException:
                sock.close()
                raise
        sock.settimeout(None)
        return cls.from_builtin_socket(sock, register_peername=True)

    @classmethod
    def from_builtin_socket(cls, sock: socket, *, register_peername: bool) -> PythonTCPClientSocket:
        self = cls(sock.family)
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        if register_peername:
            setattr_pv(self, "peer", sock.getpeername())
        return self

    @final
    @_thread_safe_python_socket_method
    def __repr__(self) -> str:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        sock_family = AddressFamily(self.family)
        if sock is None:
            return f"<{type(self).__name__} family={sock_family} closed>"
        sock_type = sock.type
        laddr: Any = sock.getsockname()
        fd: int = sock.fileno()
        try:
            raddr: Any = sock.getpeername()
        except OSError:
            pass
        else:
            return f"<{type(self).__name__} fd={fd}, family={sock_family}, type={sock_type}, laddr={laddr}, raddr={raddr}>"
        return f"<{type(self).__name__} fd={fd}, family={sock_family}, type={sock_type}, laddr={laddr}>"

    @final
    @_thread_safe_python_socket_method
    def recv(self, bufsize: int, *, flags: int = 0) -> bytes:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.recv(bufsize, flags)

    @final
    @_thread_safe_python_socket_method
    def recv_into(self, buffer: WriteableBuffer, nbytes: int = 0, *, flags: int = 0) -> int:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        return sock.recv_into(buffer, nbytes, flags)

    @final
    @_thread_safe_python_socket_method
    def send(self, data: bytes, *, flags: int = 0) -> int:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        if not data:
            return 0
        return sock.send(data, flags)

    @final
    @_thread_safe_python_socket_method
    def getpeername(self) -> SocketAddress | None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        try:
            addr: tuple[Any, ...] = sock.getpeername()
        except OSError:
            return None
        return new_socket_address(addr, sock.family)

    @final
    @_thread_safe_python_socket_method
    def is_connected(self) -> bool:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            return False
        try:
            sock.getpeername()
        except OSError:
            return False
        return True

    @final
    @_thread_safe_python_socket_method
    def reconnect(self, timeout: float | None = None) -> None:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        try:
            sock.getpeername()
        except OSError:
            pass
        else:
            return
        try:
            address: tuple[Any, ...] = getattr_pv(self, "peer")
        except AttributeError:
            raise ConnectionError("Cannot reconnect to remote host: No peername stored") from None
        try:
            sock.settimeout(timeout)
            sock.connect(address)
        finally:
            sock.settimeout(None)


class _AbstractPythonUDPSocket(_AbstractPythonSocket, AbstractUDPSocket):
    __slots__ = ()

    MAX_PACKET_SIZE: Final[int] = 8192

    @final
    @_thread_safe_python_socket_method
    def recvfrom(self, *, flags: int = 0) -> ReceivedDatagram:
        bufsize: int = self.MAX_PACKET_SIZE
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        data, addr = sock.recvfrom(bufsize, flags)
        return ReceivedDatagram(data, new_socket_address(addr, sock.family))

    @final
    @_thread_safe_python_socket_method
    def recvfrom_into(self, buffer: WriteableBuffer, nbytes: int = 0, *, flags: int = 0) -> tuple[int, SocketAddress]:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        nbytes, addr = sock.recvfrom_into(buffer, nbytes, flags)
        return (nbytes, new_socket_address(addr, sock.family))

    @final
    @_thread_safe_python_socket_method
    def sendto(self, data: bytes, address: SocketAddress, *, flags: int = 0) -> int:
        sock: socket | None = getattr_pv(self, "socket", None, owner=_AbstractPythonSocket)
        if sock is None:
            raise RuntimeError("Closed socket")
        if (data_length := len(data)) > self.MAX_PACKET_SIZE:
            raise ValueError(f"Datagram too big ({data_length} > {self.MAX_PACKET_SIZE})")
        if not data_length:
            return 0
        return sock.sendto(data, flags, address)


@final
@concreteclass
class PythonUDPServerSocket(_AbstractPythonUDPSocket, AbstractUDPServerSocket):
    __slots__ = ()

    @classmethod
    @final
    def bind(
        cls,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
    ) -> PythonUDPServerSocket:
        self: PythonUDPServerSocket = cls(family)
        sock: socket = socket(family, SOCK_DGRAM)

        try:
            if os.name not in ("nt", "cygwin"):

                try:
                    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                except OSError:
                    pass

            if family == AF_INET6 and HAS_IPV6:
                try:
                    from socket import IPPROTO_IPV6, IPV6_V6ONLY
                except ImportError:
                    pass
                else:
                    try:
                        sock.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 1)
                    except OSError:
                        pass
                    del IPPROTO_IPV6, IPV6_V6ONLY

            sock.bind(address)
        except BaseException:
            sock.close()
            raise

        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        return self


@final
@concreteclass
class PythonUDPClientSocket(_AbstractPythonUDPSocket, AbstractUDPClientSocket):
    __slots__ = ()

    @classmethod
    @final
    def create(cls, family: int = AF_INET, *, host: str = "") -> PythonUDPClientSocket:
        family = AddressFamily(family)
        self: PythonUDPClientSocket = cls(family)
        sock: socket = socket(family, SOCK_DGRAM)
        sock.bind((host, 0))
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        return self


del _thread_safe_python_socket_method
