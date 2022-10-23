# -*- coding: Utf-8 -*-


from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator

if TYPE_CHECKING:
    from threading import ExceptHookArgs

################################## Fixture-like functions ##################################


@contextmanager
def silently_ignore_systemexit_in_thread() -> Iterator[None]:
    """
    The default threading.excepthook ignores SystemExit exceptions.
    pytest overrides this hook at compile time and raise a warning for *ALL* exceptions...

    This function is not a fixture because fixtures are always called before the pytest wrapper,
    therefore we need to manually decorate the target function
    """

    import threading

    default_excepthook = threading.excepthook

    def patch_excepthook(args: ExceptHookArgs) -> Any:
        if args.exc_type is SystemExit:
            return
        return default_excepthook(args)

    setattr(threading, "excepthook", patch_excepthook)

    try:
        yield
    finally:
        setattr(threading, "excepthook", default_excepthook)
