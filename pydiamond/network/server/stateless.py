# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network server default implementation module"""

from __future__ import annotations

__all__ = [
    "AbstractRequestHandler",
    "ForkingStateLessTCPNetworkServer",
    "ForkingStateLessUDPNetworkServer",
    "StateLessTCPNetworkServer",
    "StateLessUDPNetworkServer",
    "ThreadingStateLessTCPNetworkServer",
    "ThreadingStateLessUDPNetworkServer",
]

from abc import abstractmethod
from typing import Any, Generic, TypeVar, overload

from ...system.object import Object, final
from ...system.utils.abc import concreteclass, concreteclasscheck
from ..client import TCPNetworkClient
from ..socket import SocketAddress
from .abc import (
    AbstractNetworkServer,
    AbstractTCPNetworkServer,
    AbstractUDPNetworkServer,
    ConnectedClient,
    NetworkProtocolFactory,
    StreamNetworkProtocolFactory,
)
from .concurrency import ForkingMixIn, ThreadingMixIn

_RequestT = TypeVar("_RequestT")
_ResponseT = TypeVar("_ResponseT")


class AbstractRequestHandler(Generic[_RequestT, _ResponseT], Object):
    request: _RequestT
    client: ConnectedClient[_ResponseT]
    server: AbstractNetworkServer[_RequestT, _ResponseT]

    @final
    def __init__(
        self,
        request: _RequestT,
        client: ConnectedClient[_ResponseT],
        server: AbstractNetworkServer[_RequestT, _ResponseT],
    ) -> None:
        self.request = request
        self.client = client
        self.server = server
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


@concreteclass
class StateLessTCPNetworkServer(AbstractTCPNetworkServer[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]],
        *,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]],
        *,
        family: int = ...,
        backlog: int | None = ...,
        reuse_port: bool = ...,
        dualstack_ipv6: bool = ...,
        protocol_cls: StreamNetworkProtocolFactory[_ResponseT, _RequestT] = ...,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]],
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a TCP request handler")
        self.__request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]] = request_handler_cls
        super().__init__(address, verify_client_in_thread=False, **kwargs)

    @final
    def process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        self.__request_handler_cls(request, client, self)

    @final
    def _verify_new_client(self, client: TCPNetworkClient[_ResponseT, _RequestT], address: SocketAddress) -> bool:
        return True

    @final
    def _on_disconnect(self, client: ConnectedClient[_ResponseT]) -> None:
        pass

    @property
    @final
    def request_handler_cls(self) -> type[AbstractRequestHandler[_RequestT, _ResponseT]]:
        return self.__request_handler_cls


@concreteclass
class StateLessUDPNetworkServer(AbstractUDPNetworkServer[_RequestT, _ResponseT]):
    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]],
        *,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    @overload
    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]],
        *,
        family: int = ...,
        reuse_port: bool = ...,
        protocol_cls: NetworkProtocolFactory[_ResponseT, _RequestT] = ...,
        send_flags: int = ...,
        recv_flags: int = ...,
    ) -> None:
        ...

    def __init__(
        self,
        address: tuple[str, int] | tuple[str, int, int, int],
        request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]],
        **kwargs: Any,
    ) -> None:
        concreteclasscheck(request_handler_cls)
        if not issubclass(request_handler_cls, AbstractRequestHandler):
            raise TypeError(f"{request_handler_cls.__qualname__} is not a UDP request handler")
        self.__request_handler_cls: type[AbstractRequestHandler[_RequestT, _ResponseT]] = request_handler_cls
        super().__init__(address, **kwargs)

    @final
    def process_request(self, request: _RequestT, client: ConnectedClient[_ResponseT]) -> None:
        self.__request_handler_cls(request, client, self)

    @property
    @final
    def request_handler_cls(self) -> type[AbstractRequestHandler[_RequestT, _ResponseT]]:
        return self.__request_handler_cls


class ThreadingStateLessTCPNetworkServer(ThreadingMixIn, StateLessTCPNetworkServer[_RequestT, _ResponseT]):
    pass


class ThreadingStateLessUDPNetworkServer(ThreadingMixIn, StateLessUDPNetworkServer[_RequestT, _ResponseT]):
    pass


class ForkingStateLessTCPNetworkServer(ForkingMixIn, StateLessTCPNetworkServer[_RequestT, _ResponseT]):
    pass


class ForkingStateLessUDPNetworkServer(ForkingMixIn, StateLessUDPNetworkServer[_RequestT, _ResponseT]):
    pass
