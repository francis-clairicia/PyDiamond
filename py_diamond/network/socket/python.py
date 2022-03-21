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
from socket import SOL_SOCKET, socket
from threading import RLock
from typing import Any, Callable, ParamSpec, TypeVar, final, overload

from ...system._mangling import delattr_pv, getattr_pv, hasattr_pv, setattr_pv
from ...system.utils import concreteclass, wraps
from .base import (
    AbstractSocket,
    AbstractTCPClientSocket,
    AbstractTCPServerSocket,
    AbstractTCPSocket,
    AbstractUDPClientSocket,
    AbstractUDPServerSocket,
    AbstractUDPSocket,
    IPv4SocketAddress,
    IPv6SocketAddress,
    ReceivedDatagram,
    SocketAddress,
)
from .constants import AF_INET, AF_INET6, AddressFamily, ShutdownFlag, SocketKind

_MISSING: Any = object()


_P = ParamSpec("_P")
_R = TypeVar("_R")


def _thread_safe_python_socket_method(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @wraps(func)
    def wrapper(self: Any, /, *args: Any, **kwargs: Any) -> Any:
        lock: RLock = getattr_pv(self, "lock", owner=_AbstractPythonSocket)
        with lock:
            return func(self, *args, **kwargs)

    return wrapper


class _AbstractPythonSocket(AbstractSocket):
    def __init__(self) -> None:
        setattr_pv(self, "lock", RLock(), owner=_AbstractPythonSocket)
        super().__init__()

    @_thread_safe_python_socket_method
    def __repr__(self) -> str:
        sock: socket = getattr_pv(self, "socket", _MISSING, owner=_AbstractPythonSocket)
        sock_family = self.family
        sock_type = self.type
        if sock is _MISSING:
            return f"<{type(self).__name__} family={sock_family}, type={sock_type} closed>"
        laddr: tuple[Any, ...] = sock.getsockname()
        fd: int = sock.fileno()
        return f"<{type(self).__name__} fd={fd}, family={sock_family}, type={sock_type}, laddr={laddr}>"

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
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        addr: tuple[Any, ...] = sock.getsockname()
        if int(sock.family) == AF_INET6:
            return IPv6SocketAddress(*addr)
        return IPv4SocketAddress(*addr)

    @overload
    def getsockopt(self, level: int, optname: int) -> int:
        ...

    @overload
    def getsockopt(self, level: int, optname: int, buflen: int) -> bytes:
        ...

    @final
    @_thread_safe_python_socket_method
    def getsockopt(self, level: int, optname: int, buflen: Any = _MISSING) -> Any:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        if buflen is not _MISSING:
            if not isinstance(buflen, int):
                raise TypeError("Invalid arguments")
            return sock.getsockopt(level, optname, buflen)
        return sock.getsockopt(level, optname)

    @overload
    def setsockopt(self, level: int, optname: int, value: int | bytes) -> None:
        ...

    @overload
    def setsockopt(self, level: int, optname: int, value: None, optlen: int) -> None:
        ...

    @final
    @_thread_safe_python_socket_method
    def setsockopt(self, level: int, optname: int, value: int | bytes | None, optlen: Any = _MISSING) -> None:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        if value is None:
            if optlen is _MISSING:
                raise TypeError("Invalid arguments: missing 'optlen' argument")
            if not isinstance(optlen, int):
                raise TypeError("Invalid arguments")
            return sock.setsockopt(level, optname, None, optlen)
        if optlen is not _MISSING:
            raise TypeError("Invalid arguments: 'optlen' argument given")
        return sock.setsockopt(level, optname, value)

    @final
    @_thread_safe_python_socket_method
    def getblocking(self) -> bool:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.getblocking()

    @final
    @_thread_safe_python_socket_method
    def setblocking(self, flag: bool) -> None:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.setblocking(flag)

    @final
    @_thread_safe_python_socket_method
    def gettimeout(self) -> float | None:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.gettimeout()

    @final
    @_thread_safe_python_socket_method
    def settimeout(self, value: float | None) -> None:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.settimeout(value)

    @final
    @_thread_safe_python_socket_method
    def fileno(self) -> int:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.fileno()

    @property  # type: ignore[misc]
    @final
    @_thread_safe_python_socket_method
    def family(self) -> AddressFamily:
        family: AddressFamily = getattr_pv(self, "family", owner=_AbstractPythonSocket)
        return family


class _AbstractPythonTCPSocket(_AbstractPythonSocket, AbstractTCPSocket):
    @final
    @_thread_safe_python_socket_method
    def shutdown(self, how: ShutdownFlag) -> None:
        how = ShutdownFlag(how)
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.shutdown(how)


@final
@concreteclass
class PythonTCPServerSocket(_AbstractPythonTCPSocket, AbstractTCPServerSocket):
    @final
    @classmethod
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

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

        from socket import create_server

        self: PythonTCPServerSocket = cls()
        sock: socket = create_server(address, family=family, backlog=backlog, reuse_port=False, dualstack_ipv6=dualstack_ipv6)
        if int(sock.type) != int(self.type):
            sock.close()
            raise TypeError("Invalid socket type")
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        setattr_pv(self, "family", AddressFamily(family), owner=_AbstractPythonSocket)
        setattr_pv(self, "backlog", backlog)
        return self

    @final
    @_thread_safe_python_socket_method
    def accept(self) -> tuple[PythonTCPClientSocket, SocketAddress]:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
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
        return int(getattr_pv(self, "backlog"))

    @final
    @_thread_safe_python_socket_method
    def listen(self, backlog: int) -> None:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        sock.listen(backlog)
        setattr_pv(self, "backlog", backlog)


@final
@concreteclass
class PythonTCPClientSocket(_AbstractPythonTCPSocket, AbstractTCPClientSocket):
    @final
    @classmethod
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

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

            from socket import create_connection

            sock = create_connection(address, timeout=timeout)

            if int(sock.type) != int(self.type):
                sock.close()
                raise TypeError("Invalid socket type")
        else:
            sock = socket(family, self.type)
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
        sock_type = SocketKind(self.type)
        if sock is _MISSING:
            return f"<{type(self).__name__} family={sock_family}, type={sock_type} closed>"
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
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        return sock.recv(bufsize, flags)

    @final
    @_thread_safe_python_socket_method
    def send(self, data: bytes, flags: int = 0) -> int:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        if not data:
            return 0
        sock.sendall(data, flags)
        return len(data)

    @final
    @_thread_safe_python_socket_method
    def getpeername(self) -> SocketAddress | None:
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
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


class _AbstractPythonUDPSocket(_AbstractPythonSocket, AbstractUDPSocket):
    @final
    @_thread_safe_python_socket_method
    def recvfrom(self, bufsize: int | None = None, flags: int = 0) -> ReceivedDatagram:
        if bufsize is None:
            bufsize = self.MAX_PACKET_SIZE
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
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
        sock: socket = getattr_pv(self, "socket", owner=_AbstractPythonSocket)
        if not data_length:
            return 0
        return sock.sendto(data, flags, address)


@final
@concreteclass
class PythonUDPServerSocket(_AbstractPythonUDPSocket, AbstractUDPServerSocket):
    @final
    @classmethod
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

    @final
    @classmethod
    def bind(
        cls,
        address: tuple[str, int] | tuple[str, int, int, int],
        *,
        family: int = AF_INET,
    ) -> PythonUDPServerSocket:
        self: PythonUDPServerSocket = cls()
        sock: socket = socket(family, self.type)

        try:
            if OS_NAME not in ("nt", "cygwin"):
                from socket import SO_REUSEADDR

                try:
                    sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                except OSError:
                    pass
                finally:
                    del SO_REUSEADDR

            if family == AF_INET6:
                from socket import has_ipv6 as HAS_IPV6

                if HAS_IPV6:
                    try:
                        from socket import IPPROTO_IPV6, IPV6_V6ONLY
                    except ImportError:
                        pass
                    else:
                        sock.setsockopt(IPPROTO_IPV6, IPV6_V6ONLY, 1)
                        del IPPROTO_IPV6, IPV6_V6ONLY
                del HAS_IPV6

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
    @final
    @classmethod
    def __init_subclass__(cls) -> None:
        raise TypeError("No subclass are allowed")

    @final
    @classmethod
    def create(cls, family: int = AF_INET, *, host: str = "") -> PythonUDPClientSocket:
        self: PythonUDPClientSocket = cls()
        sock: socket = socket(family, self.type)
        sock.bind((host, 0))
        setattr_pv(self, "socket", sock, owner=_AbstractPythonSocket)
        setattr_pv(self, "family", AddressFamily(sock.family), owner=_AbstractPythonSocket)
        return self


del _thread_safe_python_socket_method, _P, _R
