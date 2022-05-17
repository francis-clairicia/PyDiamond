# -*- coding: Utf-8 -*

from threading import Thread
from typing import Any, Iterator

import pytest


@pytest.fixture(scope="session", autouse=True)
def silently_ignore_systemexit_in_thread() -> Iterator[None]:
    """
    The default threading.excepthook ignores SystemExit exceptions.
    pytest overrides this hook at compile time and raise a warning for *ALL* exceptions...
    """

    run = Thread.run

    def patch_run(self: Thread, *args: Any, **kwargs: Any) -> None:
        try:
            return run(self, *args, **kwargs)
        except SystemExit as exc:
            # Explicitly catch SystemExit
            # pytest will not put a warning for unhandled exception
            if type(exc) is not SystemExit:  # Subclass of SystemExit, re-raise
                raise
            return

    setattr(Thread, "run", patch_run)
    yield
    setattr(Thread, "run", run)
