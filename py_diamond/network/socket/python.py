# -*- coding: Utf-8 -*
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

__author__ = "Francis Clairicia-Rose-Claire-Josephine"
__copyright__ = "Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine"
__license__ = "GNU GPL v3.0"


from os import name as OS_NAME
from socket import (
    SO_REUSEADDR,
    SOCK_DGRAM,
    SOCK_STREAM,
    SOL_SOCKET,
    create_connection as _create_connection,
    create_server as _create_server,
    has_ipv6 as HAS_IPV6,
    socket,
)
from threading import RLock
from typing import Any, Callable, Concatenate, Final, ParamSpec, TypeVar

from ...system._mangling import delattr_pv, getattr_pv, hasattr_pv, setattr_pv
from ...system.object import final
from ...system.utils import concreteclass, wraps
from .base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractTCPServerSocket,
    AbstractUDPClientSocket,
    AbstractUDPServerSocket,
    IPv4SocketAddress,
    IPv6SocketAddress,
    ReceivedDatagram,
    SocketAddress,
)
from .constants import AF_INET, AF_INET6, AddressFamily, ShutdownFlag

_MISSING: Any = object()


_P = ParamSpec("_P")
_R = TypeVar("_R")
_SocketVar = TypeVar("_SocketVar", bound="_AbstractPythonSocket")


def _thread_safe_python_socket_method(
    func: Callable[Concatenate[_SocketVar, _P], _R]
) -> Callable[Concatenate[_SocketVar, _P], _R]:
    @wraps(func)
    def wrapper(self: _SocketVar, /, *args: Any, **kwargs: Any) -> Any:
        lock: RLock = getattr_pv(self, "lock", owner=_AbstractPythonSocket)
        with lock:
            return func(self, *args, **kwargs)

    return wrapper


class _AbstractPythonSocket(AbstractSocket):
    __slots__ = ("__lock", "__socket", "__family")

    def __init__(self) -> None:
        setattr_pv(self, "lock", RLock(), owner=_AbstractPythonSocket)
        super().__init__()

    @_thread_safe_python_socket_method
    def __repr__(self) -> str:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        sock_family = self.family
        if sock is _MISSING:
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
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        try:
            sock.close()
        except:
            pass
        finally:
            delattr_pv(self, "socket", owner=_AbstractPythonSocket)

    @final
    @_thread_safe_python_socket_method
    def getsockname(self) -> SocketAddress:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        addr: tuple[Any, ...] = sock.getsockname()
        if int(sock.family) == AF_INET6:
            return IPv6SocketAddress(*addr)
        return IPv4SocketAddress(*addr)

    @final
    @_thread_safe_python_socket_method
    def getblocking(self) -> bool:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return sock.getblocking()

    @final
    @_thread_safe_python_socket_method
    def setblocking(self, flag: bool) -> None:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return sock.setblocking(flag)

    @final
    @_thread_safe_python_socket_method
    def gettimeout(self) -> float | None:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return sock.gettimeout()

    @final
    @_thread_safe_python_socket_method
    def settimeout(self, value: float | None) -> None:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return sock.settimeout(value)

    @final
    @_thread_safe_python_socket_method
    def fileno(self) -> int:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return sock.fileno()

    @property  # type: ignore[misc]
    @final
    @_thread_safe_python_socket_method
    def family(self) -> AddressFamily:
        family: AddressFamily = getattr_pv(self, "family", owner=_AbstractPythonSocket)
        return family


class _AbstractPythonTCPSocket(_AbstractPythonSocket):
    __slots__ = ()

    @final
    @_thread_safe_python_socket_method
    def shutdown(self, how: ShutdownFlag) -> None:
        how = ShutdownFlag(how)
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return sock.shutdown(how)


@final
@concreteclass
class PythonTCPServerSocket(_AbstractPythonTCPSocket, AbstractTCPServerSocket):
    __slots__ = ("__backlog",)

    DEFAULT_BACKLOG: Final[int] = 128

    def __init__(self) -> None:
        super().__init__()
        setattr_pv(self, "backlog", 0)

    @final
    @classmethod
    def bind(
        cls,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
        backlog: int | None = None,
        dualstack_ipv6: bool = False,
    ) -> PythonTCPServerSocket:
        family = AddressFamily(family)
        if backlog is None:
            backlog = cls.DEFAULT_BACKLOG

        self: PythonTCPServerSocket = cls()
        sock: socket = _create_server(address, family=family, backlog=backlog, reuse_port=False, dualstack_ipv6=dualstack_ipv6)
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        setattr_pv(self, "family", AddressFamily(family), owner=_AbstractPythonSocket)
        setattr_pv(self, "backlog", backlog)
        return self

    @final
    @_thread_safe_python_socket_method
    def accept(self) -> tuple[PythonTCPClientSocket, SocketAddress]:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        client: socket
        addr: tuple[Any, ...]
        client, addr = sock.accept()
        try:
            sockaddr: SocketAddress
            if int(sock.family) == AF_INET6:
                sockaddr = IPv6SocketAddress(*addr)
            else:
                sockaddr = IPv4SocketAddress(*addr)
            tcp_client = PythonTCPClientSocket()
            setattr_pv(tcp_client, "socket", client, owner=_AbstractPythonSocket)
            setattr_pv(tcp_client, "family", AddressFamily(client.family), owner=_AbstractPythonSocket)
            return (tcp_client, sockaddr)
        except:
            client.close()
            raise

    @final
    @_thread_safe_python_socket_method
    def listening(self) -> int:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        return int(getattr_pv(self, "backlog"))

    @final
    @_thread_safe_python_socket_method
    def listen(self, backlog: int) -> None:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        sock.listen(backlog)
        setattr_pv(self, "backlog", backlog)


@final
@concreteclass
class PythonTCPClientSocket(_AbstractPythonTCPSocket, AbstractTCPClientSocket):
    __slots__ = ("__peer")

    @final
    @classmethod
    def connect(
        cls, address: tuple[str, int], *, timeout: float | None = None, family: int | None = None
    ) -> PythonTCPClientSocket:
        if family is not None:
            family = AddressFamily(family)
        self: PythonTCPClientSocket = cls()
        sock: socket
        if family is None:
            sock = _create_connection(address, timeout=timeout)
        else:
            sock = socket(family, SOCK_STREAM)
            try:
                sock.settimeout(timeout)
                sock.connect(address)
            except:
                sock.close()
                raise
        sock.settimeout(None)
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        setattr_pv(self, "family", AddressFamily(sock.family), owner=_AbstractPythonSocket)
        setattr_pv(self, "peer", sock.getpeername())
        return self

    @final
    @_thread_safe_python_socket_method
    def __repr__(self) -> str:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        sock_family = AddressFamily(self.family)
        if sock is _MISSING:
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
    def recv(self, bufsize: int, flags: int = 0) -> bytes:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        if OS_NAME in ("nt", "cygwin"):  # Flags not supported on Windows
            return sock.recv(bufsize)
        return sock.recv(bufsize, flags)

    @final
    @_thread_safe_python_socket_method
    def send(self, data: bytes, flags: int = 0) -> int:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        if not data:
            return 0
        if OS_NAME in ("nt", "cygwin"):  # Flags not supported on Windows
            return sock.send(data)
        return sock.send(data, flags)

    @final
    @_thread_safe_python_socket_method
    def getpeername(self) -> SocketAddress | None:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        try:
            addr: tuple[Any, ...] = sock.getpeername()
        except OSError:
            return None
        if int(sock.family) == AF_INET6:
            return IPv6SocketAddress(*addr)
        return IPv4SocketAddress(*addr)

    @final
    @_thread_safe_python_socket_method
    def is_connected(self) -> bool:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            return False
        try:
            sock.getpeername()
        except OSError:
            return False
        return True

    @final
    @_thread_safe_python_socket_method
    def reconnect(self, timeout: float | None = None) -> None:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        try:
            sock.getpeername()
        except OSError:
            pass
        else:
            return
        address: tuple[Any, ...] = getattr_pv(self, "peer")
        try:
            sock.settimeout(timeout)
            sock.connect(address)
        except OSError:
            sock.close()
            raise
        finally:
            sock.settimeout(None)

    @final
    @_thread_safe_python_socket_method
    def try_reconnect(self, timeout: float | None = None) -> bool:
        return super().try_reconnect(timeout)


class _AbstractPythonUDPSocket(_AbstractPythonSocket):
    __slots__ = ()

    MAX_PACKET_SIZE: Final[int] = 8192

    @final
    @_thread_safe_python_socket_method
    def recvfrom(self, flags: int = 0) -> ReceivedDatagram:
        bufsize: int = self.MAX_PACKET_SIZE
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        if OS_NAME in ("nt", "cygwin"):  # Flags not supported on Windows
            data, addr = sock.recvfrom(bufsize)
        else:
            data, addr = sock.recvfrom(bufsize, flags)
        sender: SocketAddress
        if int(sock.family) == AF_INET6:
            sender = IPv6SocketAddress(*addr)
        else:
            sender = IPv4SocketAddress(*addr)
        return ReceivedDatagram(data, sender)

    @final
    @_thread_safe_python_socket_method
    def sendto(self, data: bytes, address: SocketAddress, flags: int = 0) -> int:
        if (data_length := len(data)) > self.MAX_PACKET_SIZE:
            raise ValueError(f"Datagram too big ({data_length} > {self.MAX_PACKET_SIZE})")
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        if sock is _MISSING:
            raise RuntimeError("Closed socket")
        if not data_length:
            return 0
        if OS_NAME in ("nt", "cygwin"):  # Flags not supported on Windows
            return sock.sendto(data, address)
        return sock.sendto(data, flags, address)


@final
@concreteclass
class PythonUDPServerSocket(_AbstractPythonUDPSocket, AbstractUDPServerSocket):
    __slots__ = ()

    @final
    @classmethod
    def bind(
        cls,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
    ) -> PythonUDPServerSocket:
        self: PythonUDPServerSocket = cls()
        sock: socket = socket(family, SOCK_DGRAM)

        try:
            if OS_NAME not in ("nt", "cygwin"):

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
        except:
            sock.close()
            raise

        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        setattr_pv(self, "family", AddressFamily(sock.family), owner=_AbstractPythonSocket)
        return self


@final
@concreteclass
class PythonUDPClientSocket(_AbstractPythonUDPSocket, AbstractUDPClientSocket):
    __slots__ = ()

    @final
    @classmethod
    def create(cls, family: int = AF_INET, *, host: str = "") -> PythonUDPClientSocket:
        self: PythonUDPClientSocket = cls()
        sock: socket = socket(family, SOCK_DGRAM)
        sock.bind((host, 0))
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        setattr_pv(self, "family", AddressFamily(sock.family), owner=_AbstractPythonSocket)
        return self


del _thread_safe_python_socket_method
