# -*- coding: Utf-8 -*-
# Copyright (c) 2021-2022, Francis Clairicia-Rose-Claire-Josephine
#
#
"""Network server concurrency support module

Inspired by (copied from) socketserver module
"""

from __future__ import annotations

__all__ = [
    "AbstractForkingTCPNetworkServer",
    "AbstractForkingUDPNetworkServer",
    "AbstractThreadingTCPNetworkServer",
    "AbstractThreadingUDPNetworkServer",
    "ForkingMixIn",
    "ThreadingMixIn",
]

import os
from typing import Any, TypeVar

from ...system.threading import Thread
from ...system.utils.os import fork, has_fork
from .abc import AbstractTCPNetworkServer, AbstractUDPNetworkServer, ConnectedClient

_RequestT = TypeVar("_RequestT")
_ResponseT = TypeVar("_ResponseT")


class ForkingMixIn:
    """Mix-in class to handle each request in a new process."""

    max_children: int = 40
    # If true, server_close() waits until all child processes complete.
    block_on_close: bool = True

    _active_children: set[int] | None = None

    def collect_children(self, *, blocking: bool = False) -> None:
        """Internal routine to wait for children that have exited."""
        if not has_fork():
            raise NotImplementedError("fork() not supported on this platform")

        if self._active_children is None:
            return

        # If we're above the max number of children, wait and reap them until
        # we go back below threshold. Note that we use waitpid(-1) below to be
        # able to collect children in size(<defunct children>) syscalls instead
        # of size(<children>): the downside is that this might reap children
        # which we didn't spawn, which is why we only resort to this when we're
        # above max_children.
        while len(self._active_children) >= self.max_children:
            try:
                pid, _ = os.waitpid(-1, 0)
                self._active_children.discard(pid)
            except ChildProcessError:
                # we don't have any children, we're done
                self._active_children.clear()
            except OSError:
                break

        # Now reap all defunct children.
        for pid in self._active_children.copy():
            try:
                flags = 0 if blocking else getattr(os, "WNOHANG")
                pid, _ = os.waitpid(pid, flags)
                # if the child hasn't exited yet, pid will be 0 and ignored by
                # discard() below
                self._active_children.discard(pid)
            except ChildProcessError:
                # someone else reaped it
                self._active_children.discard(pid)
            except OSError:
                pass

    def service_actions(self) -> None:
        """Collect the zombie child processes regularly in the ForkingMixIn.
        service_actions is called in the BaseServer's serve_forever loop.
        """
        super().service_actions()  # type: ignore[misc]
        self.collect_children()

    def __process_request_hook__(self, request: Any, client: ConnectedClient[Any]) -> None:
        """Fork a new subprocess to process the request."""
        pid = fork()
        if pid:
            # Parent process
            if self._active_children is None:
                self._active_children = set()
            self._active_children.add(pid)
            client.close()
            return

        # Child process.
        # This must never return, hence os._exit()!
        status = 1
        try:
            self.process_request(request, client)  # type: ignore[attr-defined]
            status = 0
        except Exception:
            self.handle_error(client)  # type: ignore[attr-defined]
        finally:
            try:
                client.shutdown()
            finally:
                os._exit(status)

    def server_close(self) -> None:
        super().server_close()  # type: ignore[misc]
        self.collect_children(blocking=self.block_on_close)


class _Threads(list[Thread]):
    """
    Joinable list of all non-daemon threads.
    """

    def append(self, thread: Thread) -> None:
        self.reap()
        if thread.daemon:
            return
        super().append(thread)

    def pop_all(self) -> list[Thread]:
        self[:], result = [], self[:]
        return result

    def join(self) -> None:
        for thread in self.pop_all():
            thread.join()

    def reap(self) -> None:
        self[:] = (thread for thread in self if thread.is_alive())


class ThreadingMixIn:
    """Mix-in class to handle each request in a new thread."""

    # Decides how threads will act upon termination of the
    # main process
    daemon_threads: bool = False
    # If true, server_close() waits until all non-daemonic threads terminate.
    block_on_close: bool = True
    # Threads object
    # used by server_close() to wait for all threads completion.
    _threads: _Threads | None = None

    def process_request_thread(self, request: Any, client: ConnectedClient[Any]) -> None:
        try:
            self.process_request(request, client)  # type: ignore[attr-defined]
        except Exception:
            self.handle_error(client)  # type: ignore[attr-defined]

    def __process_request_hook__(self, request: Any, client: ConnectedClient[Any]) -> None:
        threads: _Threads | None = self._threads
        if self.block_on_close and threads is None:
            self._threads = threads = _Threads()
        t = Thread(target=self.process_request_thread, args=(request, client))
        t.daemon = self.daemon_threads
        if threads is not None:
            threads.append(t)
        t.start()

    def server_close(self) -> None:
        super().server_close()  # type: ignore[misc]
        if self._threads:
            self._threads.join()


class AbstractThreadingTCPNetworkServer(ThreadingMixIn, AbstractTCPNetworkServer[_RequestT, _ResponseT]):
    pass


class AbstractThreadingUDPNetworkServer(ThreadingMixIn, AbstractUDPNetworkServer[_RequestT, _ResponseT]):
    pass


class AbstractForkingTCPNetworkServer(ForkingMixIn, AbstractTCPNetworkServer[_RequestT, _ResponseT]):
    pass


class AbstractForkingUDPNetworkServer(ForkingMixIn, AbstractUDPNetworkServer[_RequestT, _ResponseT]):
    pass
