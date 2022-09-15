# -*- coding: Utf-8 -*-

from __future__ import annotations

import time
from threading import current_thread
from typing import Any

from pydiamond.system.threading import Thread, thread_factory, thread_factory_method

from ..conftest import silently_ignore_systemexit_in_thread


def test_thread_decorator() -> None:
    variable: int | None = None

    @thread_factory
    def my_func(val: int) -> None:
        nonlocal variable
        variable = val

    t: Thread = my_func(28)
    assert isinstance(t, Thread)
    assert t.daemon == current_thread().daemon
    t.join()
    assert variable == 28


def test_thread_no_auto_start() -> None:
    variable: int | None = None

    @thread_factory(auto_start=False)
    def my_func(val: int) -> None:
        nonlocal variable
        variable = val

    t: Thread = my_func(28)
    assert not t.is_alive()
    assert variable is None
    t.start()
    t.join()
    assert variable == 28


def test_daemon_thread() -> None:
    @thread_factory(auto_start=False, daemon=False)
    def my_func() -> None:
        pass

    t: Thread = my_func()
    assert not t.daemon
    del t

    @thread_factory(auto_start=False, daemon=True)
    def my_daemon_func() -> None:
        pass

    t = my_daemon_func()
    assert t.daemon
    del t


def test_thread_name() -> None:
    @thread_factory(auto_start=False, name="my_thread")
    def my_func() -> None:
        pass

    t: Thread = my_func()
    assert t.name == "my_thread"


def test_custom_thread_class() -> None:
    class CustomThread(Thread):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.custom_var: str = kwargs.pop("custom_var")
            super().__init__(*args, **kwargs)

    @thread_factory(auto_start=False, thread_cls=CustomThread, custom_var="value")
    def my_func() -> None:
        pass

    t: Thread = my_func()
    assert isinstance(t, CustomThread)
    assert t.custom_var == "value"


@silently_ignore_systemexit_in_thread()
def test_terminate() -> None:
    @thread_factory(daemon=False)
    def infinite_loop() -> None:
        while True:
            time.sleep(0.01)

    t = infinite_loop()
    time.sleep(0.5)
    t.terminate()
    assert not t.is_alive()


@silently_ignore_systemexit_in_thread()
def test_join_timeout_call_terminate() -> None:
    @thread_factory(daemon=False)
    def infinite_loop() -> None:
        while True:
            time.sleep(0.01)

    t = infinite_loop()
    t.join(timeout=0.5, terminate_on_timeout=True)
    assert not t.is_alive()


def test_thread_factory_method() -> None:
    class C:
        def __init__(self) -> None:
            self.list: list[int] = []

        @thread_factory_method
        def add(self, number: int) -> None:
            self.list.append(number)

    c = C()

    threads = list(map(c.add, range(10)))

    assert all(isinstance(t, Thread) for t in threads)
    for t in threads:
        t.join()
    assert sorted(c.list) == list(range(10))
