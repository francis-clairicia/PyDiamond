# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network socket module"""

from __future__ import annotations

__all__ = [
    "AF_INET",
    "AF_INET6",
    "AddressFamily",
    "SHUT_RD",
    "SHUT_RDWR",
    "SHUT_WR",
    "ShutdownFlag",
    "create_connection",
    "create_server",
    "guess_best_buffer_size",
    "new_socket_address",
]

import os
import socket as _socket
from enum import IntEnum, unique
from typing import Any, Final, Literal, NamedTuple, TypeAlias, overload


@unique
class AddressFamily(IntEnum):
    AF_INET = _socket.AF_INET
    AF_INET6 = _socket.AF_INET6

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"

    __str__ = __repr__


@unique
class ShutdownFlag(IntEnum):
    SHUT_RD = _socket.SHUT_RD
    SHUT_RDWR = _socket.SHUT_RDWR
    SHUT_WR = _socket.SHUT_WR

    def __repr__(self) -> str:
        return f"{type(self).__name__}.{self.name}"

    __str__ = __repr__


AF_INET: Final[Literal[AddressFamily.AF_INET]] = AddressFamily.AF_INET
AF_INET6: Final[Literal[AddressFamily.AF_INET6]] = AddressFamily.AF_INET6
SHUT_RD: Final[Literal[ShutdownFlag.SHUT_RD]] = ShutdownFlag.SHUT_RD
SHUT_RDWR: Final[Literal[ShutdownFlag.SHUT_RDWR]] = ShutdownFlag.SHUT_RDWR
SHUT_WR: Final[Literal[ShutdownFlag.SHUT_WR]] = ShutdownFlag.SHUT_WR


class IPv4SocketAddress(NamedTuple):
    host: str
    port: int

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"

    def for_connection(self) -> tuple[str, int]:
        return self.host, self.port


class IPv6SocketAddress(NamedTuple):
    host: str
    port: int
    flowinfo: int = 0
    scope_id: int = 0

    def __str__(self) -> str:
        return f"{self.host}:{self.port}"

    def for_connection(self) -> tuple[str, int]:
        return self.host, self.port


SocketAddress: TypeAlias = IPv4SocketAddress | IPv6SocketAddress


@overload
def new_socket_address(addr: tuple[str, int], family: Literal[AddressFamily.AF_INET]) -> IPv4SocketAddress:
    ...


@overload
def new_socket_address(
    addr: tuple[str, int] | tuple[str, int, int, int], family: Literal[AddressFamily.AF_INET6]
) -> IPv6SocketAddress:
    ...


@overload
def new_socket_address(addr: tuple[Any, ...], family: int) -> SocketAddress:
    ...


def new_socket_address(addr: tuple[Any, ...], family: int) -> SocketAddress:
    match AddressFamily(family):
        case AddressFamily.AF_INET:
            return IPv4SocketAddress(*addr)
        case AddressFamily.AF_INET6:
            return IPv6SocketAddress(*addr)
        case _:
            return IPv4SocketAddress(addr[0], addr[1])


def create_connection(
    address: tuple[str, int],
    *,
    timeout: float | None = None,
    family: int | None = None,
    source_address: tuple[bytearray | bytes | str, int] | None = None,
) -> _socket.socket:
    if family is not None:
        family = AddressFamily(family)
    sock: _socket.socket
    if family is None:
        sock = _socket.create_connection(address, timeout=timeout, source_address=source_address)
    else:
        sock = _socket.socket(family, _socket.SOCK_STREAM)
        try:
            sock.settimeout(timeout)
            sock.connect(address)
        except BaseException:
            sock.close()
            raise
    if timeout is not None:
        sock.settimeout(None)
    return sock


def create_server(
    address: tuple[str, int] | tuple[str, int, int, int],
    *,
    family: int = AF_INET,
    type: int = _socket.SOCK_STREAM,
    backlog: int | None = None,
    reuse_port: bool = False,
    dualstack_ipv6: bool = False,
) -> _socket.socket:
    family = AddressFamily(family)
    sock: _socket.socket
    if backlog is not None and backlog <= 0:
        raise ValueError("Negative or null backlog")
    match type:
        case _socket.SOCK_STREAM:
            sock = _socket.create_server(
                address,
                family=family,
                backlog=backlog,
                reuse_port=reuse_port,
                dualstack_ipv6=dualstack_ipv6,
            )
        case _socket.SOCK_DGRAM:
            sock = _socket.socket(family, type)
            try:
                if dualstack_ipv6:
                    raise ValueError("dualstack IPv6 not supported for SOCK_DGRAM sockets")
                if os.name not in ("nt", "cygwin"):

                    try:
                        sock.setsockopt(_socket.SOL_SOCKET, _socket.SO_REUSEADDR, 1)
                    except OSError:
                        pass

                if reuse_port:
                    if not hasattr(_socket, "SO_REUSEPORT"):
                        raise ValueError("SO_REUSEPORT not supported on this platform")
                    sock.setsockopt(_socket.SOL_SOCKET, getattr(_socket, "SO_REUSEPORT"), 1)

                if family == AF_INET6 and _socket.has_ipv6:
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
                if backlog is not None:
                    sock.listen(backlog)
            except BaseException:
                sock.close()
                raise
        case _:
            raise ValueError("Unsupported socket type")

    return sock


def guess_best_buffer_size(socket: _socket.socket) -> int:
    try:
        socket_stat = os.fstat(socket.fileno())
    except OSError:  # Will not work for sockets which have not a real file descriptor (e.g. on Windows)
        pass
    else:
        if (blksize := getattr(socket_stat, "st_blksize", 0)) > 0:
            return blksize

    from io import DEFAULT_BUFFER_SIZE

    return DEFAULT_BUFFER_SIZE
