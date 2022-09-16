# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network server default implementation module"""

from __future__ import annotations

__all__ = [
    "AbstractRequestHandler",
    "AbstractTCPRequestHandler",
    "AbstractUDPRequestHandler",
    "StateLessTCPNetworkServer",
    "StateLessUDPNetworkServer",
]

from abc import abstractmethod
from typing import Any, Generic, TypeVar, overload

from ...system.object import Object, final
from ...system.utils.abc import concreteclass, concreteclasscheck
from ..client import TCPNetworkClient
from ..socket.base import AbstractTCPServerSocket, AbstractUDPServerSocket, SocketAddress
from .abc import (
    AbstractNetworkServer,
    AbstractTCPNetworkServer,
    AbstractUDPNetworkServer,
    ConnectedClient,
    NetworkProtocolFactory,
    StreamNetworkProtocolFactory,
)

_RequestT = TypeVar("_RequestT")
_ResponseT = TypeVar("_ResponseT")


class AbstractRequestHandler(Generic[_RequestT, _ResponseT], Object):
    @final
    def __init__(self, request: _RequestT, client: ConnectedClient[_ResponseT], server: AbstractNetworkServer) -> None:
        self.request: _RequestT = request
        self.client: ConnectedClient[_ResponseT] = client
        self.server: AbstractNetworkServer = server
        self.setup()
        try:
            self.handle()
        finally:
            self.teardown()

    def setup(self) -> None:
        pass

    @abstractmethod
    def handle(self) -> None:
        raise NotImplementedError

    def teardown(self) -> None:
        pass


class AbstractTCPRequestHandler(AbstractRequestHandler[_RequestT, _ResponseT]):
    server: AbstractTCPNetworkServer[_RequestT, _ResponseT]

    @classmethod
    def welcome(cls, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True


class AbstractUDPRequestHandler(AbstractRequestHandler[_RequestT, _ResponseT]):
    server: AbstractUDPNetworkServer[_RequestT, _ResponseT]


@concreteclass
class StateLessTCPNetworkServer(AbstractTCPNetworkServer[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]],
        *,
        family: int = ...,
        backlog: int | None = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT] = ...,
        socket_cls: type[AbstractTCPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractTCPServerSocket,
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]],
        *,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: Any,
        /,
        request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]],
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractTCPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a TCP request handler")
        self.__request_handler_cls: type[AbstractTCPRequestHandler[_RequestT, _ResponseT]] = request_handler_cls
        super().__init__(__arg, **kwargs)

    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        self.__request_handler_cls(request, client, self)

    def _verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return self.__request_handler_cls.welcome(client, address)

    @property
    @final
    def request_handler_cls(self) -> type[AbstractTCPRequestHandler[_RequestT, _ResponseT]]:
        return self.__request_handler_cls


@concreteclass
class StateLessUDPNetworkServer(AbstractUDPNetworkServer[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]],
        *,
        family: int = ...,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = ...,
        socket_cls: type[AbstractUDPServerSocket] = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        socket: AbstractUDPServerSocket,
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]],
        *,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = ...,
    ) -> None:
        ...

    def __init__(
        self,
        __arg: Any,
        /,
        request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]],
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractUDPRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a UDP request handler")
        self.__request_handler_cls: type[AbstractUDPRequestHandler[_RequestT, _ResponseT]] = request_handler_cls
        super().__init__(__arg, **kwargs)

    def _process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        self.__request_handler_cls(request, client, self)

    @property
    @final
    def request_handler_cls(self) -> type[AbstractUDPRequestHandler[_RequestT, _ResponseT]]:
        return self.__request_handler_cls
