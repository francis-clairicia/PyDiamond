# -*- coding: Utf-8 -*

import time
from threading import current_thread
from typing import Any, Callable

import pytest

from py_diamond.system.threading import Thread, thread


@pytest.fixture(scope="module")
def infinite_loop() -> Callable[[], Thread]:
    class MockThread(Thread):
        def run(self) -> None:
            try:
                return super().run()
            except SystemExit as exc:
                if type(exc) is not SystemExit:  # Subclass of SystemExit, re-raise
                    raise
                # Explicitly catch SystemExit
                # pytest will not put a warning for unhandled exception
                # (whereas threading.excepthook already sliently ignore this exception)
                return

    @thread(daemon=False, thread_cls=MockThread)
    def infinite_loop() -> None:
        while True:
            time.sleep(0.01)

    return infinite_loop


def test_thread_decorator() -> None:
    variable: int | None = None

    @thread
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

    @thread(auto_start=False)
    def my_func(val: int) -> None:
        nonlocal variable
        variable = val

    t: Thread = my_func(28)
    assert variable is None
    t.start()
    t.join()
    assert variable == 28


def test_daemon_thread() -> None:
    @thread(auto_start=False, daemon=False)
    def my_func() -> None:
        pass

    t: Thread = my_func()
    assert not t.daemon
    del t

    @thread(auto_start=False, daemon=True)
    def my_daemon_func() -> None:
        pass

    t = my_daemon_func()
    assert t.daemon
    del t


def test_thread_name() -> None:
    @thread(auto_start=False, name="my_thread")
    def my_func() -> None:
        pass

    t: Thread = my_func()
    assert t.name == "my_thread"


def test_custom_thread_class() -> None:
    class CustomThread(Thread):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            self.custom_var: str = kwargs.pop("custom_var")
            super().__init__(*args, **kwargs)

    @thread(auto_start=False, thread_cls=CustomThread, custom_var="value")
    def my_func() -> None:
        pass

    t: Thread = my_func()
    assert isinstance(t, CustomThread)
    assert t.custom_var == "value"


def test_terminate(infinite_loop: Callable[[], Thread]) -> None:
    t = infinite_loop()
    time.sleep(0.5)
    t.terminate()
    assert not t.is_alive()


def test_join_timeout_call_terminate(infinite_loop: Callable[[], Thread]) -> None:
    t = infinite_loop()
    t.join(timeout=0.5, terminate_on_timeout=True)
    assert not t.is_alive()
